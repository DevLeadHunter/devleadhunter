"""
French départements — where a French business sits, from its postal code or, without one, its town.

A registry match is confirmed by its département: artisans are often registered at home, one commune
away from where they work. A prospect found on Facebook often has a town but no postal code, so the
town is looked up in the official list of communes (geo.api.gouv.fr).
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

import httpx

from services.decision_maker.normalize import town_key

logger = logging.getLogger(__name__)

_COMMUNES_URL: str = "https://geo.api.gouv.fr/communes"
_TIMEOUT_SECONDS: float = 8.0
_MAX_COMMUNES: int = 10
_OVERSEAS_PREFIX: str = "97"
_CORSICA_PREFIX: str = "20"


class FrenchDepartments:
    """Finds the département of a French postal code or town."""

    _department_by_town: ClassVar[dict[str, str | None]] = {}

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

    @staticmethod
    async def _communes_named(town: str) -> list[dict[str, Any]] | None:
        """The communes the official list finds for a name, or None when it does not answer."""
        params: dict[str, str | int] = {"nom": town, "fields": "nom,codeDepartement", "limit": _MAX_COMMUNES}
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                response = await client.get(_COMMUNES_URL, params=params)
                response.raise_for_status()
                communes = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.info("Commune lookup of %r failed: %s", town, exc)
            return None
        if not isinstance(communes, list):
            return None
        return [commune for commune in communes if isinstance(commune, dict)]
