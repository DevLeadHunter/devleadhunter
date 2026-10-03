"""Countries open to prospection, with the facts the dashboard reads per country."""

from __future__ import annotations

from fastapi import APIRouter

from schemas.country import CountryProfileResponse
from services.country_profiles import CountryProfiles

router = APIRouter(prefix="/countries", tags=["countries"])


@router.get("", response_model=list[CountryProfileResponse])
async def list_countries() -> list[CountryProfileResponse]:
    """
    List the countries open to prospection, in declaration order (France first).

    Returns:
        One entry per enabled country profile.
    """
    return [CountryProfileResponse.from_profile(profile) for profile in CountryProfiles.enabled()]
