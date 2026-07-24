"""
Prospect data source metadata endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

from schemas.sources import list_source_options

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
async def get_prospect_sources() -> list[dict[str, str]]:
    """
    List available prospect scraping sources for UI selects.

    Returns:
        Source options with ``value`` and ``label`` keys.
    """
    return list_source_options(include_all=True)
