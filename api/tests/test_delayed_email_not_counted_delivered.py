"""
An email the recipient's host holds back is delayed, not delivered: the Resend webhook leaves its delivery
time empty until the real delivery, the figures do not count it as arrived, and the rows stamped before
that change are cleared by a migration.
"""

import asyncio
import json
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from api.v1.routes import webhooks
from migrations.clear_delivered_at_of_delayed_emails import run_migration
from models.email_log import EmailLog
from services.email_log_stats import aggregate_email_log_counts

_SENT_AT = datetime(2026, 11, 13, 8, 0, 37)
_STAMPED_BY_THE_DELAY = datetime(2026, 11, 13, 8, 7, 46)


class _ResendRequest:
    """Stand-in for the incoming HTTP request: only its raw body is read."""

    def __init__(self, event_type: str, email_log_id: int) -> None:
        self._body: bytes = json.dumps(
            {"type": event_type, "data": {"email_id": "resend-message-1", "tags": {"email_log_id": str(email_log_id)}}}
        ).encode()

    async def body(self) -> bytes:
        return self._body


def _email_log(db: Session, status: str, delivered_at: datetime | None = None) -> EmailLog:
    email_log = EmailLog(
        user_id=1,
        recipient_email="projardins@outlook.com",
        subject="le site",
        body_html="<p>le site</p>",
        provider="resend",
        status=status,
        sent_at=_SENT_AT,
        delivered_at=delivered_at,
    )
    db.add(email_log)
    db.commit()
    return email_log


@pytest.fixture
def notified_email_events(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The webhook with its signature check, funnel capture and notification stubbed; returns the notified events."""
    notified: list[str] = []

    async def no_capture(**_properties: Any) -> None:
        return None

    async def record_notification(_db: Session, *, event_name: str, **_details: Any) -> None:
        notified.append(event_name)

    monkeypatch.setattr(webhooks, "_verify_signature", lambda *_args: True)
    monkeypatch.setattr(webhooks.posthog_service, "capture", no_capture)
    monkeypatch.setattr(webhooks.notification_service, "notify_email_event", record_notification)
    return notified


def _receive(db: Session, event_type: str, email_log: EmailLog) -> None:
    asyncio.run(
        webhooks.resend_webhook(
            _ResendRequest(event_type, email_log.id), svix_id="", svix_timestamp="", svix_signature="", db=db
        )
    )


def test_a_delayed_email_is_notified_but_gets_no_delivery_time(db: Session, notified_email_events: list[str]) -> None:
    email_log = _email_log(db, "sent")

    _receive(db, "email.delivery_delayed", email_log)

    assert email_log.status == "delivery_delayed"
    assert email_log.delivered_at is None
    assert notified_email_events == ["email_delivery_delayed"]
    assert aggregate_email_log_counts(db).delivered == 0


@pytest.mark.usefixtures("notified_email_events")
def test_the_delivery_that_follows_a_delay_writes_the_delivery_time(db: Session) -> None:
    email_log = _email_log(db, "sent")

    _receive(db, "email.delivery_delayed", email_log)
    _receive(db, "email.delivered", email_log)

    assert email_log.status == "delivered"
    assert email_log.delivered_at is not None
    assert aggregate_email_log_counts(db).delivered == 1


def test_the_migration_clears_the_delivery_time_stamped_by_a_delay(engine: Engine, db: Session) -> None:
    delayed = _email_log(db, "delivery_delayed", delivered_at=_STAMPED_BY_THE_DELAY)
    delivered = _email_log(db, "delivered", delivered_at=_STAMPED_BY_THE_DELAY)

    run_migration(engine)
    run_migration(engine)
    db.expire_all()

    assert db.get(EmailLog, delayed.id).delivered_at is None
    assert db.get(EmailLog, delivered.id).delivered_at == _STAMPED_BY_THE_DELAY
    assert aggregate_email_log_counts(db).delivered == 1
