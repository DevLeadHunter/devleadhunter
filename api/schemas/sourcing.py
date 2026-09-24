"""
Sourcing metadata contracts: the Réceptionniste IA target verticals.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SourcingVerticalResponse(BaseModel):
    """A target vertical offered as a search preset in the dashboard."""

    key: str = Field(..., description="Stable vertical identifier (e.g. 'couvreur')")
    label: str = Field(..., description="Display label (e.g. 'Couvreurs')")
    wave: int = Field(..., ge=1, description="Prospection wave: 1 first, then 2, then 3")
    search_terms: list[str] = Field(..., description="Google Maps categories to search, one job each")
