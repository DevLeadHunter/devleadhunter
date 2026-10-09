"""Pre-swap Storyblok spaces before scheduled outreach emails."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from core.config import settings
from enums.demo_site_status import DemoSiteStatus
from models.campaign import Campaign, CampaignStatus
from models.demo_site import DemoSite
from models.email_queue import EmailQueue
from models.email_template import EmailTemplate
from services.campaign_queue_service import CampaignQueueService
from services.demo_site_service import demo_site_service

logger = logging.getLogger(__name__)

_STATUS_PENDING: str = "pending"
_MISSING_SPACE_PASS_INTERVAL: timedelta = timedelta(minutes=10)
_MISSING_SPACE_REFUSAL_PAUSE: timedelta = timedelta(hours=1)
_NEW_SITE_WINDOW: timedelta = timedelta(days=14)


class StoryblokPreswapService:
    """Warm-swaps expiring Storyblok spaces ahead of scheduled demo outreach, and gives new sites their space."""

    def __init__(self) -> None:
        """Start with no pause: the first worker tick may create a missing space."""
        self._next_missing_space_pass_at: datetime | None = None

    async def run_missing_space_pass(self, db: Session) -> bool:
        """
        Give one site generated without its CMS space the space its prospecting video films.

        Storyblok creates about ten spaces a day, so a batch of new sites outruns it: one space every ten
        minutes at most, the site whose outreach comes first served first, and an hour's pause after a refusal
        (the daily limit, reset at midnight UTC).

        Args:
            db: Database session of the worker tick.

        Returns:
            True when a space was created during this pass.
        """
        now: datetime = datetime.now(UTC)
        if self._next_missing_space_pass_at is not None and now < self._next_missing_space_pass_at:
            return False
        self._next_missing_space_pass_at = now + _MISSING_SPACE_PASS_INTERVAL
        site: DemoSite | None = self.next_site_without_space(db, now)
        if site is None:
            return False
        try:
            await demo_site_service.provision_missing_storyblok_space(db, site)
        except Exception as exc:
            db.rollback()
            self._next_missing_space_pass_at = now + _MISSING_SPACE_REFUSAL_PAUSE
            logger.info("[StoryblokSpaces] Space of demo site %s refused, next try in an hour: %s", site.id, exc)
            return False
        logger.info("[StoryblokSpaces] Space created for demo site %s", site.id)
        return True

    @classmethod
    def next_site_without_space(cls, db: Session, now: datetime) -> DemoSite | None:
        """
        The active site without a CMS space that needs one first: the one whose pending outreach comes soonest,
        else the oldest site generated these last two weeks and never sent (older sites already went out without
        one; a campaign of 120 sites takes six nights at Storyblok's daily limit).

        Args:
            db: Database session.
            now: The current time.

        Returns:
            The site, or None when every site that needs a space has one.
        """
        pending_prospects = db.execute(
            select(EmailQueue.prospect_id, EmailQueue.user_id)
            .join(Campaign, EmailQueue.campaign_id == Campaign.id)
            .where(EmailQueue.status == _STATUS_PENDING, Campaign.status == CampaignStatus.ACTIVE.value)
            .group_by(EmailQueue.prospect_id, EmailQueue.user_id)
            .order_by(func.min(EmailQueue.scheduled_at).asc())
        ).all()
        for prospect_id, user_id in pending_prospects:
            site = cls._active_demo_for_prospect(db, prospect_id, user_id)
            if site is not None and not site.storyblok_space_id:
                return site
        new_site_cutoff: datetime = (now - _NEW_SITE_WINDOW).replace(tzinfo=None)
        return db.execute(
            select(DemoSite)
            .where(
                DemoSite.status == DemoSiteStatus.ACTIVE.value,
                DemoSite.storyblok_space_id.is_(None),
                DemoSite.demo_link_sent_at.is_(None),
                DemoSite.created_at >= new_site_cutoff,
            )
            .order_by(DemoSite.created_at.asc(), DemoSite.id.asc())
            .limit(1)
        ).scalar_one_or_none()

    async def run_preswap_pass(self, db: Session) -> int:
        """
        Swap Storyblok spaces that would expire during the upcoming demo TTL window.

        Returns:
            Number of demo sites swapped during this pass.
        """
        now: datetime = datetime.now(UTC)
        lead: timedelta = timedelta(minutes=settings.storyblok_preswap_lead_minutes)
        window_end: datetime = now + lead

        rows: list[tuple[EmailQueue, EmailTemplate]] = list(
            db.execute(
                select(EmailQueue, EmailTemplate)
                .join(Campaign, EmailQueue.campaign_id == Campaign.id)
                .join(EmailTemplate, EmailQueue.template_id == EmailTemplate.id)
                .where(
                    and_(
                        EmailQueue.status == _STATUS_PENDING,
                        EmailQueue.scheduled_at > now,
                        EmailQueue.scheduled_at <= window_end,
                        Campaign.status == CampaignStatus.ACTIVE.value,
                    )
                )
                .order_by(EmailQueue.scheduled_at.asc())
            ).all()
        )

        swapped: int = 0
        seen_site_ids: set[int] = set()

        for item, template in rows:
            if not CampaignQueueService._template_uses_demo_link(template):
                continue

            site: DemoSite | None = self._active_demo_for_prospect(db, item.prospect_id, item.user_id)
            if site is None or site.id in seen_site_ids:
                continue
            if site.demo_link_sent_at is not None:
                continue
            if not demo_site_service.needs_storyblok_space_swap(site, now):
                continue

            seen_site_ids.add(site.id)
            try:
                if await demo_site_service.swap_storyblok_space_for_outreach(db, site):
                    swapped += 1
            except Exception:
                logger.warning(
                    "Storyblok pre-swap failed for demo site %s (queue item %s)",
                    site.id,
                    item.id,
                    exc_info=True,
                )

        if swapped:
            logger.info("[StoryblokPreswap] Swapped %d demo site space(s)", swapped)
        return swapped

    @staticmethod
    def _active_demo_for_prospect(db: Session, prospect_id: int, user_id: int) -> DemoSite | None:
        return db.execute(
            select(DemoSite)
            .where(
                DemoSite.prospect_id == prospect_id,
                DemoSite.user_id == user_id,
                DemoSite.status == DemoSiteStatus.ACTIVE.value,
            )
            .order_by(DemoSite.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()


storyblok_preswap_service = StoryblokPreswapService()
