"""
Campaign queue service — manages the cold-email send queue.

Responsibilities:
  - Enqueue initial (J1) and follow-up (J+N) emails when a campaign is launched.
  - A/B testing: split prospects 50/50 between variant A (campaign.template_id)
    and variant B (campaign.ab_template_id_b) at enqueue time.
  - Multiple follow-ups: after a J1 send, schedule all steps from
    ``campaign_follow_ups`` in order.  Falls back to the legacy
    ``follow_up_template_id`` if no ``campaign_follow_ups`` rows exist.
  - Skip sending to prospects who have unsubscribed or who already engaged
    (follow-ups only).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session

from models.campaign import Campaign, CampaignStatus
from models.campaign_follow_up import CampaignFollowUp
from models.email_queue import EmailQueue
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from models.email_template import EmailTemplate
from models.demo_site import DemoSite
from services.email_sending_service import EmailSendingService
from services.unsubscribe_service import unsubscribe_service
from enums.email_status import EmailStatus
from enums.demo_site_status import DemoSiteStatus

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Personalisation variable keys used in cold-email templates.
# ---------------------------------------------------------------------------
_VAR_FIRST_NAME = "prenom"
_VAR_COMPANY    = "entreprise"
_VAR_CITY       = "ville"
_VAR_EMAIL      = "email"
_VAR_PHONE      = "phone"
_VAR_DEMO_LINK  = "lien_demo"
_VAR_METIER     = "metier"

# Queue item status values
_STATUS_PENDING  = "pending"
_STATUS_SENDING  = "sending"
_STATUS_SENT     = "sent"
_STATUS_SKIPPED  = "skipped"
_STATUS_FAILED   = "failed"


@dataclass
class EnqueueResult:
    """
    Outcome of enqueuing a campaign.

    Attributes:
        enqueued:        Number of J1 queue items added.
        skipped_no_demo: Prospects skipped because their template uses
                         ``{lien_demo}`` but they have no active demo site.
                         Each entry is ``{"id": int, "name": str}``.
    """

    enqueued: int = 0
    skipped_no_demo: list[dict[str, object]] = field(default_factory=list)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-naive datetime (DB-compatible)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CampaignQueueService:
    """Manages the ``email_queue`` table for rate-limited cold outreach."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -----------------------------------------------------------------------
    # Enqueueing
    # -----------------------------------------------------------------------

    def enqueue_campaign(
        self,
        campaign: Campaign,
        template_id: int,
        ab_template_id_b: int | None = None,
    ) -> EnqueueResult:
        """
        Populate the queue with J1 items for all prospects in the campaign.

        When ``ab_template_id_b`` is provided (A/B test mode), prospects are
        split 50/50: even-indexed prospects get variant A, odd-indexed get B.

        Each item is spaced ``campaign.send_delay_minutes`` apart so the worker
        can dispatch them without extra rate-limiting logic.  Emails are sent
        via the user's ResendConfig — no EmailAccount selection.

        Guard: a prospect is **not** enqueued when its assigned template uses the
        ``{lien_demo}`` placeholder but the prospect has no active demo site.
        This prevents sending a cold email with an empty demo link; such
        prospects are returned in ``skipped_no_demo`` so the operator can
        generate their sites and re-launch.

        Args:
            campaign:         The campaign whose prospects should be enqueued.
            template_id:      J1 template (variant A when A/B testing).
            ab_template_id_b: J1 template for variant B (A/B testing only).

        Returns:
            An :class:`EnqueueResult` with the enqueued count and the list of
            prospects skipped for lacking a demo site.
        """
        now = _utcnow()
        is_ab = ab_template_id_b is not None

        # Pre-load templates once to know whether each variant needs a demo link.
        template_a: EmailTemplate | None = self.db.get(EmailTemplate, template_id)
        template_b: EmailTemplate | None = (
            self.db.get(EmailTemplate, ab_template_id_b) if ab_template_id_b else None
        )
        uses_demo_a: bool = self._template_uses_demo_link(template_a)
        uses_demo_b: bool = self._template_uses_demo_link(template_b)

        # Append after the last pending slot so re-launching is safe.
        latest: datetime | None = self.db.execute(
            select(func.max(EmailQueue.scheduled_at)).where(
                EmailQueue.campaign_id == campaign.id,
                EmailQueue.status == _STATUS_PENDING,
            )
        ).scalar()
        next_slot: datetime = latest if (latest is not None and latest > now) else now
        delay = timedelta(minutes=max(campaign.send_delay_minutes, 1))

        # Prospects already in the initial queue are never re-added.
        already_queued: set[int] = {
            row[0]
            for row in self.db.execute(
                select(EmailQueue.prospect_id).where(
                    EmailQueue.campaign_id == campaign.id,
                    EmailQueue.queue_type == "initial",
                )
            ).all()
        }

        result = EnqueueResult()
        for idx, prospect in enumerate(campaign.prospects):
            if prospect.id in already_queued:
                continue
            if unsubscribe_service.is_unsubscribed(self.db, prospect.email or ""):
                logger.debug("[Queue] Skipping unsubscribed prospect %d", prospect.id)
                continue

            if is_ab:
                variant = "A" if idx % 2 == 0 else "B"
                tpl_id = template_id if variant == "A" else ab_template_id_b
                uses_demo = uses_demo_a if variant == "A" else uses_demo_b
            else:
                variant = None
                tpl_id = template_id
                uses_demo = uses_demo_a

            # Guard: never enqueue an email that would ship an empty {lien_demo}.
            if uses_demo and not self._demo_link_for_prospect(prospect.id, campaign.user_id, variant):
                logger.info(
                    "[Queue] Skipping prospect %d — no active demo site for {lien_demo}", prospect.id
                )
                result.skipped_no_demo.append({"id": prospect.id, "name": prospect.name or ""})
                continue

            self.db.add(EmailQueue(
                user_id=campaign.user_id,
                campaign_id=campaign.id,
                prospect_id=prospect.id,
                template_id=tpl_id,
                email_account_id=None,
                queue_type="initial",
                ab_variant=variant,
                follow_up_index=0,
                scheduled_at=next_slot,
                status=_STATUS_PENDING,
            ))
            next_slot += delay
            result.enqueued += 1

        self.db.commit()
        logger.info(
            "[Queue] Enqueued %d J1 items for campaign %d (A/B=%s, %d skipped no-demo)",
            result.enqueued, campaign.id, is_ab, len(result.skipped_no_demo),
        )
        return result

    # -----------------------------------------------------------------------
    # Worker tick
    # -----------------------------------------------------------------------

    async def process_next(self) -> bool:
        """
        Dispatch the next due queue item across all active campaigns.

        Returns:
            ``True`` if an item was processed, ``False`` if nothing was due.
        """
        now = _utcnow()

        item: EmailQueue | None = self.db.execute(
            select(EmailQueue)
            .join(Campaign, EmailQueue.campaign_id == Campaign.id)
            .where(
                and_(
                    EmailQueue.status == _STATUS_PENDING,
                    EmailQueue.scheduled_at <= now,
                    Campaign.status == CampaignStatus.ACTIVE.value,
                )
            )
            .order_by(EmailQueue.scheduled_at.asc())
            .limit(1)
        ).scalar_one_or_none()

        if item is None:
            return False

        # Claim the item immediately to prevent concurrent pick.
        item.status = _STATUS_SENDING
        self.db.commit()

        try:
            await self._dispatch(item)
        except Exception as exc:  # noqa: BLE001
            logger.error("[Queue] Unhandled error dispatching item %d: %s", item.id, exc)
            item.status = _STATUS_FAILED
            self.db.commit()

        return True

    @staticmethod
    def _template_uses_demo_link(template: EmailTemplate | None) -> bool:
        """
        Return True when a template references the ``{lien_demo}`` placeholder.

        Args:
            template: Template to inspect (subject + HTML body), or None.

        Returns:
            True if the rendered email would contain the demo link placeholder.
        """
        if template is None:
            return False
        haystack: str = f"{template.subject or ''} {template.body_html or ''}"
        return f"{{{_VAR_DEMO_LINK}}}" in haystack

    def _demo_link_for_prospect(self, prospect_id: int, user_id: int, variant: str | None) -> str:
        """
        Resolve the ``{lien_demo}`` value: the prospect's active demo URL, with the
        A/B variant appended (``?v=A``) so PostHog can attribute the demo visit to
        the email variant. Returns "" when the prospect has no active demo.
        """
        site: DemoSite | None = self.db.execute(
            select(DemoSite)
            .where(
                DemoSite.prospect_id == prospect_id,
                DemoSite.user_id == user_id,
                DemoSite.status == DemoSiteStatus.ACTIVE.value,
            )
            .order_by(DemoSite.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if not site or not site.demo_url:
            return ""
        url: str = site.demo_url
        if variant:
            url = f"{url}{'&' if '?' in url else '?'}v={variant}"
        return url

    async def _dispatch(self, item: EmailQueue) -> None:
        """
        Render and send the email for a single queue item, then schedule follow-ups.

        Args:
            item: The queue item to process.
        """
        prospect: ProspectDB = item.prospect
        template: EmailTemplate = item.template
        campaign: Campaign = item.campaign

        # Guard: prospect may have unsubscribed after being enqueued.
        if not prospect.email or unsubscribe_service.is_unsubscribed(self.db, prospect.email):
            logger.info("[Queue] Skipping unsubscribed prospect %d", prospect.id)
            item.status = _STATUS_SKIPPED
            self.db.commit()
            return

        # Follow-up guard: skip if the prospect already engaged.
        if item.queue_type == "followup":
            engaged: int = self.db.execute(
                select(func.count()).where(
                    EmailLog.campaign_id == item.campaign_id,
                    EmailLog.prospect_id == str(item.prospect_id),
                    EmailLog.status.in_([
                        EmailStatus.OPENED.value,
                        EmailStatus.CLICKED.value,
                    ]),
                )
            ).scalar() or 0
            if engaged > 0:
                logger.info("[Queue] Follow-up skipped — prospect %d already engaged", prospect.id)
                item.status = _STATUS_SKIPPED
                self.db.commit()
                return

        # Guard (defense in depth): never send an email whose template needs
        # {lien_demo} when the prospect has no active demo site — e.g. the demo
        # expired between enqueue and dispatch.
        demo_link: str = self._demo_link_for_prospect(prospect.id, item.user_id, item.ab_variant)
        if self._template_uses_demo_link(template) and not demo_link:
            logger.info(
                "[Queue] Skipping send for prospect %d — no active demo site for {lien_demo}", prospect.id
            )
            item.status = _STATUS_SKIPPED
            self.db.commit()
            return

        # Build personalisation variables.
        name_parts = (prospect.name or "").split()
        variables: dict[str, str] = {
            _VAR_FIRST_NAME: name_parts[0] if name_parts else "",
            _VAR_COMPANY:    prospect.name or "",
            _VAR_CITY:       prospect.city or "",
            _VAR_EMAIL:      prospect.email or "",
            _VAR_PHONE:      prospect.phone or "",
            _VAR_METIER:     prospect.category or "",
            _VAR_DEMO_LINK:  demo_link,
        }

        email_service = EmailSendingService(self.db)
        subject: str = email_service.replace_variables(template.subject, variables)
        body_html: str = email_service.replace_variables(template.body_html, variables)

        # Behaviour-personalised follow-up (additive — keeps the rendered template
        # as the base and falls back to it if there is no behaviour data / LLM).
        if item.queue_type == "followup" and getattr(campaign, "behavior_personalized_followups", False):
            try:
                from services.behavior_service import behavior_service

                personalized = await behavior_service.draft_personalized_followup(
                    self.db,
                    item.user_id,
                    prospect,
                    base_subject=subject,
                    base_body_html=body_html,
                )
                subject = personalized.get("subject", subject) or subject
                body_html = personalized.get("body_html", body_html) or body_html
            except Exception as exc:  # noqa: BLE001 — never block a send on personalisation
                logger.warning("[Queue] Behaviour personalisation failed for prospect %d: %s", prospect.id, exc)

        result: dict = await email_service.send_via_resend_config(
            user_id=item.user_id,
            recipient_email=prospect.email,
            recipient_name=prospect.name,
            subject=subject,
            body_html=body_html,
            prospect_id=str(prospect.id),
            campaign_id=str(item.campaign_id),
            ab_variant=item.ab_variant,
        )

        item.email_log_id = result.get("email_log_id")
        item.status = _STATUS_SENT if result.get("success") else _STATUS_FAILED
        self.db.commit()

        # Schedule follow-ups after a successful J1 send.
        if item.queue_type == "initial" and result.get("success"):
            self._schedule_follow_ups(item)

    def _schedule_follow_ups(self, j1_item: EmailQueue) -> None:
        """
        Create EmailQueue rows for all follow-up steps after a J1 success.

        Uses ``campaign_follow_ups`` rows when they exist; falls back to the
        legacy ``follow_up_template_id`` / ``follow_up_delay_days`` fields.

        Args:
            j1_item: The just-sent J1 queue item.
        """
        campaign: Campaign = j1_item.campaign

        # Prefer the new multi-step follow-up table.
        follow_ups: list[CampaignFollowUp] = self.db.execute(
            select(CampaignFollowUp)
            .where(CampaignFollowUp.campaign_id == campaign.id)
            .order_by(CampaignFollowUp.position.asc())
        ).scalars().all()

        if not follow_ups:
            # Legacy fallback: single follow-up fields on the campaign.
            if campaign.follow_up_template_id:
                follow_up_at = _utcnow() + timedelta(days=campaign.follow_up_delay_days)
                self.db.add(EmailQueue(
                    user_id=j1_item.user_id,
                    campaign_id=j1_item.campaign_id,
                    prospect_id=j1_item.prospect_id,
                    template_id=campaign.follow_up_template_id,
                    email_account_id=None,
                    queue_type="followup",
                    ab_variant=j1_item.ab_variant,
                    follow_up_index=1,
                    scheduled_at=follow_up_at,
                    status=_STATUS_PENDING,
                ))
                self.db.commit()
            return

        # Build the sequence: each step's scheduled_at = previous + delay.
        base_time = _utcnow()
        for step in follow_ups:
            base_time += timedelta(days=step.delay_days)
            self.db.add(EmailQueue(
                user_id=j1_item.user_id,
                campaign_id=j1_item.campaign_id,
                prospect_id=j1_item.prospect_id,
                template_id=step.template_id,
                email_account_id=None,
                queue_type="followup",
                ab_variant=j1_item.ab_variant,
                follow_up_index=step.position,
                scheduled_at=base_time,
                status=_STATUS_PENDING,
            ))
        self.db.commit()
        logger.info(
            "[Queue] Scheduled %d follow-up(s) for prospect %d",
            len(follow_ups),
            j1_item.prospect_id,
        )

    # -----------------------------------------------------------------------
    # Immediate send (bypass delay)
    # -----------------------------------------------------------------------

    async def send_followup_now(
        self,
        campaign: Campaign,
        prospect_id: int,
        template_id: int,
    ) -> dict:
        """
        Immediately dispatch a follow-up email for a specific prospect,
        bypassing the scheduled queue.  Sends via the user's ResendConfig.

        Args:
            campaign:    The parent campaign.
            prospect_id: Target prospect ID.
            template_id: Template to use.

        Returns:
            Result dict from ``EmailSendingService.send_via_resend_config``.
        """
        prospect: ProspectDB | None = self.db.get(ProspectDB, prospect_id)
        template: EmailTemplate | None = self.db.get(EmailTemplate, template_id)

        if not prospect or not prospect.email:
            return {"success": False, "error": "Prospect introuvable ou sans email"}
        if not template:
            return {"success": False, "error": "Template introuvable"}

        name_parts = (prospect.name or "").split()
        variables: dict[str, str] = {
            _VAR_FIRST_NAME: name_parts[0] if name_parts else "",
            _VAR_COMPANY:    prospect.name or "",
            _VAR_CITY:       prospect.city or "",
            _VAR_EMAIL:      prospect.email or "",
            _VAR_PHONE:      prospect.phone or "",
            _VAR_METIER:     prospect.category or "",
            _VAR_DEMO_LINK:  self._demo_link_for_prospect(prospect_id, campaign.user_id, None),
        }

        email_service = EmailSendingService(self.db)
        subject = email_service.replace_variables(template.subject, variables)
        body_html = email_service.replace_variables(template.body_html, variables)

        return await email_service.send_via_resend_config(
            user_id=campaign.user_id,
            recipient_email=prospect.email,
            recipient_name=prospect.name,
            subject=subject,
            body_html=body_html,
            prospect_id=str(prospect_id),
            campaign_id=str(campaign.id),
        )

    # -----------------------------------------------------------------------
    # Queue management helpers
    # -----------------------------------------------------------------------

    def cancel_campaign_queue(self, campaign_id: int) -> int:
        """
        Cancel all pending items for a campaign (pause / cancel).

        Returns:
            Number of items cancelled.
        """
        items: list[EmailQueue] = self.db.execute(
            select(EmailQueue).where(
                EmailQueue.campaign_id == campaign_id,
                EmailQueue.status == _STATUS_PENDING,
            )
        ).scalars().all()

        for item in items:
            item.status = _STATUS_SKIPPED
        self.db.commit()
        logger.info("[Queue] Cancelled %d pending items for campaign %d", len(items), campaign_id)
        return len(items)

    def get_pending_count(self, campaign_id: int) -> int:
        """Return the number of pending items in the queue for a campaign."""
        return self.db.execute(
            select(func.count()).where(
                EmailQueue.campaign_id == campaign_id,
                EmailQueue.status == _STATUS_PENDING,
            )
        ).scalar() or 0

    def get_queue_items(
        self,
        campaign_id: int,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EmailQueue]:
        """Return queue items ordered by ``scheduled_at``."""
        stmt = select(EmailQueue).where(EmailQueue.campaign_id == campaign_id)
        if status is not None:
            stmt = stmt.where(EmailQueue.status == status)
        return (
            self.db.execute(stmt.order_by(EmailQueue.scheduled_at.asc()).limit(limit).offset(offset))
            .scalars()
            .all()
        )
