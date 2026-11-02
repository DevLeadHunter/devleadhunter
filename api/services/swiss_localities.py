"""
Swiss localities — the locality a Swiss postal code serves, as the federal geodata service (geo.admin.ch) lists it.

Google writes the address of a business named after its locality, without a street, oddly: « Le, Exemple-du-Lac 6,
2999 Le » for « Le Exemple-du-Lac 6, 2999 Le Exemple-du-Lac ». The town read from it is then a bare article; the
postal code tells the locality, and the address is rebuilt around it.
"""

from __future__ import annotations

import logging
import re

import httpx

from services.country_profiles import CountryProfiles
from services.decision_maker.normalize import fold

logger = logging.getLogger(__name__)

_SEARCH_URL: str = "https://api3.geo.admin.ch/rest/services/api/SearchServer"
_TIMEOUT_SECONDS: float = 10.0
_MAX_LOCALITIES: int = 10
_TAG_RE: re.Pattern[str] = re.compile(r"<[^>]+>")
_LABEL_RE: re.Pattern[str] = re.compile(r"^\s*(\d{4})\s*-\s*(.+?)\s*$")
_WORD_SEPARATORS_RE: re.Pattern[str] = re.compile(r"[^a-z0-9]+")
_BARE_ARTICLES: frozenset[str] = frozenset({"le", "la", "les", "l"})


class SwissLocalities:
    """Tells the locality of a Swiss postal code, read once per code."""

    def __init__(self) -> None:
        self._localities_by_postal_code: dict[str, list[str]] = {}

    @staticmethod
    def is_bare_article(town: str | None) -> bool:
        """Whether a town read from an address is only an article (« Le », « La », « L' »), no place at all."""
        return " ".join(_WORD_SEPARATORS_RE.split(fold(town or ""))).strip() in _BARE_ARTICLES

    async def localities_of(self, postal_code: str) -> list[str]:
        """
        The localities a Swiss postal code serves (« 2400 » serves Le Locle and Le Prévoux).

        Args:
            postal_code: A four-digit Swiss postal code.

        Returns:
            Their names; empty when the service does not answer (asked again next time).
        """
        if postal_code in self._localities_by_postal_code:
            return self._localities_by_postal_code[postal_code]
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as http:
                response = await http.get(
                    _SEARCH_URL,
                    params={
                        "searchText": postal_code,
                        "type": "locations",
                        "origins": "zipcode",
                        "limit": _MAX_LOCALITIES,
                    },
                )
            if response.status_code != 200:
                return []
            results = response.json().get("results") or []
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("geo.admin.ch lookup of postal code %s failed: %s", postal_code, exc)
            return []
        localities = [
            match.group(2)
            for result in results
            if (match := _LABEL_RE.match(_TAG_RE.sub("", str((result.get("attrs") or {}).get("label") or ""))))
            and match.group(1) == postal_code
        ]
        self._localities_by_postal_code[postal_code] = localities
        return localities

    async def mended_town_and_address(self, address: str) -> tuple[str | None, str]:
        """
        The locality a Swiss address's postal code serves, and the address rebuilt around it, for an address whose
        town reads as a bare article.

        The locality the address's words name is chosen among those of its postal code, else the only one.

        Args:
            address: The address as Google wrote it (« Le, Exemple-du-Lac 6, 2999 Le »).

        Returns:
            The locality and the rebuilt address (« Le Exemple-du-Lac 6, 2999 Le Exemple-du-Lac »); ``None`` and the
            address as it was when the postal code tells no single locality.
        """
        postal_match = CountryProfiles.get("CH").postal_code_regex.search(address)
        if postal_match is None:
            return None, address
        postal_code = postal_match.group(1)
        localities = await self.localities_of(postal_code)
        address_words = f" {' '.join(_WORD_SEPARATORS_RE.split(fold(address)))} "
        named = [locality for locality in localities if f" {self._distinctive_words(locality)} " in address_words]
        chosen = named if named else localities
        if len(chosen) != 1:
            return None, address
        locality = chosen[0]
        head = address[: postal_match.start()].strip().rstrip(",").strip()
        head_parts = [part.strip() for part in head.split(",") if part.strip()]
        if len(head_parts) > 1 and self.is_bare_article(head_parts[0]):
            head_parts = [f"{head_parts[0]} {head_parts[1]}", *head_parts[2:]]
        street = ", ".join(head_parts)
        return locality, f"{street}, {postal_code} {locality}" if street else f"{postal_code} {locality}"

    @staticmethod
    def _distinctive_words(locality: str) -> str:
        """A locality's words without its opening article (« exemple du lac » for « Le Exemple-du-Lac »)."""
        words = [word for word in _WORD_SEPARATORS_RE.split(fold(locality)) if word]
        return " ".join(words[1:] if words and words[0] in _BARE_ARTICLES else words)


swiss_localities = SwissLocalities()
