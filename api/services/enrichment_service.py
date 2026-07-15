"""
Prospect enrichment orchestration.

Separate from prospect discovery: enrichment is gathered on demand (button /
before site generation), is fully editable, and is mapped into the generated
site content (content_json → Storyblok) at build time.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from enums.enrichment_status import EnrichmentStatus
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from scrappers import scrape_signals
from scrappers.enrichment_scraper import EnrichmentData, enrichment_scraper
from services.enrichment_content import apply_to_content as _apply_to_content
from services.scraper_diagnostics_service import (
    STATUS_BLOCKED,
    STATUS_EMPTY,
    STATUS_ERROR,
    STATUS_OK,
    scraper_diagnostics_service,
)

logger = logging.getLogger(__name__)

def _count_filled_fields(data: Optional[EnrichmentData]) -> int:
    """Number of rich enrichment fields actually populated (0 = quietly empty)."""
    if data is None:
        return 0
    scalars = [data.rating, data.reviews_count, data.description, data.logo_url]
    collections = [data.photos, data.reviews, data.opening_hours, data.services, data.social_links]
    return sum(1 for value in scalars if value) + sum(1 for value in collections if value)


# Fields a client is allowed to edit manually on an enrichment record.
EDITABLE_FIELDS: tuple[str, ...] = (
    "logo_url",
    "rating",
    "reviews_count",
    "description",
    "photos",
    "reviews",
    "opening_hours",
    "services",
    "social_links",
)


class EnrichmentService:
    """Manages rich enrichment data and its mapping into site content."""

    def get_prospect_for_user(
        self, db: Session, user_id: int, prospect_id: int
    ) -> Optional[ProspectDB]:
        """Fetch a prospect owned by the user."""
        return (
            db.query(ProspectDB)
            .filter(ProspectDB.id == prospect_id, ProspectDB.user_id == user_id)
            .first()
        )

    def get_for_prospect(
        self, db: Session, user_id: int, prospect_id: int
    ) -> Optional[ProspectEnrichment]:
        """Return the enrichment record for a prospect owned by the user."""
        return (
            db.query(ProspectEnrichment)
            .filter(
                ProspectEnrichment.prospect_id == prospect_id,
                ProspectEnrichment.user_id == user_id,
            )
            .first()
        )

    def get_or_create(
        self, db: Session, user_id: int, prospect_id: int
    ) -> ProspectEnrichment:
        """Get the enrichment record, creating an empty one if needed."""
        record = self.get_for_prospect(db, user_id, prospect_id)
        if record:
            return record
        record = ProspectEnrichment(
            prospect_id=prospect_id,
            user_id=user_id,
            status=EnrichmentStatus.PENDING.value,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    def _apply_data(self, record: ProspectEnrichment, data: EnrichmentData) -> None:
        """Copy scraped data onto the record without wiping manual edits with blanks."""
        record.source = data.source or record.source
        if data.rating is not None:
            record.rating = data.rating
        if data.reviews_count is not None:
            record.reviews_count = data.reviews_count
        if data.description:
            record.description = data.description
        if data.logo_url:
            record.logo_url = data.logo_url
        if data.photos:
            record.photos = data.photos
        if data.reviews:
            record.reviews = data.reviews
        if data.opening_hours:
            record.opening_hours = data.opening_hours
        if data.services:
            record.services = data.services
        if data.social_links:
            record.social_links = data.social_links

    async def enrich(
        self, db: Session, user_id: int, prospect: ProspectDB
    ) -> ProspectEnrichment:
        """Run the enrichment scraper for a prospect and persist the result."""
        record = self.get_or_create(db, user_id, prospect.id)
        record.status = EnrichmentStatus.ENRICHING.value
        record.error_message = None
        db.commit()

        try:
            data = await enrichment_scraper.enrich(
                business_name=prospect.name,
                city=prospect.city,
            )
            self._apply_data(record, data)
            record.status = EnrichmentStatus.COMPLETED.value
            record.enriched_at = datetime.now(timezone.utc)
            self._record_diagnostic(prospect, data, error=None)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Enrichment failed for prospect_id=%s", prospect.id)
            record.status = EnrichmentStatus.FAILED.value
            record.error_message = str(exc)
            self._record_diagnostic(prospect, None, error=str(exc))

        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def _record_diagnostic(
        prospect: ProspectDB, data: Optional[EnrichmentData], error: Optional[str]
    ) -> None:
        """Record the enrichment outcome for the admin monitoring page (never silent).

        Counts how many rich fields were actually filled so a quietly-empty enrichment
        (the ``EnrichmentData()`` that used to pass unnoticed) surfaces as an incident.
        """
        block = scrape_signals.pop_block("enrichment")
        if error is not None:
            status, filled, html = STATUS_ERROR, 0, (block["html"] if block else None)
        else:
            filled = _count_filled_fields(data)
            if filled > 0:
                status, html = STATUS_OK, None
            elif block is not None:
                status, html, error = STATUS_BLOCKED, block["html"], block["reason"]
            else:
                status, html = STATUS_EMPTY, None
        scraper_diagnostics_service.record(
            source="enrichment",
            status=status,
            category=prospect.category,
            city=prospect.city,
            results_count=filled,
            error_message=error,
            html_snapshot=html,
            user_id=prospect.user_id,
        )

    async def ensure_enriched(
        self, db: Session, user_id: int, prospect: ProspectDB
    ) -> ProspectEnrichment:
        """Return a completed enrichment, running it once if not done yet."""
        record = self.get_for_prospect(db, user_id, prospect.id)
        if record and record.status == EnrichmentStatus.COMPLETED.value:
            return record
        return await self.enrich(db, user_id, prospect)

    def update(
        self, db: Session, record: ProspectEnrichment, updates: dict[str, Any]
    ) -> ProspectEnrichment:
        """Apply manual edits (add / modify / remove fields) to an enrichment record."""
        for key, value in updates.items():
            if key in EDITABLE_FIELDS:
                setattr(record, key, value)
        # A manually edited record is considered ready to use.
        if record.status != EnrichmentStatus.COMPLETED.value:
            record.status = EnrichmentStatus.COMPLETED.value
        db.commit()
        db.refresh(record)
        return record

    # ------------------------------------------------------------------ #
    # Mapping enrichment → site content
    # ------------------------------------------------------------------ #

    def to_dict(self, record: Optional[ProspectEnrichment]) -> Optional[dict[str, Any]]:
        """Serialize an enrichment record into a plain dict for content mapping."""
        if not record:
            return None
        return {
            "logo_url": record.logo_url,
            "rating": record.rating,
            "reviews_count": record.reviews_count,
            "description": record.description,
            "photos": record.photos or [],
            "reviews": record.reviews or [],
            "opening_hours": record.opening_hours or [],
            "services": record.services or [],
            "social_links": record.social_links or {},
        }

    def apply_to_content(
        self, content_json: dict[str, Any], enrichment: Optional[dict[str, Any]]
    ) -> dict[str, Any]:
        """Merge enrichment data into a template's content_json (see enrichment_content)."""
        return _apply_to_content(content_json, enrichment)


enrichment_service = EnrichmentService()
