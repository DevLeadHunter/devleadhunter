"""Prospect enrichment model — rich data used to fill generated websites.

This is intentionally decoupled from the lightweight search scrapers: enrichment
is gathered on demand (button / before site generation), never during prospect
discovery, so the search scrapers stay fast.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base
from enums.enrichment_status import EnrichmentStatus


class ProspectEnrichment(Base):
    """Rich, editable enrichment data attached to a single prospect."""

    __tablename__ = "prospect_enrichments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    prospect_id: Mapped[int] = mapped_column(
        ForeignKey("prospects.id"), nullable=False, unique=True, index=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=EnrichmentStatus.PENDING.value, index=True
    )
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Scalar enrichment fields
    logo_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    reviews_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structured, editable collections (JSON)
    photos: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    reviews: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    opening_hours: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    services: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    social_links: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enriched_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        return f"<ProspectEnrichment id={self.id} prospect_id={self.prospect_id} status={self.status}>"
