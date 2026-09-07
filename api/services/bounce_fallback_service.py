"""Multi-email bounce fallback.

When a campaign email hard-bounces on a prospect's primary address, we don't want to lose the prospect:
if they have another (not-yet-tried) email, promote it to primary and re-queue the same campaign email
to it, scheduled on a normal send slot. Always 1-to-1 — never a multi-recipient send. It stops on its
own once every email has been tried, and never re-sends when a message already reached the prospect.

When every address has bounced with no delivery, the prospect's email is a dead end: we flag it
``email_undeliverable`` so the operator sees it and can recover the prospect into an SMS campaign,
rather than silently keeping a « contacté » prospect who never received anything.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from enums.email_status import EmailStatus
from models.campaign import Campaign
from models.email_log import EmailLog
from models.email_queue import EmailQueue
from models.prospect_db import ProspectDB
from services.prospect_emails import sync_prospect_emails
from services.send_policy_service import send_policy_service

logger = logging.getLogger(__name__)

# Statuses proving the prospect already received the campaign — no point falling back after that.
_DELIVERED_STATUSES: frozenset[str] = frozenset(
    {EmailStatus.DELIVERED.value, EmailStatus.OPENED.value, EmailStatus.CLICKED.value, EmailStatus.REPLIED.value}
)


def next_fallback_email(emails: list[str], tried_lower: set[str]) -> str | None:
    """Return the first email not already attempted (case-insensitive), or None when all were tried."""
    for candidate in emails:
        cleaned = (candidate or "").strip()
        if cleaned and cleaned.lower() not in tried_lower:
            return cleaned
    return None


class BounceFallbackService:
    """Re-route a campaign email to a prospect's next email after a hard bounce."""

    def handle_bounce(self, db: Session, email_log: EmailLog) -> None:
        """Promote the next untried email and re-queue the campaign send. Best-effort, never raises."""
        try:
            self._handle(db, email_log)
        except Exception:
            logger.exception("Bounce fallback failed for email_log_id=%s", getattr(email_log, "id", None))

    def _handle(self, db: Session, email_log: EmailLog) -> None:
        if email_log.status != EmailStatus.BOUNCED.value or not email_log.prospect_id or not email_log.campaign_id:
            return
        prospect = db.get(ProspectDB, email_log.prospect_id)
        if prospect is None:
            return
        emails = list(prospect.emails or ([prospect.email] if prospect.email else []))

        history = db.execute(
            select(EmailLog.recipient_email, EmailLog.status).where(
                EmailLog.prospect_id == prospect.id, EmailLog.campaign_id == email_log.campaign_id
            )
        ).all()
        # The message already reached the prospect on some address → nothing to recover.
        if any(status in _DELIVERED_STATUSES for _, status in history):
            return
        tried_lower = {(recipient or "").strip().lower() for recipient, _ in history if recipient}
        fallback = next_fallback_email(emails, tried_lower)
        if fallback is None:
            # Every address bounced with no delivery — the email is a dead end. Flag it so the
            # prospect surfaces for SMS recovery instead of staying a silent « contacté ».
            self._mark_undeliverable(db, prospect, email_log.error_message)
            return

        sync_prospect_emails(prospect, primary=fallback)
        db.add(prospect)

        campaign = db.get(Campaign, email_log.campaign_id)
        if campaign is None:
            return
        template_id = (
            campaign.ab_template_id_b
            if email_log.ab_variant == "B" and campaign.ab_template_id_b
            else campaign.template_id
        )
        db.add(
            EmailQueue(
                user_id=email_log.user_id,
                campaign_id=campaign.id,
                prospect_id=prospect.id,
                template_id=template_id,
                email_account_id=None,
                queue_type="initial",
                ab_variant=email_log.ab_variant,
                follow_up_index=0,
                scheduled_at=self._next_slot(db, email_log.user_id),
                status="pending",
            )
        )
        db.commit()
        logger.info(
            "Bounce fallback: prospect_id=%s re-queued to next email after %s bounced",
            prospect.id,
            email_log.recipient_email,
        )

    @staticmethod
    def _mark_undeliverable(db: Session, prospect: ProspectDB, reason: str | None) -> None:
        """Flag the prospect's email as a dead end (idempotent). Never touches ``contacted``."""
        if prospect.email_undeliverable:
            return
        prospect.email_undeliverable = True
        prospect.email_undeliverable_at = datetime.now(UTC).replace(tzinfo=None)
        prospect.email_undeliverable_reason = (reason or "").strip()[:500] or None
        db.add(prospect)
        db.commit()
        logger.info("Prospect %s flagged email_undeliverable after every address bounced", prospect.id)

    @staticmethod
    def clear_undeliverable(db: Session, prospect: ProspectDB) -> None:
        """Lift the dead-email flag (a later delivery succeeded, or the email was fixed by hand)."""
        if not prospect.email_undeliverable:
            return
        prospect.email_undeliverable = False
        prospect.email_undeliverable_at = None
        prospect.email_undeliverable_reason = None
        db.add(prospect)

    @staticmethod
    def _next_slot(db: Session, user_id: int) -> datetime:
        """Return the next in-window send slot (respects the user's SendPolicy), or now as a fallback."""
        resolved = send_policy_service.resolve(db, user_id)
        seed = send_policy_service.pending_counts_by_day(db, user_id)
        slots = send_policy_service.next_send_slots(resolved, 1, seed_counts=seed)
        return slots[0] if slots else datetime.now(UTC).replace(tzinfo=None)


bounce_fallback_service = BounceFallbackService()
