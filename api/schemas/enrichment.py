"""Pydantic schemas for prospect enrichment data."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProspectEnrichmentResponse(BaseModel):
    """Enrichment data returned to the dashboard."""

    id: int
    prospect_id: int
    status: str
    source: str | None = None
    logo_url: str | None = None
    rating: float | None = None
    reviews_count: int | None = None
    description: str | None = None
    photos: list[str] = Field(default_factory=list)
    reviews: list[dict[str, Any]] = Field(default_factory=list)
    opening_hours: list[dict[str, Any]] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    social_links: dict[str, Any] = Field(default_factory=dict)
    # Vision labels keyed by photo URL: {"kind", "description", "dishes", "appeal"} (empty until labelled).
    photo_labels: dict[str, Any] = Field(default_factory=dict)
    # Decision-maker contact (resolved by the cascade, or set manually).
    contact_first_name: str | None = None
    contact_last_name: str | None = None
    contact_gender: str | None = None
    contact_name_source: str | None = None
    contact_name_confidence: float | None = None
    contact_name_manual: bool = False
    contact_name_status: str | None = None
    contact_name_provenance: str | None = None
    contact_siren: str | None = None
    # « À confirmer » proposal — plausible name waiting for a human confirm/reject.
    proposed_first_name: str | None = None
    proposed_last_name: str | None = None
    proposed_gender: str | None = None
    proposed_source: str | None = None
    proposed_confidence: float | None = None
    proposed_provenance: str | None = None
    proposed_state: str | None = None
    # Every candidate of the last cascade run (drawer display + calibration).
    name_candidates: list[dict[str, Any]] = Field(default_factory=list)
    # Maps place identity + cross-source check (registry ↔ place).
    place_title: str | None = None
    place_city: str | None = None
    place_postal_code: str | None = None
    identity_check_status: str | None = None
    identity_check_detail: str | None = None
    error_message: str | None = None
    enriched_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("photos", "reviews", "opening_hours", "services", "name_candidates", mode="before")
    @classmethod
    def _none_to_empty_list(cls, value: Any) -> Any:
        """NULL collection columns from the DB are exposed as empty lists."""
        return [] if value is None else value

    @field_validator("social_links", "photo_labels", mode="before")
    @classmethod
    def _none_to_empty_dict(cls, value: Any) -> Any:
        """A NULL dict column from the DB is exposed as an empty dict."""
        return {} if value is None else value

    model_config = ConfigDict(from_attributes=True)


class ProspectEnrichmentUpdate(BaseModel):
    """Manual edits to enrichment data (add / modify / remove)."""

    logo_url: str | None = None
    rating: float | None = Field(default=None, ge=0, le=5)
    reviews_count: int | None = Field(default=None, ge=0)
    description: str | None = None
    photos: list[str] | None = None
    reviews: list[dict[str, Any]] | None = None
    opening_hours: list[dict[str, Any]] | None = None
    services: list[str] | None = None
    social_links: dict[str, Any] | None = None
    contact_first_name: str | None = None
    contact_last_name: str | None = None
