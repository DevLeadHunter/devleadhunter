"""Countries supported by the prospection pipeline (ISO 3166-1 alpha-2)."""

from __future__ import annotations

SUPPORTED_COUNTRIES: dict[str, str] = {
    "FR": "France",
    "CH": "Suisse",
    "BE": "Belgique",
}

DEFAULT_COUNTRY: str = "FR"


def normalize_country(code: str | None) -> str:
    """
    Normalize a country code to a supported uppercase alpha-2 value.

    Args:
        code: Raw code from a job or prospect payload.

    Returns:
        The uppercase code when supported, the French default otherwise.
    """
    cleaned = (code or "").strip().upper()
    return cleaned if cleaned in SUPPORTED_COUNTRIES else DEFAULT_COUNTRY


def country_label(code: str | None) -> str:
    """
    French display name of a country ("Suisse"), used to disambiguate search queries.

    Args:
        code: ISO alpha-2 code.

    Returns:
        The label of the normalized code.
    """
    return SUPPORTED_COUNTRIES[normalize_country(code)]
