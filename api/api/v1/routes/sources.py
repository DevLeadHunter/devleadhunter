"""
Prospect data source metadata endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

from schemas.sources import list_source_options
from schemas.sourcing import SourcingVerticalResponse
from services.sourcing_verticals import SourcingVerticalCatalog

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
async def get_prospect_sources() -> list[dict[str, str]]:
    """
    List available prospect scraping sources for UI selects.

    Returns:
        Source options with ``value`` and ``label`` keys.
    """
    return list_source_options(include_all=True)


@router.get("/verticals", response_model=list[SourcingVerticalResponse])
async def get_sourcing_verticals() -> list[SourcingVerticalResponse]:
    """
    List the Réceptionniste IA target verticals, wave by wave, for the search presets.

    Returns:
        The verticals in catalog order (wave 1 first).
    """
    return [
        SourcingVerticalResponse(
            key=vertical.key,
            label=vertical.label,
            wave=vertical.wave,
            search_terms=list(vertical.search_terms),
        )
        for vertical in SourcingVerticalCatalog.VERTICALS
    ]
