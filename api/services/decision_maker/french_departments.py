"""
French départements — where a French business sits, from its postal code or, without one, its town.

A registry match is confirmed by its département: artisans are often registered at home, one commune
away from where they work. A prospect found on Facebook often has a town but no postal code, so the
town is looked up in the official list of communes (geo.api.gouv.fr).
"""

from __future__ import annotations

import logging
import re
from typing import Any, ClassVar

import httpx

from services.decision_maker.normalize import town_key

logger = logging.getLogger(__name__)

_COMMUNES_URL: str = "https://geo.api.gouv.fr/communes"
_TIMEOUT_SECONDS: float = 8.0
_MAX_COMMUNES: int = 10
_OVERSEAS_PREFIX: str = "97"
_CORSICA_PREFIX: str = "20"
_COMMUNE_LINK_WORDS: frozenset[str] = frozenset(
    {"de", "du", "des", "la", "le", "les", "sur", "sous", "en", "et", "aux"}
)


class FrenchDepartments:
    """Finds the département of a French postal code or town."""

    _department_by_town: ClassVar[dict[str, str | None]] = {}
    _is_town_by_word: ClassVar[dict[str, bool]] = {}

    @staticmethod
    def of_postal_code(postal_code: str | None) -> str | None:
        """
        The département of a French postal code (« 46000 » → « 46 », « 97411 » → « 974 »).

        Args:
            postal_code: A five-digit French postal code, if any.

        Returns:
            The département code, or None for no code, a malformed one or Corsica (2A or 2B, which
            the code alone does not tell apart).
        """
        code = (postal_code or "").strip()
        if len(code) != 5 or not code.isdigit() or code.startswith(_CORSICA_PREFIX):
            return None
        return code[:3] if code.startswith(_OVERSEAS_PREFIX) else code[:2]

    @classmethod
    async def of_town(cls, town: str | None) -> str | None:
        """
        The département of the French commune of that name, from the official list of communes.

        Args:
            town: The business's town, as the prospect carries it.

        Returns:
            The département code, or None when no commune bears exactly that name, several in
            different départements do, or the list does not answer (then it is asked again later).
        """
        key = town_key(town or "")
        if not key:
            return None
        if key in cls._department_by_town:
            return cls._department_by_town[key]
        communes = await cls._communes_named(town or "")
        if communes is None:
            return None
        departments = {
            str(commune.get("codeDepartement") or "")
            for commune in communes
            if town_key(str(commune.get("nom") or "")) == key
        }
        department = departments.pop() if len(departments) == 1 else None
        cls._department_by_town[key] = department
        return department

    @classmethod
    async def is_town_name(cls, word: str) -> bool:
        """
        Whether a word is the name of a French commune (« Lescar »), a place rather than the business's own word.

        Args:
            word: A word of a business name.

        Returns:
            True when a commune bears exactly that name; False when none does or the list does not answer.
        """
        key = town_key(word)
        if not key:
            return False
        if key in cls._is_town_by_word:
            return cls._is_town_by_word[key]
        communes = await cls._communes_named(word)
        if communes is None:
            return False
        is_town = any(town_key(str(commune.get("nom") or "")) == key for commune in communes)
        cls._is_town_by_word[key] = is_town
        return is_town

    @classmethod
    async def commune_name(cls, registry_commune: str, *, postal_code: str | None = None) -> str:
        """
        A commune's name as the official list spells it (« PONT-DU-CHATEAU » gives « Pont-du-Château »).

        The registry writes communes in capitals, without accents nor always hyphens; the communes of its postal code
        are read first when it gives one (« TROUVILLE SUR MER » at 14360 is « Trouville-sur-Mer »). A name the list
        does not find is only made readable (« Pont-du-Chateau »).

        Args:
            registry_commune: The commune as the registry writes it.
            postal_code: Its postal code, when the registry gives one.

        Returns:
            The commune's spelling.
        """
        key = town_key(registry_commune)
        spelled = cls._spelling_among(await cls._communes_of_postal_code(postal_code), key) if postal_code else None
        if spelled is None:
            spelled = cls._spelling_among(await cls._communes_named(registry_commune), key)
        return spelled or cls.readable_commune(registry_commune)

    @staticmethod
    def _spelling_among(communes: list[dict[str, Any]] | None, key: str) -> str | None:
        """The official name of the commune of the list whose comparison key is *key*."""
        return next(
            (
                str(commune["nom"])
                for commune in communes or []
                if commune.get("nom") and town_key(str(commune["nom"])) == key
            ),
            None,
        )

    @staticmethod
    def readable_commune(registry_commune: str) -> str:
        """A commune the registry writes in capitals, made readable (« PONT-DU-CHATEAU » gives « Pont-du-Chateau »)."""
        words = re.split(r"([\s-])", registry_commune.strip().lower())
        return "".join(
            word if word in _COMMUNE_LINK_WORDS and index > 0 else word.capitalize() for index, word in enumerate(words)
        )

    @staticmethod
    async def _communes_named(town: str) -> list[dict[str, Any]] | None:
        """The communes the official list finds for a name, or None when it does not answer."""
        return await FrenchDepartments._communes_where(
            {"nom": town, "fields": "nom,codeDepartement", "limit": _MAX_COMMUNES}
        )

    @staticmethod
    async def _communes_of_postal_code(postal_code: str) -> list[dict[str, Any]] | None:
        """The communes the official list gives a postal code, or None when it does not answer."""
        return await FrenchDepartments._communes_where({"codePostal": postal_code, "fields": "nom,codeDepartement"})

    @staticmethod
    async def _communes_where(params: dict[str, str | int]) -> list[dict[str, Any]] | None:
        """The communes the official list answers a query with, or None when it does not answer."""
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.get(_COMMUNES_URL, params=params)
                response.raise_for_status()
                communes = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.info("Commune lookup %s failed: %s", params, exc)
            return None
        if not isinstance(communes, list):
            return None
        return [commune for commune in communes if isinstance(commune, dict)]
