"""Pydantic schemas for prospect enrichment data."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class ProspectEnrichmentResponse(BaseModel):
    """Enrichment data returned to the dashboard."""

    id: int
    prospect_id: int
    status: str
    source: Optional[str] = None
    logo_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    description: Optional[str] = None
    photos: list[str] = Field(default_factory=list)
    reviews: list[dict[str, Any]] = Field(default_factory=list)
    opening_hours: list[dict[str, Any]] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    social_links: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    enriched_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("photos", "reviews", "opening_hours", "services", mode="before")
    @classmethod
    def _none_to_empty_list(cls, value: Any) -> Any:
        """NULL collection columns from the DB are exposed as empty lists."""
        return [] if value is None else value

    @field_validator("social_links", mode="before")
    @classmethod
    def _none_to_empty_dict(cls, value: Any) -> Any:
        """A NULL social_links column from the DB is exposed as an empty dict."""
        return {} if value is None else value

    model_config = {"from_attributes": True}


class ProspectEnrichmentUpdate(BaseModel):
    """Manual edits to enrichment data (add / modify / remove)."""

    logo_url: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    reviews_count: Optional[int] = Field(default=None, ge=0)
    description: Optional[str] = None
    photos: Optional[list[str]] = None
    reviews: Optional[list[dict[str, Any]]] = None
    opening_hours: Optional[list[dict[str, Any]]] = None
    services: Optional[list[str]] = None
    social_links: Optional[dict[str, Any]] = None
