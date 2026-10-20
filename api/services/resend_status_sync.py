"""
Apply a Resend ``last_event`` to an email log when the status is polled instead of pushed.

The poll (``GET /emails/{id}``) only says which event came last, never when it happened, so it
cannot tell a Gmail prefetch from a human read the way the webhook does. Opens are therefore
left to the webhook: a polled ``opened`` only proves the email was delivered.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from enums.email_status import EmailStatus
from models.email_log import EmailLog


class ResendStatusSync:
    """Translate Resend's polled ``last_event`` into an email log status and its timestamps."""

    STATUS_BY_LAST_EVENT: ClassVar[dict[str, str]] = {
        "scheduled": EmailStatus.SCHEDULED.value,
        "sent": EmailStatus.SENT.value,
        "delivered": EmailStatus.DELIVERED.value,
        "delivery_delayed": EmailStatus.DELIVERY_DELAYED.value,
        "opened": EmailStatus.DELIVERED.value,
        "clicked": EmailStatus.CLICKED.value,
        "bounced": EmailStatus.BOUNCED.value,
        "complained": EmailStatus.COMPLAINED.value,
        "failed": EmailStatus.FAILED.value,
        "suppressed": EmailStatus.SUPPRESSED.value,
    }

    TIMESTAMP_COLUMNS_BY_STATUS: ClassVar[dict[str, list[str]]] = {
        EmailStatus.DELIVERED.value: ["delivered_at"],
        EmailStatus.DELIVERY_DELAYED.value: [],
        EmailStatus.CLICKED.value: ["delivered_at", "clicked_at"],
        EmailStatus.BOUNCED.value: ["bounced_at"],
        EmailStatus.COMPLAINED.value: ["complained_at"],
        EmailStatus.FAILED.value: ["failed_at"],
        EmailStatus.SUPPRESSED.value: ["suppressed_at"],
    }

    @classmethod
    def apply_last_event(cls, email_log: EmailLog, last_event: str, now: datetime) -> bool:
        """Move the log to the status implied by ``last_event`` and fill the timestamps it implies.

        Args:
            email_log: The row to update in place.
            last_event: Resend's ``last_event`` value for that message.
            now: Timestamp written to the columns the new status implies, when they are still empty.

        Returns:
            True when the status changed, False when the event is unknown or already reflected.
        """
        new_status: str | None = cls.STATUS_BY_LAST_EVENT.get(last_event)
        if not new_status or new_status == email_log.status:
            return False
        email_log.status = new_status
        for column_name in cls.TIMESTAMP_COLUMNS_BY_STATUS.get(new_status, []):
            if not getattr(email_log, column_name):
                setattr(email_log, column_name, now)
        return True
