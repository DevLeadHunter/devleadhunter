"""
Prospect data service.
"""

from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from enums.contact_name_status import ProposedContactState
from models.email_unsubscribe import EmailUnsubscribe
from models.prospect import Prospect, ProspectCreate, ProspectUpdate
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from models.search import ProspectSearchRequest
from models.sms_suppression import SmsSuppression
from models.user import User
from services.activity_log_service import CATEGORY_PROSPECT, STATUS_INFO, STATUS_WARNING, activity_log_service
from services.prospect_emails import sync_prospect_emails
from services.sms.phone_normalizer import to_e164_fr
from services.validation_service import ValidationService


def _org_visibility_filter(user_id: int, organization_id: int | None):
    """SQLAlchemy filter: prospects owned by the user OR shared with their org.

    The org side is strictly scoped to ``organization_id`` — a prospect from
    another organization can never match (no cross-org leak).
    """
    if organization_id is None:
        return ProspectDB.user_id == user_id
    return or_(
        ProspectDB.user_id == user_id,
        ProspectDB.organization_id == organization_id,
    )


class ProspectService:
    """
    Service for managing prospect data operations.

    This service handles CRUD operations and search functionality
    for prospects using SQLAlchemy database.
    """

    def __init__(self):
        """Initialize the prospect service."""
        pass

    async def search_prospects(
        self, db: Session, request: ProspectSearchRequest, user_id: int | None = None
    ) -> list[Prospect]:
        """
        Search for prospects based on given criteria.

        Args:
            db: Database session
            request: Search criteria including category, city, and max results
            user_id: Optional user ID to filter prospects by user

        Returns:
            List of matching prospects

        Example:
            >>> request = ProspectSearchRequest(category="restaurant", city="Paris")
            >>> results = await service.search_prospects(db, request)
        """
        query = db.query(ProspectDB)

        # Filter by user if provided
        if user_id is not None:
            query = query.filter(ProspectDB.user_id == user_id)

        # Filter by category (partial match)
        if request.category:
            query = query.filter(ProspectDB.category.ilike(f"%{request.category}%"))

        # Filter by city
        if request.city:
            query = query.filter(ProspectDB.city.ilike(f"%{request.city}%"))

        # Order by creation date (most recent first)
        query = query.order_by(ProspectDB.created_at.desc())

        # Limit results
        db_prospects = query.limit(request.max_results).all()

        # Convert to Pydantic models
        return [Prospect.model_validate(p) for p in db_prospects]

    async def get_all_prospects(
        self,
        db: Session,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 1000,
        organization_id: int | None = None,
    ) -> list[Prospect]:
        """
        Get all prospects visible to a user (their own + their organization's).

        Args:
            db: Database session
            user_id: Optional user ID to filter prospects by user
            skip: Number of records to skip
            limit: Maximum number of records to return
            organization_id: The user's organization (None = personal scope only)

        Returns:
            List of all visible prospects, reservation names resolved
        """
        query = db.query(ProspectDB)

        # Filter by user if provided
        if user_id is not None:
            query = query.filter(_org_visibility_filter(user_id, organization_id))

        # Order by creation date (most recent first)
        query = query.order_by(ProspectDB.created_at.desc())

        db_prospects = query.offset(skip).limit(limit).all()

        return self._to_models_with_reservers(db, db_prospects)

    @staticmethod
    def _to_models_with_reservers(db: Session, db_prospects: list[ProspectDB]) -> list[Prospect]:
        """Convert rows to Pydantic models, resolving ``reserved_by_name`` and
        the pending decision-maker proposal flag in one query each."""
        reserver_ids = {p.reserved_by_user_id for p in db_prospects if p.reserved_by_user_id}
        names: dict[int, str] = {}
        if reserver_ids:
            rows = db.execute(select(User.id, User.name).where(User.id.in_(reserver_ids))).all()
            names = {row[0]: row[1] for row in rows}

        prospect_ids = [p.id for p in db_prospects]
        pending_proposal_ids: set[int] = set()
        if prospect_ids:
            pending_rows = db.execute(
                select(ProspectEnrichment.prospect_id).where(
                    ProspectEnrichment.prospect_id.in_(prospect_ids),
                    ProspectEnrichment.proposed_state == ProposedContactState.PENDING.value,
                )
            ).all()
            pending_proposal_ids = {row[0] for row in pending_rows}

        resolved_opt_outs = ProspectService._resolve_opt_outs(db, db_prospects)

        prospects: list[Prospect] = []
        for db_prospect in db_prospects:
            prospect = Prospect.model_validate(db_prospect)
            if prospect.reserved_by_user_id:
                prospect.reserved_by_name = names.get(prospect.reserved_by_user_id)
            prospect.has_pending_contact_proposal = db_prospect.id in pending_proposal_ids
            ProspectService._set_opt_out_flags(prospect, db_prospect, resolved_opt_outs)
            prospects.append(prospect)
        return prospects

    @staticmethod
    def _resolve_opt_outs(
        db: Session, db_prospects: list[ProspectDB]
    ) -> tuple[set[tuple[int, str]], set[str], dict[int, str]]:
        """Batch-resolve the SMS-STOP and email-unsubscribe state of a prospect list.

        SMS STOP is scoped per owner (a suppression blocks that owner's sends); email
        unsubscribe is global by address (mirrors the send-time guard).

        Args:
            db: Active database session.
            db_prospects: The prospect rows being serialized.

        Returns:
            ``(suppressed (owner_id, e164) pairs, unsubscribed lowercased emails, prospect_id → e164)``.
        """
        prospect_phone: dict[int, str] = {}
        phones: set[str] = set()
        emails: set[str] = set()
        for db_prospect in db_prospects:
            phone_e164 = to_e164_fr(db_prospect.phone) if db_prospect.phone else None
            if phone_e164 and db_prospect.user_id:
                prospect_phone[db_prospect.id] = phone_e164
                phones.add(phone_e164)
            if db_prospect.email:
                emails.add(db_prospect.email.lower())

        suppressed_pairs: set[tuple[int, str]] = set()
        if phones:
            rows = db.execute(
                select(SmsSuppression.user_id, SmsSuppression.phone_e164).where(SmsSuppression.phone_e164.in_(phones))
            ).all()
            suppressed_pairs = {(row[0], row[1]) for row in rows}

        unsubscribed_emails: set[str] = set()
        if emails:
            rows = db.execute(select(EmailUnsubscribe.email).where(EmailUnsubscribe.email.in_(emails))).all()
            unsubscribed_emails = {str(row[0]).lower() for row in rows}

        return suppressed_pairs, unsubscribed_emails, prospect_phone

    @staticmethod
    def _set_opt_out_flags(
        prospect: Prospect,
        db_prospect: ProspectDB,
        resolved: tuple[set[tuple[int, str]], set[str], dict[int, str]],
    ) -> None:
        """Stamp the SMS-STOP and email-unsubscribe flags on a serialized prospect.

        Args:
            prospect: The serialized model to flag.
            db_prospect: The source row (owner + id + email).
            resolved: The batch result from :meth:`_resolve_opt_outs`.
        """
        suppressed_pairs, unsubscribed_emails, prospect_phone = resolved
        phone_e164 = prospect_phone.get(db_prospect.id)
        prospect.sms_opted_out = bool(
            phone_e164 and db_prospect.user_id and (db_prospect.user_id, phone_e164) in suppressed_pairs
        )
        prospect.email_unsubscribed = bool(db_prospect.email and db_prospect.email.lower() in unsubscribed_emails)

    async def get_prospect(self, db: Session, prospect_id: int) -> Prospect | None:
        """
        Retrieve a prospect by ID.

        Args:
            db: Database session
            prospect_id: Unique prospect identifier

        Returns:
            Prospect object if found, None otherwise
        """
        db_prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
        if not db_prospect:
            return None
        prospect = Prospect.model_validate(db_prospect)
        self._set_opt_out_flags(prospect, db_prospect, self._resolve_opt_outs(db, [db_prospect]))
        return prospect

    @staticmethod
    def _demote_social_website(
        website: str | None, website_status: str | None, facebook_url: str | None
    ) -> tuple[str | None, str | None, str | None]:
        """Demote a social page wrongly saved as a website: a Facebook page becomes ``facebook_url``, then cleared.

        A Facebook/Instagram page is never a real website, so it must not mark the prospect as "has a site"
        (which would hide it from the without-a-site targeting). Import and manual edits both flow through here.

        Args:
            website: The raw website URL to check.
            website_status: The liveness status, cleared when the URL is social.
            facebook_url: The existing Facebook URL, filled from the website only when empty and the URL is Facebook.

        Returns:
            The corrected ``(website, website_status, facebook_url)`` triple.
        """
        if website and ValidationService.is_social_url(website):
            if "facebook.com" in website.lower() and not (facebook_url or "").strip():
                facebook_url = website
            return None, None, facebook_url
        return website, website_status, facebook_url

    async def create_prospect(
        self,
        db: Session,
        prospect: ProspectCreate,
        user_id: int,
        organization_id: int | None = None,
        record_activity: bool = True,
    ) -> Prospect:
        """
        Create a new prospect.

        Args:
            db: Database session
            prospect: Prospect data to create
            user_id: ID of the user creating the prospect
            organization_id: The creator's organization — the prospect is shared with it
            record_activity: Whether to log a « prospect créé » entry (off for bulk imports, which log one summary)

        Returns:
            Created prospect with generated ID
        """
        # Convert Source enum to string
        source_value = prospect.source.value if hasattr(prospect.source, "value") else str(prospect.source)

        website, website_status, facebook_url = self._demote_social_website(
            prospect.website,
            prospect.website_status.value if prospect.website_status is not None else None,
            prospect.facebook_url,
        )

        db_prospect = ProspectDB(
            name=prospect.name,
            address=prospect.address,
            city=prospect.city,
            phone=prospect.phone,
            email=prospect.email,
            emails=[prospect.email] if prospect.email else None,
            website=website,
            website_status=website_status,
            google_maps_url=prospect.google_maps_url,
            facebook_url=facebook_url,
            category=prospect.category,
            source=source_value,
            confidence=prospect.confidence,
            user_id=user_id,
            organization_id=organization_id,
        )
        db.add(db_prospect)
        db.commit()
        db.refresh(db_prospect)

        if record_activity:
            location = f" · {db_prospect.city}" if db_prospect.city else ""
            activity_log_service.record(
                category=CATEGORY_PROSPECT,
                action="prospect_created",
                status=STATUS_INFO,
                title=f"Prospect créé · {db_prospect.name}{location}",
                user_id=user_id,
                entity_type="prospect",
                entity_id=db_prospect.id,
            )

        return Prospect.model_validate(db_prospect)

    async def check_duplicate(self, db: Session, name: str, city: str | None, user_id: int) -> bool:
        """
        Check if a prospect with the same name and city already exists for this user.

        Args:
            db: Database session
            name: Business name
            city: City name
            user_id: User ID

        Returns:
            True if duplicate exists, False otherwise
        """
        query = db.query(ProspectDB).filter(and_(ProspectDB.user_id == user_id, ProspectDB.name.ilike(name)))

        if city:
            query = query.filter(ProspectDB.city.ilike(city))

        return query.first() is not None

    async def facebook_url_exists(self, db: Session, facebook_url: str, user_id: int) -> bool:
        """Whether the user already has a prospect carrying this Facebook page URL.

        Sharper duplicate key than name+city for Facebook-discovered prospects,
        whose names come from SERP titles and vary from one search to the next.

        Args:
            db: Database session
            facebook_url: Canonical Facebook page URL
            user_id: User ID

        Returns:
            True if a prospect with this page URL exists, False otherwise
        """
        return (
            db.query(ProspectDB.id)
            .filter(and_(ProspectDB.user_id == user_id, ProspectDB.facebook_url == facebook_url))
            .first()
            is not None
        )

    async def bulk_create_prospects(
        self, db: Session, prospects: list[ProspectCreate], user_id: int, skip_duplicates: bool = True
    ) -> tuple[list[Prospect], int]:
        """
        Create multiple prospects at once.

        Args:
            db: Database session
            prospects: List of prospect data to create
            user_id: ID of the user creating the prospects
            skip_duplicates: If True, skip prospects that already exist

        Returns:
            Tuple of (list of created prospects, number of skipped duplicates)
        """
        created_prospects = []
        skipped_count = 0

        for prospect_data in prospects:
            # Check for duplicates if requested
            if skip_duplicates:
                is_duplicate = await self.check_duplicate(
                    db=db, name=prospect_data.name, city=prospect_data.city, user_id=user_id
                )
                if is_duplicate:
                    skipped_count += 1
                    continue

            # Create the prospect (no per-row log — the import logs one summary below).
            created = await self.create_prospect(db, prospect_data, user_id, record_activity=False)
            created_prospects.append(created)

        if created_prospects:
            skipped_note = f" ({skipped_count} doublon(s) ignoré(s))" if skipped_count else ""
            activity_log_service.record(
                category=CATEGORY_PROSPECT,
                action="prospects_imported",
                status=STATUS_INFO,
                title=f"Import de {len(created_prospects)} prospect(s){skipped_note}",
                user_id=user_id,
            )

        return created_prospects, skipped_count

    async def update_prospect(self, db: Session, prospect_id: int, update_data: ProspectUpdate) -> Prospect | None:
        """
        Update an existing prospect.

        Args:
            db: Database session
            prospect_id: Prospect ID to update
            update_data: Fields to update

        Returns:
            Updated prospect if found, None otherwise
        """
        db_prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
        if not db_prospect:
            return None

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)
        # A manually corrected URL invalidates the liveness verdict of the old one.
        if "website" in update_dict and "website_status" not in update_dict:
            update_dict["website_status"] = None
        # A social page (Facebook…) set as the website is demoted — it never counts as a real site.
        if "website" in update_dict:
            website, website_status, facebook_url = self._demote_social_website(
                update_dict.get("website"),
                update_dict.get("website_status"),
                update_dict.get("facebook_url") or db_prospect.facebook_url,
            )
            update_dict["website"] = website
            update_dict["website_status"] = website_status
            if facebook_url and not (db_prospect.facebook_url or "").strip():
                update_dict["facebook_url"] = facebook_url
        for field, value in update_dict.items():
            if field in ("source", "website_status") and value is not None:
                # Convert enum to its stored string value
                value = value.value if hasattr(value, "value") else str(value)
            setattr(db_prospect, field, value)

        # Editing the primary email through the regular update keeps the multi-email list in sync,
        # and clears a « email injoignable » flag: the operator just fixed the address by hand.
        if update_dict.get("email"):
            sync_prospect_emails(db_prospect, primary=update_dict["email"])
            if db_prospect.email_undeliverable:
                db_prospect.email_undeliverable = False
                db_prospect.email_undeliverable_at = None
                db_prospect.email_undeliverable_reason = None

        db.commit()
        db.refresh(db_prospect)

        prospect = Prospect.model_validate(db_prospect)
        self._set_opt_out_flags(prospect, db_prospect, self._resolve_opt_outs(db, [db_prospect]))
        return prospect

    async def set_do_not_contact(
        self, db: Session, prospect_id: int, *, user_id: int, enabled: bool, reason: str | None = None
    ) -> Prospect | None:
        """Mark a prospect « ne plus contacter » (or lift it), and hold back its pending sends.

        Turning it on blocks every future outreach (campaign enqueue + dispatch, SMS relance/cold)
        and marks the prospect's pending queue items ``skipped`` so the campaign page shows the line
        as held back — the trace the operator wants. Turning it off lifts the block; already held-back
        rows stay as they are (re-queue them by hand if needed). The decision is logged to the feed.

        Args:
            db: Active database session.
            prospect_id: The prospect to flag.
            user_id: The operator making the decision (for the activity log).
            enabled: ``True`` to stop all contact, ``False`` to re-allow it.
            reason: Optional note kept with the flag and shown on the held-back queue lines.

        Returns:
            The updated prospect, or ``None`` when it does not exist.
        """
        from services.campaign_queue_service import CampaignQueueService

        db_prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
        if db_prospect is None:
            return None

        clean_reason = (reason or "").strip()[:500] or None
        db_prospect.do_not_contact = enabled
        db_prospect.do_not_contact_reason = clean_reason if enabled else None
        db_prospect.do_not_contact_at = datetime.now(UTC) if enabled else None
        db.commit()
        db.refresh(db_prospect)

        if enabled:
            CampaignQueueService(db).skip_pending_for_prospect(prospect_id, clean_reason)

        activity_log_service.record(
            category=CATEGORY_PROSPECT,
            action="prospect_do_not_contact" if enabled else "prospect_contact_reenabled",
            status=STATUS_WARNING if enabled else STATUS_INFO,
            title=(
                f"Ne plus contacter · {db_prospect.name}" if enabled else f"Contact ré-autorisé · {db_prospect.name}"
            ),
            detail=clean_reason if enabled else None,
            user_id=user_id,
            entity_type="prospect",
            entity_id=db_prospect.id,
        )

        prospect = Prospect.model_validate(db_prospect)
        self._set_opt_out_flags(prospect, db_prospect, self._resolve_opt_outs(db, [db_prospect]))
        return prospect

    async def delete_prospect(self, db: Session, prospect_id: int) -> bool:
        """
        Delete a prospect together with the data it owns.

        Its non-delivered demo sites are soft-deleted first (Storyblok space and
        video files cleaned up); a delivered one is left untouched — it is sold and
        lives on the client's domain. The enrichment is then removed explicitly:
        its foreign key to ``prospects`` has no ``ON DELETE`` rule in prod
        (RESTRICT), so a bare prospect delete raises an IntegrityError there.
        Interactions, campaign links and queued emails already cascade in the database.

        Args:
            db: Database session
            prospect_id: Prospect ID to delete

        Returns:
            True if deleted, False if not found
        """
        from enums.demo_site_status import DemoSiteStatus
        from models.demo_site import DemoSite
        from services.demo_site_service import demo_site_service
        from services.prospect_photo_storage_service import prospect_photo_storage

        db_prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
        if not db_prospect:
            return False

        demo_sites = (
            db.query(DemoSite)
            .filter(DemoSite.prospect_id == prospect_id, DemoSite.status != DemoSiteStatus.DELIVERED.value)
            .all()
        )
        for demo_site in demo_sites:
            await demo_site_service.delete_demo_site(db, demo_site)

        db.query(ProspectEnrichment).filter(ProspectEnrichment.prospect_id == prospect_id).delete(
            synchronize_session=False
        )
        db.delete(db_prospect)
        db.commit()

        # The prospect's rehosted photos on R2 are now unreferenced — reclaim their space (best-effort).
        await prospect_photo_storage.delete_for_prospect(prospect_id)
        return True

    async def get_prospects_count(self, db: Session, user_id: int | None = None) -> int:
        """
        Get total count of prospects.

        Args:
            db: Database session
            user_id: Optional user ID to filter by

        Returns:
            Total number of prospects
        """
        query = db.query(ProspectDB)
        if user_id is not None:
            query = query.filter(ProspectDB.user_id == user_id)
        return query.count()


# Global service instance
prospect_service = ProspectService()
