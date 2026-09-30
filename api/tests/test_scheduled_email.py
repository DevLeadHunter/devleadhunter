"""Scheduled conversation replies — planning, editing, dispatch and restart recovery."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import services.conversation_service as conversation_module
import services.scheduled_email_service as scheduled_module
from enums.scheduled_email_status import ScheduledEmailStatus
from models.email_reply import EmailReply
from models.scheduled_email import ScheduledEmail
from services.scheduled_email_service import ScheduledEmailError, ScheduledEmailService

USER_ID: int = 1


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _add_reply(db: Session, *, user_id: int = USER_ID) -> EmailReply:
    reply = EmailReply(
        email_log_id=5,
        user_id=user_id,
        prospect_id=200,
        from_email="hugo@example.ch",
        subject="Re: le site",
        resend_email_id=f"rcv-{user_id}-{_now().timestamp()}",
        matched_by="token",
        received_at=_now() - timedelta(days=7),
    )
    db.add(reply)
    db.commit()
    return reply


@pytest.fixture
def service(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> ScheduledEmailService:
    """The service, with its worker sessions bound to the test database."""
    monkeypatch.setattr(scheduled_module, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(scheduled_module.notification_service, "notify_email_event", AsyncMock())
    return ScheduledEmailService()


def _mock_send(monkeypatch: pytest.MonkeyPatch, result: dict[str, Any]) -> AsyncMock:
    send = AsyncMock(return_value=result)
    monkeypatch.setattr(conversation_module.conversation_service, "send_reply", send)
    return send


def test_schedule_reply_plans_and_marks_reply_handled(db: Session, service: ScheduledEmailService) -> None:
    reply = _add_reply(db)
    moment = datetime.now(UTC) + timedelta(hours=10)

    row = service.schedule_reply(db, USER_ID, reply.id, "<p>Bonjour Hugo</p>", moment)

    assert row is not None
    assert row.status == ScheduledEmailStatus.PENDING.value
    assert row.scheduled_at == moment.replace(tzinfo=None)
    assert row.recipient_email == "hugo@example.ch"
    db.refresh(reply)
    assert reply.handled_at is not None


def test_schedule_rejects_past_time_and_foreign_reply(db: Session, service: ScheduledEmailService) -> None:
    reply = _add_reply(db)
    with pytest.raises(ScheduledEmailError):
        service.schedule_reply(db, USER_ID, reply.id, "<p>x</p>", _now() - timedelta(minutes=5))
    with pytest.raises(ScheduledEmailError):
        service.schedule_reply(db, USER_ID, reply.id, "   ", _now() + timedelta(hours=1))
    assert service.schedule_reply(db, 999, reply.id, "<p>x</p>", _now() + timedelta(hours=1)) is None


def test_dispatch_sends_only_due_rows(
    db: Session, service: ScheduledEmailService, monkeypatch: pytest.MonkeyPatch
) -> None:
    reply = _add_reply(db)
    due = service.schedule_reply(db, USER_ID, reply.id, "<p>due</p>", _now() + timedelta(hours=1))
    later = service.schedule_reply(db, USER_ID, reply.id, "<p>later</p>", _now() + timedelta(hours=5))
    assert due is not None and later is not None
    due.scheduled_at = _now() - timedelta(seconds=5)
    db.commit()
    send = _mock_send(monkeypatch, {"success": True, "email_log_id": 42})

    attempted = asyncio.run(service.dispatch_due())

    assert attempted == 1
    assert send.await_args.args[1:] == (USER_ID, reply.id, "<p>due</p>")
    db.expire_all()
    assert db.get(ScheduledEmail, due.id).status == ScheduledEmailStatus.SENT.value
    assert db.get(ScheduledEmail, due.id).email_log_id == 42
    assert db.get(ScheduledEmail, later.id).status == ScheduledEmailStatus.PENDING.value


def test_failed_send_is_kept_and_can_be_replanned(
    db: Session, service: ScheduledEmailService, monkeypatch: pytest.MonkeyPatch
) -> None:
    reply = _add_reply(db)
    row = service.schedule_reply(db, USER_ID, reply.id, "<p>x</p>", _now() + timedelta(hours=1))
    assert row is not None
    _mock_send(monkeypatch, {"success": False, "error": "Resend down"})

    asyncio.run(service.send_now(db, USER_ID, row.id))

    db.refresh(row)
    assert row.status == ScheduledEmailStatus.FAILED.value
    assert row.error_message == "Resend down"
    with pytest.raises(ScheduledEmailError):
        service.update(db, USER_ID, row.id, body_html="<p>y</p>")
    updated = service.update(db, USER_ID, row.id, scheduled_at=_now() + timedelta(hours=2))
    assert updated is not None and updated.status == ScheduledEmailStatus.PENDING.value


def test_cancel_and_interrupted_recovery(db: Session, service: ScheduledEmailService) -> None:
    reply = _add_reply(db)
    first = service.schedule_reply(db, USER_ID, reply.id, "<p>a</p>", _now() + timedelta(hours=1))
    second = service.schedule_reply(db, USER_ID, reply.id, "<p>b</p>", _now() + timedelta(hours=1))
    assert first is not None and second is not None

    assert service.cancel(db, USER_ID, first.id) is True
    assert service.cancel(db, USER_ID, first.id) is False

    second.status = ScheduledEmailStatus.SENDING.value
    db.commit()
    assert service.fail_interrupted() == 1
    db.expire_all()
    assert db.get(ScheduledEmail, second.id).status == ScheduledEmailStatus.FAILED.value


def test_thread_items_expose_pending_rows_only(db: Session, service: ScheduledEmailService) -> None:
    reply = _add_reply(db)
    kept = service.schedule_reply(db, USER_ID, reply.id, "<p>a</p>", _now() + timedelta(hours=1))
    dropped = service.schedule_reply(db, USER_ID, reply.id, "<p>b</p>", _now() + timedelta(hours=2))
    assert kept is not None and dropped is not None
    service.cancel(db, USER_ID, dropped.id)

    items = service.thread_items(db, USER_ID, 200, "hugo@example.ch")

    assert [item["scheduled_id"] for item in items] == [kept.id]
    assert items[0]["is_conversation_reply"] is True
