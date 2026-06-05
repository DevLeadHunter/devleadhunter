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
from services.email_sending_service import EmailSendingService
from services.unsubscribe_service import unsubscribe_service
from enums.email_status import EmailStatus

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
    ) -> int:
        """
        Populate the queue with J1 items for all prospects in the campaign.

        When ``ab_template_id_b`` is provided (A/B test mode), prospects are
        split 50/50: even-indexed prospects get variant A, odd-indexed get B.

        Each item is spaced ``campaign.send_delay_minutes`` apart so the worker
        can dispatch them without extra rate-limiting logic.  Emails are sent
        via the user's ResendConfig — no EmailAccount selection.

        Args:
            campaign:         The campaign whose prospects should be enqueued.
            template_id:      J1 template (variant A when A/B testing).
            ab_template_id_b: J1 template for variant B (A/B testing only).

        Returns:
            Number of queue items added.
        """
        now = _utcnow()
        is_ab = ab_template_id_b is not None

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

        count = 0
        for idx, prospect in enumerate(campaign.prospects):
            if prospect.id in already_queued:
                continue
            if unsubscribe_service.is_unsubscribed(self.db, prospect.email or ""):
                logger.debug("[Queue] Skipping unsubscribed prospect %d", prospect.id)
                continue

            if is_ab:
                variant = "A" if idx % 2 == 0 else "B"
                tpl_id = template_id if variant == "A" else ab_template_id_b
            else:
                variant = None
                tpl_id = template_id

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
            count += 1

        self.db.commit()
        logger.info("[Queue] Enqueued %d J1 items for campaign %d (A/B=%s)", count, campaign.id, is_ab)
        return count

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

        # Build personalisation variables.
        name_parts = (prospect.name or "").split()
        variables: dict[str, str] = {
            _VAR_FIRST_NAME: name_parts[0] if name_parts else "",
            _VAR_COMPANY:    prospect.name or "",
            _VAR_CITY:       prospect.city or "",
            _VAR_EMAIL:      prospect.email or "",
            _VAR_PHONE:      prospect.phone or "",
            _VAR_METIER:     prospect.category or "",
            _VAR_DEMO_LINK:  "",
        }

        email_service = EmailSendingService(self.db)
        subject: str = email_service.replace_variables(template.subject, variables)
        body_html: str = email_service.replace_variables(template.body_html, variables)

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
            _VAR_DEMO_LINK:  "",
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
