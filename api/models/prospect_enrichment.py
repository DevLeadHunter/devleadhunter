"""Prospect enrichment model — rich data used to fill generated websites.

This is intentionally decoupled from the lightweight search scrapers: enrichment
is gathered on demand (button / before site generation), never during prospect
discovery, so the search scrapers stay fast.
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from enums.enrichment_status import EnrichmentStatus


class ProspectEnrichment(Base):
    """Rich, editable enrichment data attached to a single prospect."""

    __tablename__ = "prospect_enrichments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    prospect_id: Mapped[int] = mapped_column(ForeignKey("prospects.id"), nullable=False, unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=EnrichmentStatus.PENDING.value, index=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Scalar enrichment fields
    # TEXT, not VARCHAR: a Facebook logo is rehosted as a base64 data URI at scrape time (see
    # facebook_enrichment_scraper), which far exceeds any VARCHAR length and would be truncated.
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviews_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Decision-maker contact (resolved by the decision_maker cascade, or set
    # manually). Golden rule: only trusted names land here — the greeting
    # falls back to a plain « Bonjour » when these are empty.
    contact_first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_gender: Mapped[str | None] = mapped_column(String(1), nullable=True)  # 'M' | 'F'
    contact_name_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    contact_name_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    contact_name_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    # How the trusted name was established (ContactNameStatus: auto | confirmed | manual).
    contact_name_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Human-readable justification of the trusted name (shown in the drawer).
    contact_name_provenance: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # SIREN of the registry company the trusted name came from — pre-fills the
    # billing drawer at sale time (Qonto requires the client's SIREN).
    contact_siren: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # « À confirmer » proposal: a plausible but unproven name, waiting for a
    # human confirm/reject in the drawer. NEVER read by email variables — only
    # contact_* feeds « Bonjour {Prénom} ».
    proposed_first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    proposed_last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    proposed_gender: Mapped[str | None] = mapped_column(String(1), nullable=True)  # 'M' | 'F'
    proposed_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    proposed_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    proposed_provenance: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # ProposedContactState: pending | rejected (a rejected identity is never re-proposed).
    proposed_state: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Every candidate of the last cascade run (source, confidence, provenance) —
    # drawer display, threshold calibration and debugging.
    name_candidates: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Identity of the Maps place the data was actually read from (durable
    # anchor — also feeds the cascade's geo when the address has no CP).
    place_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    place_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    place_postal_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Cross-source check registry ↔ Maps place (IdentityCheckStatus + French detail).
    identity_check_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    identity_check_detail: Mapped[str | None] = mapped_column(String(400), nullable=True)

    # Structured, editable collections (JSON)
    photos: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reviews: Mapped[list | None] = mapped_column(JSON, nullable=True)
    opening_hours: Mapped[list | None] = mapped_column(JSON, nullable=True)
    services: Mapped[list | None] = mapped_column(JSON, nullable=True)
    social_links: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # What each photo shows, read once by the vision model and keyed by photo URL:
    # ``{url: {"kind": "dish" | "truck" | "menu_board" | …, "description", "dishes", "appeal"}}``.
    # Lets site generation and the specialties editor pick real dish photos (never the truck on a
    # menu card) and read the dishes off photographed menu boards. NULL until first labelled.
    photo_labels: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    enriched_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)

    def __repr__(self) -> str:
        return f"<ProspectEnrichment id={self.id} prospect_id={self.prospect_id} status={self.status}>"
