"""Countries supported by the prospection pipeline (ISO 3166-1 alpha-2).

The facts of each country (currency, timezone, SMS rules, formats…) live in
``services.country_profiles``; this module keeps the short helpers the scrapers and the
job payloads read.
"""

from __future__ import annotations

from services.country_profiles import DEFAULT_COUNTRY_CODE, CountryProfiles

SUPPORTED_COUNTRIES: dict[str, str] = CountryProfiles.labels()

DEFAULT_COUNTRY: str = DEFAULT_COUNTRY_CODE


def normalize_country(code: str | None) -> str:
    """
    Normalize a country code to a supported uppercase alpha-2 value.

    Args:
        code: Raw code from a job or prospect payload.

    Returns:
        The uppercase code when supported, the French default otherwise.
    """
    return CountryProfiles.get(code).code


def country_label(code: str | None) -> str:
    """
    French display name of a country ("Suisse"), used to disambiguate search queries.

    Args:
        code: ISO alpha-2 code.

    Returns:
        The label of the normalized code.
    """
    return CountryProfiles.get(code).label
