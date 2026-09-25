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


class WebsiteEquipmentScanRequest(BaseModel):
    """Prospects whose website should be scanned for a chat widget and a contact form."""

    prospect_ids: list[int] = Field(..., min_length=1, max_length=500, description="Prospects to scan")


class WebsiteEquipmentScanResponse(BaseModel):
    """How many scans were queued (prospects without a live website are skipped)."""

    scheduled: int = Field(..., ge=0, description="Prospects whose website is being scanned in the background")
