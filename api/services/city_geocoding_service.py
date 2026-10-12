"""
City centres for the coverage map, looked up once and shared by every device and every user.

France asks the official list of communes (geo.api.gouv.fr), which also gives the commune's département and region;
the other countries ask Photon (OpenStreetMap), filtered to the city's country so a homonym abroad is never placed.
A city no geocoder knows is kept as unknown and asked again after a month; a failed call is never kept, so the
next map asks again. The session's connection goes back to the pool before any geocoder is asked: Photon often
takes several seconds per city.
"""

from __future__ import annotations

import asyncio
import logging
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from enums.city_geocoding import CityGeocodingStatus
from models.geocoded_city import GeocodedCity
from schemas.dashboard import CityLocation, CityToPlace, CoverageCity, PlacedCity
from services.country_profiles import CountryProfiles

logger = logging.getLogger(__name__)

CountryAndCityKey = tuple[str, str]


@dataclass(frozen=True)
class CityPlacement:
    """Where the lookup of one city stands, with its centre once placed."""

    status: CityGeocodingStatus
    location: CityLocation | None = None


_PENDING: CityPlacement = CityPlacement(CityGeocodingStatus.PENDING)
_UNKNOWN: CityPlacement = CityPlacement(CityGeocodingStatus.UNKNOWN)


