"""Coverage-map cities are looked up once, kept for every later map, and never placed in the wrong country."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.v1.routes.dashboard import dashboard_coverage
from core.clock import naive_utc_now
from enums.city_geocoding import CityGeocodingStatus
from models.geocoded_city import GeocodedCity
from models.prospect_db import ProspectDB
from models.user import User
from schemas.dashboard import CityToPlace, PlacedCity
from services.city_geocoding_service import CityGeocodingService, city_geocoding_service


class ScriptedGeocoders:
    """Answers each geocoder call from a script keyed by the city asked, and keeps the calls."""

    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.asked: list[str] = []

    async def get_json(self, client: object, url: str, params: dict[str, str | int]) -> Any:
        """The scripted answer for the city of this call, None when the script has none."""
        asked = str(params.get("nom") or params.get("q"))
        self.asked.append(asked)
        return self.answers.get(asked)


@pytest.fixture
def geocoders(monkeypatch: pytest.MonkeyPatch) -> ScriptedGeocoders:
    scripted = ScriptedGeocoders({})
    monkeypatch.setattr(CityGeocodingService, "_get_json", staticmethod(scripted.get_json))
    return scripted


def _commune(name: str, code: str, longitude: float, latitude: float, region: str) -> dict[str, Any]:
    return {
        "nom": name,
        "code": code,
        "codeDepartement": code[:2],
        "codeRegion": region,
        "centre": {"type": "Point", "coordinates": [longitude, latitude]},
    }


def _photon(name: str, countrycode: str, osm_key: str, osm_value: str, longitude: float, latitude: float) -> dict:
    return {
        "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
        "properties": {"name": name, "countrycode": countrycode, "osm_key": osm_key, "osm_value": osm_value},
    }


def _place(db: Session, *towns: tuple[str, str]) -> list[PlacedCity]:
    return asyncio.run(
        city_geocoding_service.place_cities(db, [CityToPlace(city=city, country=country) for city, country in towns])
    )


def test_a_french_town_lands_on_its_exact_commune_with_its_region(db: Session, geocoders: ScriptedGeocoders) -> None:
    geocoders.answers["betton"] = [
        _commune("Betton-Bettonet", "73042", 6.11, 45.53, "84"),
        _commune("Betton", "35024", -1.64, 48.18, "53"),
    ]

    [placed] = _place(db, ("Betton", "FR"))

    assert placed.geocoding is CityGeocodingStatus.PLACED
    assert placed.location is not None
    assert (placed.location.latitude, placed.location.longitude) == (48.18, -1.64)
    assert (placed.location.insee_code, placed.location.region_code) == ("35024", "53")


def test_a_swiss_town_keeps_to_switzerland_and_prefers_the_town_to_its_canton(
    db: Session, geocoders: ScriptedGeocoders
) -> None:
    geocoders.answers["Fribourg, Suisse"] = {
        "features": [
            _photon("Fribourg", "FR", "place", "village", 6.9, 48.6),
            _photon("Fribourg", "CH", "boundary", "administrative", 7.06, 46.73),
            _photon("Fribourg", "CH", "place", "city", 7.16, 46.80),
        ]
    }

    [placed] = _place(db, ("Fribourg", "ch"))

    assert placed.country == "CH"
    assert placed.location is not None
    assert (placed.location.latitude, placed.location.longitude) == (46.80, 7.16)
    assert placed.location.region_code == ""


def test_a_placed_town_is_never_asked_again_by_any_later_map(db: Session, geocoders: ScriptedGeocoders) -> None:
    geocoders.answers["Genève, Suisse"] = {"features": [_photon("Genève", "CH", "place", "city", 6.14, 46.2)]}

    _place(db, ("Genève", "CH"))
    [placed_again] = _place(db, ("  GENEVE ", "CH"))

    assert geocoders.asked == ["Genève, Suisse"]
    assert placed_again.geocoding is CityGeocodingStatus.PLACED


def test_a_failed_call_is_not_kept_and_comes_back_pending(db: Session, geocoders: ScriptedGeocoders) -> None:
    [placed] = _place(db, ("Lausanne", "CH"))

    assert placed.geocoding is CityGeocodingStatus.PENDING
    assert geocoders.asked == ["Lausanne, Suisse", "Lausanne, Suisse"]
    assert db.execute(select(GeocodedCity)).scalars().all() == []


def test_an_unknown_town_is_kept_then_asked_again_after_a_month(db: Session, geocoders: ScriptedGeocoders) -> None:
    geocoders.answers["bricous"] = []

    [placed] = _place(db, ("Bricous", "FR"))
    [still_unknown] = _place(db, ("Bricous", "FR"))
    row = db.execute(select(GeocodedCity)).scalar_one()
    row.geocoded_at = naive_utc_now() - timedelta(days=31)
    db.commit()
    _place(db, ("Bricous", "FR"))

    assert placed.geocoding is CityGeocodingStatus.UNKNOWN
    assert still_unknown.geocoding is CityGeocodingStatus.UNKNOWN
    assert geocoders.asked == ["bricous", "bricous"]


def test_no_database_connection_is_held_while_a_geocoder_answers(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    transaction_open_during_calls: list[bool] = []

    async def answer(client: object, url: str, params: dict[str, str | int]) -> list[dict[str, Any]]:
        transaction_open_during_calls.append(db.in_transaction())
        return [_commune("Albi", "81004", 2.14, 43.93, "76")]

    monkeypatch.setattr(CityGeocodingService, "_get_json", staticmethod(answer))
    db.add(User(name="Camille Durand", email="camille@example.com", hashed_password="x"))
    db.commit()
    db.execute(select(User)).all()

    _place(db, ("Albi", "FR"))

    assert transaction_open_during_calls == [False]


def test_the_coverage_answer_carries_the_known_centres_and_leaves_the_others_pending(
    db: Session, geocoders: ScriptedGeocoders
) -> None:
    owner = User(name="Camille Durand", email="camille@example.com", hashed_password="x")
    db.add(owner)
    db.commit()
    for name, city, country in (("Jardins du Tarn", "Albi", "FR"), ("Paysages du Léman", "Nyon", "CH")):
        db.add(
            ProspectDB(
                name=name,
                city=city,
                country=country,
                category="Paysagiste",
                source="google",
                confidence=2,
                user_id=owner.id,
            )
        )
    db.commit()
    geocoders.answers["albi"] = [_commune("Albi", "81004", 2.14, 43.93, "76")]
    _place(db, ("albi", "FR"))

    response = asyncio.run(dashboard_coverage(scope="me", member_id=None, categories=None, current_user=owner, db=db))

    by_city = {city.city: city for city in response.cities}
    assert by_city["Albi"].geocoding is CityGeocodingStatus.PLACED
    assert by_city["Albi"].location is not None and by_city["Albi"].location.region_code == "76"
    assert by_city["Nyon"].geocoding is CityGeocodingStatus.PENDING
    assert by_city["Nyon"].location is None
