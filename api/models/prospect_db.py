"""
Prospect database model for SQLAlchemy.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

if TYPE_CHECKING:
    from models.campaign import Campaign


class ProspectDB(Base):
    """
    Prospect database model for storing scraped business data.

    Attributes:
        id: Unique identifier (auto-increment)
        name: Business name
        address: Street address
        city: City name
        phone: Phone number
        email: Email address
        website: Website URL
        category: Business category
        source: Data source (google, pagesjaunes, etc.)
        confidence: Confidence score (1-4)
        user_id: ID of the user who saved this prospect
        created_at: Timestamp when prospect was created
        updated_at: Timestamp when prospect was last updated
    """

    __tablename__ = "prospects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # All known phone numbers, best-first; ``phone`` above stays synced to ``phones[0]`` (the primary).
    phones: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # All known emails, best-first; ``email`` above stays synced to ``emails[0]`` (the primary).
    emails: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Liveness of the found website (WebsiteStatus value, NULL = none/unchecked).
    # Dead/placeholder prospects keep their URL so the verdict can be verified by hand.
    website_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Google Maps place URL captured at discovery — anchors enrichment on the
    # exact listing instead of re-searching by name (homonym safety).
    google_maps_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Facebook page URL — enrichment anchor used when the prospect has no Google listing (Google wins when present).
    facebook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    contacted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0", index=True)
    # Operator decision "ne plus contacter ce prospect" (e.g. he said no by phone). Blocks EVERY
    # outreach channel (campaign enqueue + dispatch, SMS relance/cold). Distinct from the
    # prospect-driven opt-outs (STOP SMS / email unsubscribe), which are resolved server-side, not stored here.
    do_not_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0", index=True)
    do_not_contact_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    do_not_contact_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Email dead-end: the campaign email bounced and no other address could be tried. The prospect
    # stays « contacté » (we DID attempt) but is flagged so the operator can recover it into an SMS
    # campaign. Cleared on the next successful delivery or when the email is edited by hand.
    email_undeliverable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0", index=True
    )
    email_undeliverable_at: Mapped[datetime | None] = mapped_column(nullable=True)
    email_undeliverable_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # Team sharing: set while the creator belongs to an organization → the prospect
    # is visible to every member. Cleared when the creator leaves the org.
    organization_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    # Reservation: one member "takes" the prospect; the others see it locked
    # (anti double-outreach — one prospect, one outreacher).
    reserved_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    reserved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Lighthouse audit of the prospect's EXISTING website (PageSpeed Insights) —
    # feeds the "site améliorable → proposer une refonte" pitch.
    lighthouse_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    lighthouse_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)

    # Relationships
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign", secondary="campaign_prospects", back_populates="prospects"
    )

    def __repr__(self) -> str:
        """String representation of the prospect."""
        return f"<ProspectDB(id={self.id}, name='{self.name}', city='{self.city}', source='{self.source}')>"
