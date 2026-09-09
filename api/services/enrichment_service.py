"""
Prospect enrichment orchestration.

Separate from prospect discovery: enrichment is gathered on demand (button /
before site generation), is fully editable, and is mapped into the generated
site content (content_json → Storyblok) at build time.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from enums.contact_name_status import ContactNameStatus, ProposedContactState
from enums.enrichment_status import EnrichmentStatus
from enums.identity_check_status import IdentityCheckStatus
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from scrappers import scrape_signals
from scrappers.enrichment_scraper import EnrichmentData, _dedupe_reviews, enrichment_scraper
from scrappers.google_scraper import GoogleScraper
from services.decision_maker.types import NameCandidate, NameResolution
from services.enrichment_content import EnrichmentContentMapper
from services.photo_labeling_service import photo_labeling_service, should_label_for_category
from services.prospect_emails import sync_prospect_emails
from services.prospect_photo_storage_service import prospect_photo_storage
from services.scraper_diagnostics_service import (
    STATUS_BLOCKED,
    STATUS_EMPTY,
    STATUS_ERROR,
    STATUS_OK,
    scraper_diagnostics_service,
)
from services.validation_service import validation_service

logger = logging.getLogger(__name__)

_POSTAL_CODE_RE = re.compile(r"\b(\d{5})\b")

# Registre/Pappers are shared rate-limited APIs — a scraping job must not fire dozens of lookups at once.
_CONTACT_RESOLUTION_SEMAPHORE = asyncio.Semaphore(2)


def _count_filled_fields(data: EnrichmentData | None) -> int:
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
    "contact_first_name",
    "contact_last_name",
)

# Manual contact edits flip these bookkeeping fields (human input always wins).
_CONTACT_FIELDS: tuple[str, ...] = ("contact_first_name", "contact_last_name")


class EnrichmentService:
    """Manages rich enrichment data and its mapping into site content."""

    def get_prospect_for_user(self, db: Session, user_id: int, prospect_id: int) -> ProspectDB | None:
        """Fetch a prospect owned by the user."""
        return db.query(ProspectDB).filter(ProspectDB.id == prospect_id, ProspectDB.user_id == user_id).first()

    def get_for_prospect(self, db: Session, user_id: int, prospect_id: int) -> ProspectEnrichment | None:
        """Return the enrichment record for a prospect owned by the user."""
        return (
            db.query(ProspectEnrichment)
            .filter(
                ProspectEnrichment.prospect_id == prospect_id,
                ProspectEnrichment.user_id == user_id,
            )
            .first()
        )

    def get_or_create(self, db: Session, user_id: int, prospect_id: int) -> ProspectEnrichment:
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

    @staticmethod
    def _all_days_closed(hours: list) -> bool:
        """True when every scraped opening-hours row reads « fermé »/« closed ».

        That is the signal of a temporary holiday shutdown, not a real weekly
        schedule — so the caller keeps the existing hours rather than overwriting
        them with a misleading « closed 7/7 » on the demo site. A schedule that
        merely closes a few days a week has other rows filled, so it returns False.
        """
        rows = [h for h in hours if isinstance(h, dict) and h.get("hours")]
        if not rows:
            return False
        return all(("ferm" in str(h["hours"]).lower() or "closed" in str(h["hours"]).lower()) for h in rows)

    @staticmethod
    def _valid_hour_rows(hours: list | None) -> list[dict[str, str]]:
        """Keep only well-formed opening-hours rows."""
        if not hours:
            return []
        return [
            {"day": str(row["day"]).strip(), "hours": str(row["hours"]).strip()}
            for row in hours
            if isinstance(row, dict) and row.get("day") and row.get("hours")
        ]

    @staticmethod
    def _should_apply_opening_hours(existing: list | None, incoming: list) -> bool:
        """True when incoming hours are usable and at least as complete as existing."""
        if EnrichmentService._all_days_closed(incoming):
            return False
        incoming_rows: list[dict[str, str]] = EnrichmentService._valid_hour_rows(incoming)
        if not incoming_rows:
            return False
        existing_rows: list[dict[str, str]] = EnrichmentService._valid_hour_rows(existing)
        if not existing_rows:
            return True
        return len(incoming_rows) >= len(existing_rows)

    @staticmethod
    def _merge_reviews(existing: list | None, incoming: list) -> list[dict[str, Any]]:
        """Append new review snippets without dropping existing ones or re-adding the same author."""
        merged_source: list[dict[str, Any]] = [row for row in (existing or []) if isinstance(row, dict)]
        merged_source.extend(row for row in incoming if isinstance(row, dict))
        return _dedupe_reviews(merged_source)

    def _apply_data(self, record: ProspectEnrichment, data: EnrichmentData) -> None:
        """Copy the scraped data onto the record. « Relancer l'enrichissement » is a REFRESH: the
        scrape-derived blurb and gallery are replaced (a fresh empty description clears the previous
        stale one, photos are the new identity-deduped set), not merely filled when the record is blank.
        """
        record.source = data.source or record.source
        if data.rating is not None:
            record.rating = data.rating
        if data.reviews_count is not None:
            record.reviews_count = data.reviews_count
        # Description: a re-run REFRESHES the blurb. When the fresh scrape yields nothing usable (weak
        # Facebook page → the « X J'aime · category » meta is stripped to empty), CLEAR the previous
        # value instead of keeping the stale/wrong one forever (Léo prefers empty over wrong).
        if data.description and not validation_service.is_generic_platform_description(data.description):
            record.description = data.description
        else:
            record.description = None
        if data.logo_url:
            record.logo_url = data.logo_url
        if data.photos:
            # A re-run REFRESHES the gallery: replace with the fresh, identity-deduped scrape (Google
            # first, Facebook appended) — no forever-union of stale URLs, no image-size duplicates.
            record.photos = list(data.photos)[:40]
        if data.reviews:
            # Facebook re-scrapes often start from a single stale DOM review; prefer
            # a fuller incoming list instead of forever appending the first one.
            if (data.source or "").startswith("facebook") and len(data.reviews) >= len(record.reviews or []):
                record.reviews = list(data.reviews)
            else:
                record.reviews = self._merge_reviews(record.reviews, data.reviews)
            # Same Facebook author often comes back with extra DOM chrome on a relance.
            record.reviews = _dedupe_reviews(record.reviews)
        if data.opening_hours and self._should_apply_opening_hours(record.opening_hours, data.opening_hours):
            record.opening_hours = self._valid_hour_rows(data.opening_hours)
        if data.services:
            record.services = data.services
        if data.social_links:
            record.social_links = data.social_links
        if data.place_title:
            record.place_title = data.place_title
        if data.place_city:
            record.place_city = data.place_city
        if data.place_postal_code:
            record.place_postal_code = data.place_postal_code

    async def enrich(
        self,
        db: Session,
        user_id: int,
        prospect: ProspectDB,
        scraped_data: EnrichmentData | None = None,
    ) -> ProspectEnrichment:
        """Persist enrichment for a prospect, scraping it here only when needed.

        Args:
            db: Active database session.
            user_id: Owner of the prospect.
            prospect: Prospect being enriched.
            scraped_data: Result already scraped by the desktop sidecar. When set,
                nothing is scraped here — Google blocks datacenter IPs, so the
                desktop app scrapes from the user's own connection and posts the
                outcome. ``None`` keeps the server-side scrape (web build).

        Returns:
            The persisted enrichment record.
        """
        record = self.get_or_create(db, user_id, prospect.id)
        record.status = EnrichmentStatus.ENRICHING.value
        record.error_message = None
        db.commit()

        try:
            data = scraped_data or await enrichment_scraper.enrich(
                business_name=prospect.name,
                city=prospect.city,
                google_maps_url=prospect.google_maps_url,
                facebook_url=prospect.facebook_url,
            )
            # A Facebook-anchored scrape that carries NOTHING did not read the page (the
            # scraper degrades to an empty payload when the browser is unavailable or the
            # page is walled). Persisting it as success would poison every consumer — the
            # discovery match filter would blacklist the page as « no email » without ever
            # having read it — so emptiness is an explicit failure.
            if self._facebook_scrape_is_empty(prospect, data):
                logger.warning("Facebook enrichment returned an empty payload for prospect_id=%s", prospect.id)
                record.status = EnrichmentStatus.FAILED.value
                record.error_message = (
                    "Page Facebook illisible (navigateur indisponible ou page bloquée) — relancez l'enrichissement."
                )
                self._record_diagnostic(prospect, None, error="facebook scrape returned an empty payload")
                db.commit()
                db.refresh(record)
                return record
            # The homonym guard is a « nom + ville » SEARCH safeguard (it opens the first result, which
            # could be a homonym). When the scrape is anchored on an EXACT source — a Facebook page pasted
            # for this prospect, or the Maps place URL stored at discovery — the listing is guaranteed
            # right, so the guard is skipped (it was wrongly rejecting owners who stuff prices into the
            # Maps name, e.g. « … Coupe Adulte 23€ »).
            mismatch = None if self._anchored_on_exact_listing(prospect, data) else self._place_mismatch(prospect, data)
            if mismatch is not None:
                # An explicit failure beats silently absorbing a homonym's
                # photos/reviews into the prospect's demo site.
                logger.warning("Enrichment identity mismatch for prospect_id=%s: %s", prospect.id, mismatch)
                record.status = EnrichmentStatus.FAILED.value
                record.error_message = f"{mismatch}. Données rejetées — relancez ou éditez manuellement."
                self._record_diagnostic(prospect, None, error=mismatch)
            else:
                # Facebook photos arrive as short-lived signed fbcdn URLs; the scraper captured the
                # usable ones as base64 data URIs. Move them to permanent R2 storage now, so the record
                # (and every later re-generation) holds durable URLs instead of links that die in days.
                data.photos = await prospect_photo_storage.rehost_photos(prospect.id, data.photos)
                if data.logo_url:
                    data.logo_url = await prospect_photo_storage.rehost_one(prospect.id, data.logo_url)
                self._apply_data(record, data)
                # A Facebook page on the Maps listing (as the "website" link or a social link) is not a
                # real website — capture it as the prospect's facebook_url so a later complementary
                # Facebook enrichment can recover a second contact email (e.g. contact@…).
                facebook_url = self._facebook_url_from_data(data)
                if facebook_url and not (prospect.facebook_url or "").strip():
                    prospect.facebook_url = facebook_url
                    db.add(prospect)
                    logger.info("Enrichment found a Facebook page for prospect_id=%s: %s", prospect.id, facebook_url)
                # Fold any discovered email (typically from the Facebook page) into the multi-email list,
                # and backfill the list from the existing single email on first pass.
                emails = getattr(data, "emails", None) or []
                if emails or not prospect.emails:
                    sync_prospect_emails(prospect, add=emails)
                    db.add(prospect)
                # A re-run must not leave a stale social page (Instagram, TikTok…) parked in the website
                # field from an earlier enrichment or import — demote it first so it gets re-evaluated.
                if (prospect.website or "").strip() and not validation_service.is_valid_website(prospect.website):
                    logger.info("Enrichment demoted a social page stored as website for prospect_id=%s", prospect.id)
                    prospect.website = None
                    db.add(prospect)
                # Double-check for a website: a REAL one on the Maps listing means the prospect isn't
                # the « no website » target after all — fill it in when we had none. Social pages
                # (Instagram, TikTok, Facebook…) are NOT websites: is_valid_website rejects them all,
                # so an Instagram-only food truck never gets wrongly flagged as « has a site ».
                website = (data.website or "").strip()
                if website and validation_service.is_valid_website(website) and not (prospect.website or "").strip():
                    prospect.website = website
                    db.add(prospect)
                    logger.info("Enrichment found a website for prospect_id=%s: %s", prospect.id, website)
                # Phone from the page (Facebook « Coordonnées ») — Facebook-discovered prospects
                # start with no contact data at all, so the enrichment fills the gap.
                phone = (getattr(data, "phone", None) or "").strip()
                if phone and not (prospect.phone or "").strip():
                    prospect.phone = phone
                    db.add(prospect)
                    logger.info("Enrichment found a phone for prospect_id=%s", prospect.id)
                record.status = EnrichmentStatus.COMPLETED.value
                record.enriched_at = datetime.now(UTC)
                self._record_diagnostic(prospect, data, error=None)
        except Exception as exc:
            logger.exception("Enrichment failed for prospect_id=%s", prospect.id)
            record.status = EnrichmentStatus.FAILED.value
            record.error_message = str(exc)
            self._record_diagnostic(prospect, None, error=str(exc))

        db.commit()

        # Photo labelling (vision, best-effort, in the background) for food trades, so site generation
        # and the specialties editor know which photos show a dish. Other trades label on demand.
        if record.status == EnrichmentStatus.COMPLETED.value and should_label_for_category(prospect.category):
            photo_labeling_service.schedule(prospect.id)

        # Decision-maker name resolution (best-effort, never blocks enrichment).
        await self._resolve_contact(db, prospect, record)

        db.refresh(record)
        return record

    @staticmethod
    def _facebook_scrape_is_empty(prospect: ProspectDB, data: EnrichmentData) -> bool:
        """Whether a Facebook-anchored scrape came back with no substance at all.

        A readable public page always yields at least its title (the ``h1``); a payload
        with none of the substance fields means the page was never actually read.

        Args:
            prospect: The prospect being enriched.
            data: The scraped payload.

        Returns:
            ``True`` when the payload must be treated as a scrape failure.
        """
        if not (prospect.facebook_url or "").strip() or not (data.source or "").startswith("facebook"):
            return False
        return not any(
            [
                (data.place_title or "").strip(),
                (data.description or "").strip(),
                data.photos,
                data.emails,
                data.reviews,
                data.rating is not None,
                data.social_links,
                (data.website or "").strip(),
                (data.logo_url or "").strip(),
            ]
        )

    @staticmethod
    def _facebook_url_from_data(data: object) -> str | None:
        """Extract a Facebook page URL from scraped enrichment, or None.

        Prefers an explicit social link; falls back to the Maps "website" link when it points to
        ``facebook.com`` (a common case for businesses whose only web presence is a Facebook page).
        """
        social = getattr(data, "social_links", None)
        candidate = social.get("facebook") if isinstance(social, dict) else None
        if not candidate:
            website = str(getattr(data, "website", "") or "")
            if "facebook.com/" in website.lower():
                candidate = website
        candidate = str(candidate or "").strip()
        return candidate or None

    async def _resolve_contact(self, db: Session, prospect: ProspectDB, record: ProspectEnrichment) -> None:
        """Run the decision-maker cascade and persist its 3-way outcome.

        AUTO writes the trusted contact; PROPOSED fills the « à confirmer »
        fields (never used in emails until confirmed); NONE clears a previous
        machine-set name. A human-set or human-confirmed name always wins and
        is never touched here. Any failure is swallowed + surfaced as a
        monitoring diagnostic — a broken resolution must never break
        enrichment or sending.
        """
        if record.contact_name_manual or record.contact_name_status in (
            ContactNameStatus.MANUAL.value,
            ContactNameStatus.CONFIRMED.value,
        ):
            return
        try:
            from services.decision_maker.resolver import (
                context_from_prospect,
                decision_maker_resolver,
            )

            resolution = await decision_maker_resolver.resolve(context_from_prospect(prospect, record))
            record.name_candidates = [candidate.to_persistable() for candidate in resolution.candidates]

            # Shared entity check: the registry match and the Maps place must
            # designate the same business — a conflict blocks automatic use.
            status_to_apply = resolution.status
            check_status, check_detail = self._identity_check(record, resolution.candidate)
            record.identity_check_status = check_status
            record.identity_check_detail = check_detail
            if status_to_apply == NameResolution.AUTO and check_status == IdentityCheckStatus.CONFLICT.value:
                status_to_apply = NameResolution.PROPOSED

            if status_to_apply == NameResolution.AUTO and resolution.candidate is not None:
                self._store_trusted_contact(record, resolution.candidate)
            elif status_to_apply == NameResolution.PROPOSED and resolution.candidate is not None:
                self._store_proposed_contact(record, resolution.candidate)
            else:
                self._clear_machine_contact(record)
                # The cascade no longer backs the pending proposal — withdraw it
                # (a REJECTED marker survives so the identity never comes back).
                if record.proposed_state == ProposedContactState.PENDING.value:
                    self._clear_proposed_contact(record)
            db.commit()
            scraper_diagnostics_service.record(
                source="decision_maker",
                status=STATUS_OK if resolution.candidate is not None else STATUS_EMPTY,
                category=prospect.category,
                city=prospect.city,
                results_count=1 if resolution.candidate is not None else 0,
                error_message=self._resolution_outcome_detail(status_to_apply, resolution.candidate),
                html_snapshot=None,
                user_id=prospect.user_id,
            )
        except Exception as exc:
            logger.warning("Decision-maker resolution failed for prospect %s: %s", prospect.id, exc)
            scraper_diagnostics_service.record(
                source="decision_maker",
                status=STATUS_ERROR,
                category=prospect.category,
                city=prospect.city,
                results_count=0,
                error_message=str(exc),
                html_snapshot=None,
                user_id=prospect.user_id,
            )

    @staticmethod
    def _store_trusted_contact(record: ProspectEnrichment, candidate: NameCandidate) -> None:
        """Write an AUTO-grade candidate as the trusted contact (emails use it)."""
        record.contact_first_name = candidate.first
        record.contact_last_name = candidate.last
        record.contact_gender = candidate.gender
        record.contact_name_source = candidate.source
        record.contact_name_confidence = candidate.confidence
        record.contact_name_status = ContactNameStatus.AUTO.value
        record.contact_name_provenance = candidate.provenance or None
        record.contact_siren = EnrichmentService._candidate_siren(candidate)
        EnrichmentService._clear_proposed_contact(record)

    @staticmethod
    def _store_proposed_contact(record: ProspectEnrichment, candidate: NameCandidate) -> None:
        """Surface a PROPOSED-grade candidate for human confirm/reject.

        A previously rejected identity is never re-proposed — the rejection
        would otherwise reappear at every enrichment re-run. A previous
        machine-trusted name is cleared: under the new rules it no longer
        qualifies for automatic use.
        """
        already_rejected = (
            record.proposed_state == ProposedContactState.REJECTED.value
            and (record.proposed_first_name or "") == (candidate.first or "")
            and (record.proposed_last_name or "") == (candidate.last or "")
        )
        EnrichmentService._clear_machine_contact(record)
        if already_rejected:
            return
        record.proposed_first_name = candidate.first
        record.proposed_last_name = candidate.last
        record.proposed_gender = candidate.gender
        record.proposed_source = candidate.source
        record.proposed_confidence = candidate.confidence
        record.proposed_provenance = candidate.provenance or None
        record.proposed_state = ProposedContactState.PENDING.value
        record.contact_siren = EnrichmentService._candidate_siren(candidate)

    @staticmethod
    def _candidate_siren(candidate: NameCandidate) -> str | None:
        """SIREN of the registry company the candidate came from, when any."""
        siren = str(candidate.raw.get("siren") or "") if candidate.raw else ""
        return siren or None

    @staticmethod
    def _clear_machine_contact(record: ProspectEnrichment) -> None:
        """Drop a machine-resolved trusted name (manual/confirmed never reach here).

        The SIREN goes with it: it belonged to the discarded identity's company
        and must not pre-fill a billing form for someone else.
        """
        record.contact_first_name = None
        record.contact_last_name = None
        record.contact_gender = None
        record.contact_name_source = None
        record.contact_name_confidence = None
        record.contact_name_status = None
        record.contact_name_provenance = None
        record.contact_siren = None

    @staticmethod
    def _clear_proposed_contact(record: ProspectEnrichment) -> None:
        """Wipe the proposal fields (after promotion, withdrawal or override)."""
        record.proposed_first_name = None
        record.proposed_last_name = None
        record.proposed_gender = None
        record.proposed_source = None
        record.proposed_confidence = None
        record.proposed_provenance = None
        record.proposed_state = None

    def schedule_contact_resolution(self, prospect_ids: list[int]) -> None:
        """Fire-and-forget decision-maker resolution for freshly saved prospects.

        Called right after a prospect is persisted (search, scraping job, manual
        creation) so the name is already there when the drawer opens — no manual
        « Rechercher automatiquement » click needed. Never blocks the caller.
        """
        if prospect_ids:
            asyncio.create_task(self._resolve_contacts_in_background(list(prospect_ids)))

    async def _resolve_contacts_in_background(self, prospect_ids: list[int]) -> None:
        """Resolve decision-makers on a fresh DB session, throttled globally.

        Prospects whose contact was already settled (manual, confirmed, auto,
        pending/rejected proposal) are skipped — only untouched ones cost a
        registry lookup.
        """
        from core.database import SessionLocal

        for prospect_id in prospect_ids:
            async with _CONTACT_RESOLUTION_SEMAPHORE:
                db: Session = SessionLocal()
                try:
                    prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
                    if prospect is None:
                        continue
                    record = self.get_or_create(db, prospect.user_id, prospect.id)
                    already_settled = (
                        record.contact_name_manual
                        or record.contact_name_status is not None
                        or record.proposed_state is not None
                    )
                    if already_settled:
                        continue
                    await self._resolve_contact(db, prospect, record)
                except Exception as exc:
                    logger.warning("Background contact resolution failed for prospect %s: %s", prospect_id, exc)
                finally:
                    db.close()

    async def resolve_contact(self, db: Session, user_id: int, prospect: ProspectDB) -> ProspectEnrichment:
        """(Re)run only the decision-maker resolution for a prospect (on demand)."""
        record = self.get_or_create(db, user_id, prospect.id)
        # An explicit re-run overrides previous manual/confirmed/rejected locks on purpose.
        record.contact_name_manual = False
        record.contact_name_status = None
        record.proposed_state = None
        await self._resolve_contact(db, prospect, record)
        db.refresh(record)
        return record

    def confirm_proposed_contact(self, db: Session, record: ProspectEnrichment) -> ProspectEnrichment:
        """Promote the pending proposal to the trusted contact (human decision).

        Raises:
            ValueError: When no pending proposal exists on the record.
        """
        if record.proposed_state != ProposedContactState.PENDING.value or not (
            record.proposed_first_name or record.proposed_last_name
        ):
            raise ValueError("Aucun décisionnaire « à confirmer » sur ce prospect")
        record.contact_first_name = record.proposed_first_name
        record.contact_last_name = record.proposed_last_name
        record.contact_gender = record.proposed_gender
        record.contact_name_source = record.proposed_source
        record.contact_name_confidence = record.proposed_confidence
        record.contact_name_status = ContactNameStatus.CONFIRMED.value
        record.contact_name_provenance = record.proposed_provenance
        self._clear_proposed_contact(record)
        db.commit()
        db.refresh(record)
        return record

    def reject_proposed_contact(self, db: Session, record: ProspectEnrichment) -> ProspectEnrichment:
        """Reject the pending proposal (kept as rejected so it never comes back).

        Raises:
            ValueError: When no pending proposal exists on the record.
        """
        if record.proposed_state != ProposedContactState.PENDING.value:
            raise ValueError("Aucun décisionnaire « à confirmer » sur ce prospect")
        record.proposed_state = ProposedContactState.REJECTED.value
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def _resolution_outcome_detail(status: str, candidate: NameCandidate | None) -> str | None:
        """French one-liner of the cascade outcome, shown on the monitoring page."""
        if candidate is None:
            return None
        percent = round(candidate.confidence * 100)
        name = " ".join(part for part in (candidate.first, candidate.last) if part)
        if status == NameResolution.AUTO:
            return f"Nom validé automatiquement : {name} ({candidate.source}, {percent} %)"
        return f"Nom proposé à confirmation : {name} ({candidate.source}, {percent} %)"

    @staticmethod
    def _identity_check(record: ProspectEnrichment, candidate: NameCandidate | None) -> tuple[str | None, str | None]:
        """Cross-check the registry match against the Maps place identity.

        The place was already validated against the prospect at enrichment time,
        so a registry siège in another département than the place means the
        registry matched a homonym — the name must not be used automatically.

        Returns:
            The (IdentityCheckStatus value, French detail) pair — (None, None)
            when either anchor is missing.
        """
        if candidate is None or not candidate.primary:
            return None, None
        siege_postal = str(candidate.raw.get("siege_postal_code") or "") if candidate.raw else ""
        place_postal = record.place_postal_code or ""
        if len(siege_postal) != 5 or len(place_postal) != 5:
            return None, None
        if siege_postal[:2] == place_postal[:2]:
            return (
                IdentityCheckStatus.COHERENT.value,
                f"Identité croisée : le registre (CP {siege_postal}) et la fiche Google Maps "
                f"(CP {place_postal}) désignent la même zone",
            )
        return (
            IdentityCheckStatus.CONFLICT.value,
            f"Le registre (CP {siege_postal}) et la fiche Google Maps (CP {place_postal}) "
            "ne désignent probablement pas la même entreprise — homonyme possible",
        )

    @staticmethod
    def _anchored_on_exact_listing(prospect: ProspectDB, data: EnrichmentData) -> bool:
        """True when the scrape hit an EXACT source, making the homonym guard (a search safeguard) moot.

        The guard exists only for the « nom + ville » search, which opens the first result and could land
        on a homonym. Two anchors bypass it: a Facebook page pasted for this prospect (``data.source``
        starts with "facebook"), or the Google Maps place URL stored at discovery — the scraper opens that
        exact listing, so its title need not match the prospect name (owners stuff prices into it).
        """
        if (data.source or "").startswith("facebook"):
            return True
        return GoogleScraper.is_maps_url(prospect.google_maps_url or "")

    @staticmethod
    def _place_mismatch(prospect: ProspectDB, data: EnrichmentData) -> str | None:
        """Reject scraped data read from another business's Maps place."""
        postal_match = _POSTAL_CODE_RE.search(prospect.address or "")
        return validation_service.place_identity_mismatch(
            prospect_name=prospect.name or "",
            prospect_city=prospect.city,
            prospect_postal_code=postal_match.group(1) if postal_match else None,
            place_title=data.place_title,
            place_city=data.place_city,
            place_postal_code=data.place_postal_code,
        )

    @staticmethod
    def _record_diagnostic(prospect: ProspectDB, data: EnrichmentData | None, error: str | None) -> None:
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

    async def ensure_enriched(self, db: Session, user_id: int, prospect: ProspectDB) -> ProspectEnrichment:
        """Return a completed enrichment, running it once if not done yet."""
        record = self.get_for_prospect(db, user_id, prospect.id)
        if record and record.status == EnrichmentStatus.COMPLETED.value:
            return record
        return await self.enrich(db, user_id, prospect)

    @staticmethod
    def has_unrehostable_photos(record: ProspectEnrichment) -> bool:
        """True when a photo or the logo is still a Facebook-CDN URL the site can't render (needs R2 rehost)."""
        from services.templates.site_content import _is_unrehostable_photo

        candidates: list[object] = list(record.photos or [])
        if record.logo_url:
            candidates.append(record.logo_url)
        return any(isinstance(url, str) and _is_unrehostable_photo(url) for url in candidates)

    async def rehost_existing_photos(self, db: Session, record: ProspectEnrichment) -> ProspectEnrichment:
        """Move a record's already-collected photos to permanent R2 storage, in place, without scraping.

        Repairs an enrichment captured before the R2 rehost, or whose Facebook photos stayed as fbcdn
        URLs — the user's curation (which photos, in which order) is preserved because the stored list is
        rehosted as-is. Each still-live fbcdn URL is downloaded server-side and moved to R2; a Google or
        already-R2 URL is left untouched.

        Args:
            db: Active database session.
            record: The enrichment record to rehost in place.

        Returns:
            The saved record with its photos (and logo) pointing at permanent R2 URLs where possible.
        """
        if record.photos:
            record.photos = await prospect_photo_storage.rehost_photos(record.prospect_id, list(record.photos))
        if record.logo_url:
            record.logo_url = await prospect_photo_storage.rehost_one(record.prospect_id, record.logo_url)
        db.commit()
        db.refresh(record)
        # Labels are keyed by URL: the rehosted photos need theirs again (only when already labelled).
        if record.photo_labels:
            photo_labeling_service.schedule(record.prospect_id)
        return record

    def update(self, db: Session, record: ProspectEnrichment, updates: dict[str, Any]) -> ProspectEnrichment:
        """Apply manual edits (add / modify / remove fields) to an enrichment record."""
        for key, value in updates.items():
            if key in EDITABLE_FIELDS:
                setattr(record, key, value)
        # A human-set contact always wins over automatic resolution.
        if any(key in updates for key in _CONTACT_FIELDS):
            record.contact_name_manual = True
            record.contact_name_source = "manual"
            record.contact_name_confidence = 1.0
            record.contact_name_status = ContactNameStatus.MANUAL.value
            record.contact_name_provenance = None
            # Typing a name settles the question — drop any pending proposal.
            self._clear_proposed_contact(record)
            from services.decision_maker.normalize import infer_gender

            record.contact_gender = infer_gender(record.contact_first_name)
        # A manually edited record is considered ready to use.
        if record.status != EnrichmentStatus.COMPLETED.value:
            record.status = EnrichmentStatus.COMPLETED.value
        db.commit()
        db.refresh(record)
        return record

    # ------------------------------------------------------------------ #
    # Mapping enrichment → site content
    # ------------------------------------------------------------------ #

    def to_dict(self, record: ProspectEnrichment | None) -> dict[str, Any] | None:
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
            "photo_labels": record.photo_labels or {},
        }

    def apply_to_content(self, content_json: dict[str, Any], enrichment: dict[str, Any] | None) -> dict[str, Any]:
        """Merge enrichment data into a template's content_json (see enrichment_content)."""
        return EnrichmentContentMapper.apply_to_content(content_json, enrichment)


enrichment_service = EnrichmentService()
