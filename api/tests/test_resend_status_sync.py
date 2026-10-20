"""
Unit tests for the polled Resend status sync: a polled open never counts as a human open.
"""

from datetime import datetime

from models.email_log import EmailLog
from services.resend_status_sync import ResendStatusSync

_SENT_AT = datetime(2026, 10, 20, 12, 30, 51)
_NOW = datetime(2026, 10, 20, 13, 36, 30)


def _email_log(status: str, **columns: datetime | None) -> EmailLog:
    """A bare email log row, never attached to a session."""
    return EmailLog(status=status, sent_at=_SENT_AT, **columns)


def test_a_polled_open_only_proves_delivery() -> None:
    """Resend saying « opened » moves a sent email to delivered, never to opened."""
    email_log = _email_log("sent")
    changed = ResendStatusSync.apply_last_event(email_log, "opened", _NOW)
    assert changed is True
    assert email_log.status == "delivered"
    assert email_log.delivered_at == _NOW
    assert email_log.opened_at is None
    assert email_log.machine_opened_at is None


def test_a_polled_open_on_a_delivered_email_changes_nothing() -> None:
    """The row the webhook already marked delivered keeps its status and its empty opened_at."""
    email_log = _email_log("delivered", delivered_at=_SENT_AT)
    changed = ResendStatusSync.apply_last_event(email_log, "opened", _NOW)
    assert changed is False
    assert email_log.status == "delivered"
    assert email_log.opened_at is None


def test_a_polled_click_does_not_invent_an_open() -> None:
    """A click fills clicked_at (and delivery) but leaves the human open to the webhook."""
    email_log = _email_log("delivered", delivered_at=_SENT_AT)
    changed = ResendStatusSync.apply_last_event(email_log, "clicked", _NOW)
    assert changed is True
    assert email_log.status == "clicked"
    assert email_log.clicked_at == _NOW
    assert email_log.delivered_at == _SENT_AT
    assert email_log.opened_at is None


def test_an_existing_timestamp_is_kept() -> None:
    """A bounce stamps bounced_at once; a second pass never overwrites it."""
    bounced_at = datetime(2026, 10, 19, 10, 30, 48)
    email_log = _email_log("sent", bounced_at=bounced_at)
    ResendStatusSync.apply_last_event(email_log, "bounced", _NOW)
    assert email_log.status == "bounced"
    assert email_log.bounced_at == bounced_at


def test_an_unknown_event_changes_nothing() -> None:
    """An event Resend may add later is ignored rather than guessed."""
    email_log = _email_log("sent")
    assert ResendStatusSync.apply_last_event(email_log, "queued", _NOW) is False
    assert email_log.status == "sent"
