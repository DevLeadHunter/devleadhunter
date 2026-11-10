"""A J+30 relance skipped because the prospect answered an email stays skipped, unless the operator revives it by hand.

A revived relance goes out despite the reply that skipped it; a reply received after the revival skips it again.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.v1.routes.sms import router as sms_router
from core.database import get_db
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.email_reply import EmailReply
from models.prospect_db import ProspectDB
from models.sms_auto_queue import SmsAutoQueue
from models.sms_config import SmsConfig
from services.auth_service import get_current_user
from services.sms_auto_campaign_service import sms_auto_campaign_service
from services.sms_automation_service import sms_automation_service
from services.sms_relance_service import sms_relance_service
from services.sms_service import sms_service
from tests.sms_fakes import AsyncCallRecorder

_USER_ID = 7
_REPLY_REASON = "A répondu à l'email"
_NOW: datetime = datetime.now(UTC).replace(tzinfo=None)


def _prospect_who_replied(db: Session) -> ProspectDB:
    prospect = ProspectDB(
        user_id=_USER_ID,
        name="Bearn Services Exterieurs",
        category="Paysagiste",
        source="search",
        phone="06 50 93 36 31",
        email="bearn@example.com",
        country="FR",
    )
    db.add(prospect)
    db.flush()
    db.add(
        DemoSite(
            user_id=_USER_ID,
            prospect_id=prospect.id,
            slug="bearn-services-exterieurs",
            business_name="Bearn Services Exterieurs",
            status="active",
            expires_at=_NOW + timedelta(days=7),
        )
    )
    email_log = EmailLog(
        user_id=_USER_ID,
        prospect_id=prospect.id,
        recipient_email="bearn@example.com",
        subject="le site de Bearn Services Exterieurs",
        body_html="<p>Bonjour</p>",
        provider="resend",
        status="replied",
        sent_at=_NOW - timedelta(days=14),
        replied_at=_NOW - timedelta(days=12),
    )
    db.add(email_log)
    db.flush()
    _reply(db, prospect, email_log.id, received_at=_NOW - timedelta(days=12))
    db.add(SmsConfig(user_id=_USER_ID, sender="Dibodev", auto_relance_enabled=True))
    db.commit()
    return prospect


def _reply(
    db: Session, prospect: ProspectDB, email_log_id: int, *, received_at: datetime, is_auto_reply: bool = False
) -> None:
    db.add(
        EmailReply(
            email_log_id=email_log_id,
            user_id=_USER_ID,
            prospect_id=prospect.id,
            from_email="bearn@example.com",
            resend_email_id=f"received-{received_at.isoformat()}",
            matched_by="token",
            is_auto_reply=is_auto_reply,
            received_at=received_at,
        )
    )
    db.commit()


def _relance(db: Session, prospect: ProspectDB, *, status: str) -> SmsAutoQueue:
    row = SmsAutoQueue(
        user_id=_USER_ID,
        prospect_id=prospect.id,
        kind="relance",
        status=status,
        skip_reason=_REPLY_REASON if status == "skipped" else None,
        scheduled_at=_NOW + timedelta(days=16),
        emailed_at=_NOW - timedelta(days=14),
    )
    db.add(row)
    db.commit()
    return row


def _revive_by_hand(db: Session, row: SmsAutoQueue) -> int:
    application = FastAPI()
    application.include_router(sms_router)
    application.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=_USER_ID)
    application.dependency_overrides[get_db] = lambda: db
    response = TestClient(application).post(
        f"{sms_router.prefix}/auto-queue/{row.id}/reschedule",
        json={"scheduled_at": (_NOW + timedelta(days=16)).isoformat()},
    )
    db.refresh(row)
    return response.status_code


@pytest.fixture
def relance_sends(monkeypatch: pytest.MonkeyPatch) -> AsyncCallRecorder:
    """The relance sends of the worker, recorded instead of reaching smsmode, every day inside the legal window."""
    recorder = AsyncCallRecorder(result=True)
    monkeypatch.setattr(sms_relance_service, "send_relance", recorder)
    monkeypatch.setattr(sms_service, "legal_window_refusal", lambda country=None: None)
    monkeypatch.setattr(sms_auto_campaign_service, "get", lambda db, user_id: None)
    monkeypatch.setattr(
        sms_automation_service,
        "enabled_configs",
        lambda db: db.query(SmsConfig).filter(SmsConfig.user_id == _USER_ID).all(),
    )
    return recorder


def test_a_reply_still_skips_a_planned_relance(db: Session) -> None:
    row = _relance(db, _prospect_who_replied(db), status="pending")

    sms_automation_service.revalidate(db)

    assert (row.status, row.skip_reason) == ("skipped", _REPLY_REASON)


def test_a_relance_revived_by_hand_stays_planned_despite_the_earlier_reply(db: Session) -> None:
    row = _relance(db, _prospect_who_replied(db), status="skipped")

    assert _revive_by_hand(db, row) == 200
    sms_automation_service.revalidate(db)

    assert row.status == "pending"
    assert row.revived_at is not None


def test_a_reply_after_the_revival_skips_the_relance_again(db: Session) -> None:
    prospect = _prospect_who_replied(db)
    first_email_id: int = db.query(EmailLog.id).scalar()
    row = _relance(db, prospect, status="skipped")
    _revive_by_hand(db, row)

    _reply(db, prospect, first_email_id, received_at=row.revived_at + timedelta(minutes=5))
    sms_automation_service.revalidate(db)

    assert (row.status, row.skip_reason) == ("skipped", _REPLY_REASON)


def test_an_out_of_office_after_the_revival_leaves_the_relance_planned(db: Session) -> None:
    prospect = _prospect_who_replied(db)
    first_email_id: int = db.query(EmailLog.id).scalar()
    row = _relance(db, prospect, status="skipped")
    _revive_by_hand(db, row)

    _reply(db, prospect, first_email_id, received_at=row.revived_at + timedelta(minutes=5), is_auto_reply=True)
    sms_automation_service.revalidate(db)

    assert row.status == "pending"


def test_moving_a_planned_relance_is_not_a_revival(db: Session) -> None:
    row = _relance(db, _prospect_who_replied(db), status="pending")

    assert _revive_by_hand(db, row) == 200

    assert row.revived_at is None


def test_the_worker_sends_a_revived_relance_once_due(db: Session, relance_sends: AsyncCallRecorder) -> None:
    row = _relance(db, _prospect_who_replied(db), status="skipped")
    _revive_by_hand(db, row)
    row.scheduled_at = _NOW - timedelta(minutes=1)
    db.commit()

    sent = asyncio.run(sms_automation_service._send_due(db))

    assert sent == 1
    assert row.status == "sent"
    assert len(relance_sends.calls) == 1


def test_the_worker_never_texts_a_prospect_who_replied_without_a_revival(
    db: Session, relance_sends: AsyncCallRecorder
) -> None:
    row = _relance(db, _prospect_who_replied(db), status="pending")
    row.scheduled_at = _NOW - timedelta(minutes=1)
    db.commit()

    sent = asyncio.run(sms_automation_service._send_due(db))

    assert sent == 0
    assert (row.status, row.skip_reason) == ("skipped", _REPLY_REASON)
    assert relance_sends.calls == []
