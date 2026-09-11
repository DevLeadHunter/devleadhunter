"""
Prospect data models.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from enums.source import Source
from enums.website_status import WebsiteStatus


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
    address: str | None = Field(None, description="Street address")
    city: str | None = Field(None, description="City name")
    phone: str | None = Field(None, description="Phone number")
    email: EmailStr | None = Field(None, description="Email address")
    website: str | None = Field(None, description="Website URL")
    website_status: WebsiteStatus | None = Field(
        None,
        description=(
            "Liveness of the found website: live, dead (DNS/4xx/5xx/error page) or "
            "placeholder (directory mini-site). None when no website or never checked."
        ),
    )
    google_maps_url: str | None = Field(
        None,
        max_length=2048,
        description=(
            "Google Maps place URL captured at discovery — anchors enrichment on the "
            "exact listing instead of re-searching by name (homonym safety)."
        ),
    )
    facebook_url: str | None = Field(
        None,
        max_length=2048,
        description=(
            "Facebook page URL — enrichment anchor used when the prospect has no Google "
            "listing. Google Maps stays the source of truth when both are present."
        ),
    )
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

    social_url: str | None = Field(
        None,
        description=(
            "Transient: Facebook / Instagram profile URL extracted from PagesJaunes. "
            "Used during email enrichment; never written to the database."
        ),
    )


class ProspectEnrichRequest(BaseModel):
    """Request payload to pre-fill a prospect from Google Maps."""

    business_name: str | None = Field(None, max_length=255, description="Business name")
    google_maps_url: str | None = Field(None, max_length=2048, description="Google Maps place URL")
    city: str | None = Field(None, max_length=128, description="City hint for business name search")


class ProspectSearchSuggestionsRequest(BaseModel):
    """Request payload to search businesses on Google Maps."""

    query: str = Field(..., min_length=2, max_length=255, description="Business name search query")
    city: str | None = Field(None, max_length=128, description="City hint")
    max_results: int = Field(default=8, ge=1, le=15, description="Maximum suggestions to return")


class ProspectSearchSuggestion(BaseModel):
    """A Google Maps business suggestion for autocomplete."""

    id: str = Field(..., description="Unique suggestion id (Google Maps URL)")
    label: str = Field(..., description="Business display name")
    description: str | None = Field(None, description="Address or secondary line")
    google_maps_url: str = Field(..., description="Google Maps place URL")


class ProspectUpdate(BaseModel):
    """
    Model for updating an existing prospect.

    All fields are optional to allow partial updates.
    """

    name: str | None = Field(None, description="Business name")
    address: str | None = Field(None, description="Street address")
    city: str | None = Field(None, description="City name")
    phone: str | None = Field(None, description="Phone number")
    email: EmailStr | None = Field(None, description="Email address")
    website: str | None = Field(None, description="Website URL")
    website_status: WebsiteStatus | None = Field(None, description="Liveness of the website URL")
    facebook_url: str | None = Field(None, max_length=2048, description="Facebook page URL")
    google_maps_url: str | None = Field(None, max_length=2048, description="Google Maps place URL")
    category: str | None = Field(None, description="Business category")
    source: Source | None = Field(None, description="Data source identifier")
    confidence: int | None = Field(None, ge=1, le=4, description="Confidence score 1-4")
    contacted: bool | None = Field(None, description="Whether this prospect has been contacted")


class ProspectEmailsUpdate(BaseModel):
    """Replace a prospect's full ordered email list (first entry = primary).

    The client sends the whole list, so this single payload covers reorder, add and remove.
    """

    emails: list[EmailStr] = Field(
        default_factory=list,
        description="Ordered emails; the first one becomes the primary shown in the table and used to send.",
    )


class ProspectPhonesUpdate(BaseModel):
    """Replace a prospect's full ordered phone list (first entry = primary).

    The client sends the whole list, so this single payload covers reorder, add and remove.
    """

    phones: list[str] = Field(
        default_factory=list,
        description="Ordered numbers; the first one becomes the primary shown in the table and used for SMS.",
    )


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
    emails: list[str] | None = Field(
        None,
        description="All known emails, ordered; emails[0] is the primary (mirrors the `email` field).",
    )
    phones: list[str] | None = Field(
        None,
        description="All known numbers, ordered; phones[0] is the primary (mirrors the `phone` field).",
    )
    user_id: int = Field(..., description="User ID who saved this prospect")
    contacted: bool = Field(False, description="Whether this prospect has been contacted")
    created_at: datetime | None = Field(None, description="Timestamp when created")
    organization_id: int | None = Field(None, description="Organization the prospect is shared with (creator's org)")
    reserved_by_user_id: int | None = Field(None, description="Member currently reserving this prospect (None = free)")
    reserved_by_name: str | None = Field(
        None, description="Display name of the reserving member (resolved server-side)"
    )
    reserved_at: datetime | None = Field(None, description="When the reservation was made")
    lighthouse_json: dict | None = Field(None, description="Latest Lighthouse audit of the prospect's existing website")
    lighthouse_at: datetime | None = Field(None, description="When the audit was run")
    has_pending_contact_proposal: bool = Field(
        False,
        description="A decision-maker name awaits confirm/reject in the drawer (resolved server-side)",
    )
    sms_opted_out: bool = Field(
        False,
        description="The prospect replied STOP to an SMS — no more SMS can be sent (resolved server-side)",
    )
    email_unsubscribed: bool = Field(
        False,
        description="The prospect unsubscribed from the cold-email list (resolved server-side)",
    )
    do_not_contact: bool = Field(
        False,
        description="Operator marked « ne plus contacter » — blocks every outreach channel (campaigns + SMS)",
    )
    do_not_contact_reason: str | None = Field(
        None, description="Optional note on why contact was stopped (shown on the held-back queue lines)"
    )
    do_not_contact_at: datetime | None = Field(None, description="When « ne plus contacter » was set")
    email_undeliverable: bool = Field(
        False,
        description="The campaign email bounced with no other address to try — recover the prospect via SMS",
    )
    email_undeliverable_at: datetime | None = Field(None, description="When the email was flagged undeliverable")
    email_undeliverable_reason: str | None = Field(None, description="The bounce reason reported by the provider")
