"""
Scheduled emails — write a message now, let the worker send it at the chosen time.

The send itself replays the immediate path (``conversation_service.send_reply``),
so a scheduled answer keeps the signature, the inbox BCC copy, the thread headers
and the reply capture of an answer sent on the spot.

A prospect who replies before the planned time does NOT cancel the send: the user
wrote the message and decides, the conversation only flags it.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from core.database import SessionLocal
from enums.scheduled_email_status import ScheduledEmailStatus
from models.email_reply import EmailReply
from models.scheduled_email import ScheduledEmail
from services.email_signatures import render_default_signature_html
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

KIND_CONVERSATION_REPLY: str = "conversation_reply"

_MINIMUM_DELAY: timedelta = timedelta(minutes=1)
_MAXIMUM_DELAY: timedelta = timedelta(days=90)
_WORKER_INTERVAL_SECONDS: int = 30
_EDITABLE_STATUSES: tuple[str, ...] = (ScheduledEmailStatus.PENDING.value, ScheduledEmailStatus.FAILED.value)
_VISIBLE_STATUSES: tuple[str, ...] = (
    ScheduledEmailStatus.PENDING.value,
    ScheduledEmailStatus.SENDING.value,
    ScheduledEmailStatus.FAILED.value,
)


class ScheduledEmailError(ValueError):
    """A scheduling request the user must correct (message shown as is)."""


def _utc_now() -> datetime:
    """Current time as naive UTC, the storage convention of the API."""
    return datetime.now(UTC).replace(tzinfo=None)


def _to_naive_utc(moment: datetime) -> datetime:
    """Normalise an incoming datetime to naive UTC (a naive input is read as UTC)."""
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(UTC).replace(tzinfo=None)


class ScheduledEmailService:
    """Plans, edits, cancels and dispatches scheduled emails."""

    @staticmethod
    def _validate_body(body_html: str) -> str:
        """Refuse an empty message."""
        cleaned: str = (body_html or "").strip()
        if not cleaned:
            raise ScheduledEmailError("Message vide")
        return cleaned

    @staticmethod
    def _validate_moment(scheduled_at: datetime) -> datetime:
        """Refuse a time in the past or too far away."""
        moment: datetime = _to_naive_utc(scheduled_at)
        now: datetime = _utc_now()
        if moment < now + _MINIMUM_DELAY:
            raise ScheduledEmailError("Choisissez une heure dans le futur")
        if moment > now + _MAXIMUM_DELAY:
            raise ScheduledEmailError("Programmation limitée à 90 jours")
        return moment

    def _owned(self, db: Session, user_id: int, scheduled_id: int) -> ScheduledEmail | None:
        """The user's scheduled email, or ``None``."""
        row: ScheduledEmail | None = db.get(ScheduledEmail, scheduled_id)
        if row is None or row.user_id != user_id:
            return None
        return row

    def schedule_reply(
        self, db: Session, user_id: int, reply_id: int, body_html: str, scheduled_at: datetime
    ) -> ScheduledEmail | None:
        """
        Plan an answer to a prospect's reply.

        Marks the sender's pending replies as handled: the answer is written, the
        « à traiter » queue no longer needs to remind the user.

        Args:
            db: Active database session.
            user_id: Owner of the conversation.
            reply_id: The reply being answered.
            body_html: The answer's HTML body, without signature.
            scheduled_at: When to send it.

        Returns:
            The planned row, or ``None`` when the reply is not the user's.

        Raises:
            ScheduledEmailError: Empty message or invalid time.
        """
        reply: EmailReply | None = db.get(EmailReply, reply_id)
        if reply is None or reply.user_id != user_id:
            return None
        body: str = self._validate_body(body_html)
        moment: datetime = self._validate_moment(scheduled_at)

        row = ScheduledEmail(
            user_id=user_id,
            kind=KIND_CONVERSATION_REPLY,
            reply_id=reply.id,
            prospect_id=reply.prospect_id,
            recipient_email=reply.from_email,
            body_html=body,
            scheduled_at=moment,
            status=ScheduledEmailStatus.PENDING.value,
        )
        db.add(row)
        now: datetime = _utc_now()
        pending_replies = db.execute(
            select(EmailReply).where(
                EmailReply.user_id == user_id,
                EmailReply.from_email == reply.from_email,
                EmailReply.handled_at.is_(None),
            )
        ).scalars()
        for pending in pending_replies:
            pending.handled_at = now
        db.commit()
        db.refresh(row)
        return row

    def update(
        self,
        db: Session,
        user_id: int,
        scheduled_id: int,
        *,
        body_html: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> ScheduledEmail | None:
        """
        Change the text and/or time of a planned email; a failed one goes back to pending.

        Args:
            db: Active database session.
            user_id: Owner.
            scheduled_id: The planned email.
            body_html: New message, when changed.
            scheduled_at: New time, when changed.

        Returns:
            The updated row, or ``None`` when it is not the user's.

        Raises:
            ScheduledEmailError: Already sent/cancelled, empty message or invalid time.
        """
        row: ScheduledEmail | None = self._owned(db, user_id, scheduled_id)
        if row is None:
            return None
        if row.status not in _EDITABLE_STATUSES:
            raise ScheduledEmailError("Ce message n'est plus modifiable")
        if body_html is not None:
            row.body_html = self._validate_body(body_html)
        if scheduled_at is not None:
            row.scheduled_at = self._validate_moment(scheduled_at)
        elif row.status == ScheduledEmailStatus.FAILED.value:
            raise ScheduledEmailError("Choisissez une nouvelle heure d'envoi")
        row.status = ScheduledEmailStatus.PENDING.value
        row.error_message = None
        db.commit()
        db.refresh(row)
        return row

    def cancel(self, db: Session, user_id: int, scheduled_id: int) -> bool:
        """
        Cancel a planned email that has not gone out.

        Args:
            db: Active database session.
            user_id: Owner.
            scheduled_id: The planned email.

        Returns:
            ``True`` when cancelled, ``False`` when unknown, foreign or already sent.
        """
        row: ScheduledEmail | None = self._owned(db, user_id, scheduled_id)
        if row is None or row.status not in _EDITABLE_STATUSES:
            return False
        row.status = ScheduledEmailStatus.CANCELLED.value
        db.commit()
        return True

    def thread_items(
        self, db: Session, user_id: int, prospect_id: int | None, recipient_email: str
    ) -> list[dict[str, Any]]:
        """
        Planned emails of a conversation, shaped like conversation items.

        Scoped like the thread itself: by prospect when known, else by address.

        Args:
            db: Active database session.
            user_id: Owner.
            prospect_id: The thread's prospect.
            recipient_email: The thread's address (fallback scope).

        Returns:
            Pending, in-flight and failed planned emails, with the signature that will be appended.
        """
        query = select(ScheduledEmail).where(
            ScheduledEmail.user_id == user_id,
            ScheduledEmail.status.in_(_VISIBLE_STATUSES),
        )
        if prospect_id is not None:
            query = query.where(ScheduledEmail.prospect_id == prospect_id)
        else:
            query = query.where(ScheduledEmail.recipient_email == recipient_email)
        rows: list[ScheduledEmail] = list(db.execute(query.order_by(ScheduledEmail.scheduled_at)).scalars())
        # Rendered now, as the send renders it: the preview matches the email that will leave.
        signature_html: str = render_default_signature_html(db, user_id) if rows else ""
        return [
            {
                "direction": "outbound",
                "id": row.id,
                "subject": None,
                "body_text": None,
                "body_html": row.body_html,
                "counterpart": row.recipient_email,
                "timestamp": row.scheduled_at.isoformat(),
                "is_auto_reply": False,
                "is_conversation_reply": True,
                "pending": False,
                "status": None,
                "intent": None,
                "reply_id": row.reply_id,
                "scheduled_id": row.id,
                "scheduled_at": row.scheduled_at.isoformat(),
                "scheduled_status": row.status,
                "scheduled_created_at": row.created_at.isoformat(),
                "scheduled_error": row.error_message,
                "signature_html": signature_html,
            }
            for row in rows
        ]

    # ------------------------------------------------------------------ #
    # Sending
    # ------------------------------------------------------------------ #

    @staticmethod
    def _claim(db: Session, scheduled_id: int, from_statuses: tuple[str, ...]) -> bool:
        """Atomically move a row to ``sending``; ``False`` when another pass got it first."""
        result = db.execute(
            update(ScheduledEmail)
            .where(ScheduledEmail.id == scheduled_id, ScheduledEmail.status.in_(from_statuses))
            .values(status=ScheduledEmailStatus.SENDING.value)
        )
        db.commit()
        return result.rowcount == 1

    async def _send_claimed(self, db: Session, row: ScheduledEmail) -> dict[str, Any]:
        """Send a claimed row through the immediate path and record the outcome."""
        from services.conversation_service import conversation_service

        result: dict[str, Any]
        if row.kind != KIND_CONVERSATION_REPLY or row.reply_id is None:
            result = {"success": False, "error": "Type d'envoi inconnu"}
        else:
            try:
                result = await conversation_service.send_reply(db, row.user_id, row.reply_id, row.body_html)
            except Exception as exc:  # the row must never stay stuck in « sending »
                logger.exception("[ScheduledEmail] send %s crashed", row.id)
                result = {"success": False, "error": str(exc)}
            if result.get("error") == "not_found":
                result = {"success": False, "error": "La réponse d'origine n'existe plus"}

        db.refresh(row)
        if result.get("success"):
            row.status = ScheduledEmailStatus.SENT.value
            row.sent_at = _utc_now()
            row.email_log_id = result.get("email_log_id")
            row.error_message = None
            db.commit()
            return result

        row.status = ScheduledEmailStatus.FAILED.value
        row.error_message = str(result.get("error") or "Échec de l'envoi")[:500]
        db.commit()
        try:
            await notification_service.notify_email_event(
                db,
                user_id=row.user_id,
                event_name="email_scheduled_reply_failed",
                recipient_email=row.recipient_email,
                prospect_id=row.prospect_id,
            )
        except Exception:  # pragma: no cover — a notification never breaks the worker
            logger.warning("[ScheduledEmail] failure notification for %s not sent", row.id)
        return result

    async def send_now(self, db: Session, user_id: int, scheduled_id: int) -> dict[str, Any] | None:
        """
        Send a planned (or failed) email immediately.

        Args:
            db: Active database session.
            user_id: Owner.
            scheduled_id: The planned email.

        Returns:
            The send result, or ``None`` when the row is not the user's.

        Raises:
            ScheduledEmailError: Already sent, cancelled or being sent.
        """
        row: ScheduledEmail | None = self._owned(db, user_id, scheduled_id)
        if row is None:
            return None
        if not self._claim(db, row.id, _EDITABLE_STATUSES):
            raise ScheduledEmailError("Ce message n'est plus modifiable")
        db.refresh(row)
        return await self._send_claimed(db, row)

    async def dispatch_due(self) -> int:
        """
        Send every pending email whose time has come.

        Returns:
            The number of emails attempted.
        """
        db: Session = SessionLocal()
        attempted: int = 0
        try:
            due_ids: list[int] = list(
                db.execute(
                    select(ScheduledEmail.id).where(
                        ScheduledEmail.status == ScheduledEmailStatus.PENDING.value,
                        ScheduledEmail.scheduled_at <= _utc_now(),
                    )
                ).scalars()
            )
            for scheduled_id in due_ids:
                if not self._claim(db, scheduled_id, (ScheduledEmailStatus.PENDING.value,)):
                    continue
                row: ScheduledEmail | None = db.get(ScheduledEmail, scheduled_id)
                if row is None:
                    continue
                db.refresh(row)
                await self._send_claimed(db, row)
                attempted += 1
        finally:
            db.close()
        return attempted

    @staticmethod
    def fail_interrupted() -> int:
        """
        Mark rows left in ``sending`` by a restart as failed, never resend them blindly.

        A restart during a send leaves no proof of whether the mail left, so the user
        checks the thread and reschedules; a silent resend could double the message.

        Returns:
            The number of rows marked failed.
        """
        db: Session = SessionLocal()
        try:
            result = db.execute(
                update(ScheduledEmail)
                .where(ScheduledEmail.status == ScheduledEmailStatus.SENDING.value)
                .values(
                    status=ScheduledEmailStatus.FAILED.value,
                    error_message="Envoi interrompu par un redémarrage : vérifiez le fil puis reprogrammez",
                )
            )
            db.commit()
            return result.rowcount or 0
        finally:
            db.close()

    async def run_loop(self) -> None:
        """Worker: recover interrupted sends once, then dispatch due emails forever."""
        try:
            interrupted: int = await asyncio.to_thread(self.fail_interrupted)
            if interrupted:
                logger.warning("[ScheduledEmail] %d interrupted send(s) marked failed", interrupted)
        except Exception:
            logger.exception("[ScheduledEmail] recovery of interrupted sends failed")
        while True:
            try:
                await self.dispatch_due()
            except Exception:
                logger.exception("[ScheduledEmail] dispatch tick failed")
            await asyncio.sleep(_WORKER_INTERVAL_SECONDS)


scheduled_email_service = ScheduledEmailService()
