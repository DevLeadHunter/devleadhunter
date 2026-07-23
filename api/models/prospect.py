"""
Prospect data models.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from enums.source import Source


class ProspectBase(BaseModel):
    """
    Base prospect model with common fields.
    
    Attributes:
        name: Business name (required)
        address: Street address (optional)
        city: City name (optional)
        phone: Phone number (optional)
        email: Email address (optional)
        website: Website URL (optional)
        category: Business category (required)
        source: Data source identifier (required)
        confidence: Confidence score between 1 and 4 (required)
    """
    
    name: str = Field(..., min_length=1, description="Business name")
    address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    website: Optional[str] = Field(None, description="Website URL")
    category: str = Field(..., description="Business category")
    source: Source = Field(..., description="Data source identifier")
    confidence: int = Field(
        ...,
        ge=1,
        le=4,
        description="Confidence score 1-4",
        json_schema_extra={"example": 3},
    )


class ProspectCreate(ProspectBase):
    """
    Model for creating a new prospect.

    Inherits all persistent fields from :class:`ProspectBase` and adds
    ``social_url`` — a **transient, in-memory-only** field used during the
    scraping pipeline to carry a Facebook / Instagram profile URL found on
    PagesJaunes.

    ``social_url`` is never persisted to the database: the repository layer
    (``prospect_service.create_prospect``) maps fields explicitly and ignores
    unknown ones.
    """

    social_url: Optional[str] = Field(
        None,
        description=(
            "Transient: Facebook / Instagram profile URL extracted from PagesJaunes. "
            "Used during email enrichment; never written to the database."
        ),
    )


class ProspectEnrichRequest(BaseModel):
    """Request payload to pre-fill a prospect from Google Maps."""

    business_name: Optional[str] = Field(None, max_length=255, description="Business name")
    google_maps_url: Optional[str] = Field(None, max_length=2048, description="Google Maps place URL")
    city: Optional[str] = Field(None, max_length=128, description="City hint for business name search")


class ProspectSearchSuggestionsRequest(BaseModel):
    """Request payload to search businesses on Google Maps."""

    query: str = Field(..., min_length=2, max_length=255, description="Business name search query")
    city: Optional[str] = Field(None, max_length=128, description="City hint")
    max_results: int = Field(default=8, ge=1, le=15, description="Maximum suggestions to return")


class ProspectSearchSuggestion(BaseModel):
    """A Google Maps business suggestion for autocomplete."""

    id: str = Field(..., description="Unique suggestion id (Google Maps URL)")
    label: str = Field(..., description="Business display name")
    description: Optional[str] = Field(None, description="Address or secondary line")
    google_maps_url: str = Field(..., description="Google Maps place URL")


class ProspectUpdate(BaseModel):
    """
    Model for updating an existing prospect.
    
    All fields are optional to allow partial updates.
    """
    
    name: Optional[str] = Field(None, description="Business name")
    address: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    phone: Optional[str] = Field(None, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")
    website: Optional[str] = Field(None, description="Website URL")
    category: Optional[str] = Field(None, description="Business category")
    source: Optional[Source] = Field(None, description="Data source identifier")
    confidence: Optional[int] = Field(None, ge=1, le=4, description="Confidence score 1-4")
    contacted: Optional[bool] = Field(None, description="Whether this prospect has been contacted")


class Prospect(ProspectBase):
    """Complete prospect model with ID and ownership metadata."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 123,
                "name": "Le Bon Restaurant",
                "address": "123 Rue de la Paix",
                "city": "Paris",
                "email": "contact@bonrestaurant.fr",
                "website": "https://www.bonrestaurant.fr",
                "category": "restaurant",
                "source": "google",
                "confidence": 3,
                "phone": "+33123456789",
                "user_id": 1,
                "created_at": "2024-01-15T10:30:00Z",
            }
        },
    )

    id: int = Field(..., description="Unique prospect identifier")
    user_id: int = Field(..., description="User ID who saved this prospect")
    contacted: bool = Field(False, description="Whether this prospect has been contacted")
    created_at: Optional[datetime] = Field(None, description="Timestamp when created")
    organization_id: Optional[int] = Field(
        None, description="Organization the prospect is shared with (creator's org)"
    )
    reserved_by_user_id: Optional[int] = Field(
        None, description="Member currently reserving this prospect (None = free)"
    )
    reserved_by_name: Optional[str] = Field(
        None, description="Display name of the reserving member (resolved server-side)"
    )
    reserved_at: Optional[datetime] = Field(None, description="When the reservation was made")
    lighthouse_json: Optional[dict] = Field(
        None, description="Latest Lighthouse audit of the prospect's existing website"
    )
    lighthouse_at: Optional[datetime] = Field(None, description="When the audit was run")