class CityGeocodingService:
    """Places the cities of the coverage map, from the shared cache first, then from the public geocoders."""

    _FRENCH_COMMUNES_URL: str = "https://geo.api.gouv.fr/communes"
    _PHOTON_URL: str = "https://photon.komoot.io/api/"
    _USER_AGENT: str = "DevLeadHunter coverage map (+https://devleadhunter.fr)"
    _TIMEOUT_SECONDS: float = 12.0
    _CONCURRENT_LOOKUPS: int = 6
    _RETRY_DELAY_SECONDS: float = 0.8
    _UNKNOWN_ASKED_AGAIN_AFTER: timedelta = timedelta(days=30)
    _SETTLEMENT_PLACE_VALUES: frozenset[str] = frozenset(
        {"city", "town", "village", "hamlet", "suburb", "municipality"}
    )

    @staticmethod
    def city_key(city: str) -> str:
        """
        The cache key of a city name: trimmed, lowercased, without accents (« Genève » → « geneve »).

        Args:
            city: City name as a prospect carries it.

        Returns:
            The key, empty for a blank name.
        """
        decomposed = unicodedata.normalize("NFD", city.strip().lower())
        return "".join(character for character in decomposed if not unicodedata.combining(character))

    def with_cached_placements(self, db: Session, cities: list[CoverageCity]) -> list[CoverageCity]:
        """
        The coverage cities with the centre the shared cache knows; the others stay pending for the dashboard to ask.

        Args:
            db: Active database session.
            cities: Cities of the coverage answer.

        Returns:
            The same cities, in order, each with its geocoding status and location.
        """
        keys = [self._country_and_city_key(city.city, city.country) for city in cities]
        placements = self._cached_placements(db, keys)
        placed_cities: list[CoverageCity] = []
        for city, key in zip(cities, keys, strict=True):
            placement = placements.get(key, _PENDING)
            placed_cities.append(
                city.model_copy(update={"geocoding": placement.status, "location": placement.location})
            )
        return placed_cities

    async def place_cities(self, db: Session, cities: list[CityToPlace]) -> list[PlacedCity]:
        """
        Place cities from the cache, else from the geocoders, saving their answers for every later map.

        Args:
            db: Active database session; its connection is handed back before the geocoders are asked.
            cities: Cities the dashboard could not place.

        Returns:
            One answer per city, in order; a city whose lookup failed comes back pending.
        """
        keys = [self._country_and_city_key(city.city, city.country) for city in cities]
        names_by_key = {key: city.city.strip() for key, city in zip(keys, cities, strict=True) if key[1]}
        placements = self._cached_placements(db, names_by_key)
        db.commit()
        missing = {key: name for key, name in names_by_key.items() if key not in placements}
        if missing:
            looked_up = await self._look_up_all(missing)
            self._save(db, looked_up)
            placements.update(looked_up)
        placed_cities: list[PlacedCity] = []
        for city, key in zip(cities, keys, strict=True):
            placement = placements.get(key, _PENDING)
            placed_cities.append(
                PlacedCity(city=city.city, country=key[0], geocoding=placement.status, location=placement.location)
            )
        return placed_cities

    def _country_and_city_key(self, city: str, country: str) -> CountryAndCityKey:
        """The cache identity of a city: its country upper-cased (blank reads as France) and its city key."""
        return ((country or "").strip().upper() or "FR", self.city_key(city))

    def _cached_placements(
        self, db: Session, keys: Iterable[CountryAndCityKey]
    ) -> dict[CountryAndCityKey, CityPlacement]:
        """What the shared cache knows of these cities; one kept as unknown over a month ago is left out, to ask again."""
        wanted = {key for key in keys if key[1]}
        if not wanted:
            return {}
        rows = (
            db.execute(select(GeocodedCity).where(GeocodedCity.city_key.in_({city_key for _, city_key in wanted})))
            .scalars()
            .all()
        )
        asked_again_before = naive_utc_now() - self._UNKNOWN_ASKED_AGAIN_AFTER
        placements: dict[CountryAndCityKey, CityPlacement] = {}
        for row in rows:
            key = (row.country, row.city_key)
            if key not in wanted or (not row.is_found and row.geocoded_at < asked_again_before):
                continue
            placements[key] = self._placement_of(row)
        return placements

    async def _look_up_all(self, missing: dict[CountryAndCityKey, str]) -> dict[CountryAndCityKey, CityPlacement]:
        """Ask the geocoders for every missing city, a few at a time so a burst stays under their rate limits."""
        gate = asyncio.Semaphore(self._CONCURRENT_LOOKUPS)
        async with httpx.AsyncClient(timeout=self._TIMEOUT_SECONDS, headers={"User-Agent": self._USER_AGENT}) as client:

            async def look_up(key: CountryAndCityKey, name: str) -> tuple[CountryAndCityKey, CityPlacement]:
                async with gate:
                    return key, await self._look_up_with_one_retry(client, name, key[0])

            answers = await asyncio.gather(*(look_up(key, name) for key, name in missing.items()))
        return dict(answers)

    async def _look_up_with_one_retry(self, client: httpx.AsyncClient, city: str, country: str) -> CityPlacement:
        """Look a city up, once more after a short pause when the call itself failed (a rate-limit burst, a drop)."""
        placement = await self._look_up(client, city, country)
        if placement.status is not CityGeocodingStatus.PENDING:
            return placement
        await asyncio.sleep(self._RETRY_DELAY_SECONDS)
        return await self._look_up(client, city, country)

    async def _look_up(self, client: httpx.AsyncClient, city: str, country: str) -> CityPlacement:
        """Route a city to its country's geocoder."""
        if country == "FR":
            return await self._french_commune(client, city)
        return await self._foreign_city(client, city, country)

    async def _french_commune(self, client: httpx.AsyncClient, city: str) -> CityPlacement:
        """
        Place a French city through the official list of communes, the exact name before the most populated match.

        « Betton » used to land on Betton-Bettonet (306 inhabitants, Savoie) when the first match was trusted.
        """
        key = self.city_key(city)
        answer = await self._get_json(
            client,
            self._FRENCH_COMMUNES_URL,
            {"nom": key, "fields": "code,nom,centre,codeDepartement,codeRegion", "boost": "population", "limit": 5},
        )
        if not isinstance(answer, list):
            return _PENDING
        communes = [commune for commune in answer if isinstance(commune, dict)]
        exact = next((commune for commune in communes if self.city_key(str(commune.get("nom") or "")) == key), None)
        chosen = exact or (communes[0] if communes else None)
        coordinates = self._coordinates((chosen or {}).get("centre"))
        if chosen is None or coordinates is None:
            return _UNKNOWN
        longitude, latitude = coordinates
        return CityPlacement(
            CityGeocodingStatus.PLACED,
            CityLocation(
                latitude=latitude,
                longitude=longitude,
                insee_code=str(chosen.get("code") or ""),
                department_code=str(chosen.get("codeDepartement") or ""),
                region_code=str(chosen.get("codeRegion") or ""),
            ),
        )

    async def _foreign_city(self, client: httpx.AsyncClient, city: str, country: str) -> CityPlacement:
        """Place a city abroad through Photon, in its own country, the settlement before its namesake province."""
        profile = CountryProfiles.declared(country)
        query = f"{city.strip()}, {profile.search_label or profile.label}" if profile else city.strip()
        answer = await self._get_json(client, self._PHOTON_URL, {"q": query, "limit": 5, "lang": "fr"})
        if not isinstance(answer, dict):
            return _PENDING
        features = [feature for feature in answer.get("features") or [] if isinstance(feature, dict)]
        in_country = [
            feature
            for feature in features
            if str((feature.get("properties") or {}).get("countrycode") or "").upper() == country
        ]
        candidates = [feature for feature in in_country if self._is_settlement(feature)] or in_country
        key = self.city_key(city)
        exact = next(
            (
                feature
                for feature in candidates
                if self.city_key(str((feature.get("properties") or {}).get("name") or "")) == key
            ),
            None,
        )
        chosen = exact or (candidates[0] if candidates else None)
        coordinates = self._coordinates((chosen or {}).get("geometry"))
        if coordinates is None:
            return _UNKNOWN
        longitude, latitude = coordinates
        return CityPlacement(CityGeocodingStatus.PLACED, CityLocation(latitude=latitude, longitude=longitude))

    def _is_settlement(self, feature: dict[str, Any]) -> bool:
        """Whether a Photon result is a city, town, village or suburb rather than an area sharing its name."""
        properties = feature.get("properties") or {}
        return properties.get("osm_key") == "place" and properties.get("osm_value") in self._SETTLEMENT_PLACE_VALUES

    @staticmethod
    def _coordinates(point: Any) -> tuple[float, float] | None:
        """The (longitude, latitude) of a GeoJSON point, None when the answer carries none."""
        coordinates = point.get("coordinates") if isinstance(point, dict) else None
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            return None
        longitude, latitude = coordinates[0], coordinates[1]
        if not isinstance(longitude, int | float) or not isinstance(latitude, int | float):
            return None
        return float(longitude), float(latitude)

    @staticmethod
    async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, str | int]) -> Any:
        """The decoded answer of a geocoder, None when the call failed (network, status, body)."""
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.info("Geocoding call to %s failed: %s", url, exc)
            return None

    def _save(self, db: Session, placements: dict[CountryAndCityKey, CityPlacement]) -> None:
        """Keep the placed and unknown cities in the cache; a city another map saved meanwhile keeps that answer."""
        answered = {
            key: placement
            for key, placement in placements.items()
            if placement.status is not CityGeocodingStatus.PENDING
        }
        if not answered:
            return
        existing = {
            (row.country, row.city_key): row
            for row in db.execute(
                select(GeocodedCity).where(GeocodedCity.city_key.in_({city_key for _, city_key in answered}))
            ).scalars()
        }
        now = naive_utc_now()
        for key, placement in answered.items():
            row = existing.get(key)
            if row is None:
                row = GeocodedCity(country=key[0], city_key=key[1])
                db.add(row)
            location = placement.location
            row.is_found = location is not None
            row.latitude = location.latitude if location else None
            row.longitude = location.longitude if location else None
            row.insee_code = location.insee_code if location else ""
            row.department_code = location.department_code if location else ""
            row.region_code = location.region_code if location else ""
            row.geocoded_at = now
        try:
            db.commit()
        except IntegrityError:
            db.rollback()

    @staticmethod
    def _placement_of(row: GeocodedCity) -> CityPlacement:
        """The placement a cache row stands for."""
        if not row.is_found or row.latitude is None or row.longitude is None:
            return _UNKNOWN
        return CityPlacement(
            CityGeocodingStatus.PLACED,
            CityLocation(
                latitude=row.latitude,
                longitude=row.longitude,
                insee_code=row.insee_code,
                department_code=row.department_code,
                region_code=row.region_code,
            ),
        )


city_geocoding_service = CityGeocodingService()
