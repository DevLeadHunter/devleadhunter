"""A spam report ends every contact with the prospect: « ne plus contacter » is set and pending sends are held back."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import api.v1.routes.webhooks as webhooks_module
import services.prospect_service as prospect_service_module
from core.database import get_db
from enums.email_status import EmailStatus
from models.email_log import EmailLog
from models.email_queue import EmailQueue
from models.prospect_db import ProspectDB
from services.prospect_service import SPAM_REPORT_REASON, prospect_service

_USER_ID = 7
_MESSAGE_ID = "msg_carprog86"


@pytest.fixture(autouse=True)
def quiet_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    """No activity feed, PostHog capture or push leaves the test; the webhook accepts unsigned calls."""

    async def nothing(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(prospect_service_module.activity_log_service, "record", lambda **_kwargs: None)
    monkeypatch.setattr(webhooks_module.posthog_service, "capture", nothing)
    monkeypatch.setattr(webhooks_module.notification_service, "notify_email_event", nothing)
    monkeypatch.setattr(webhooks_module.settings, "resend_webhook_secret", "")


def _prospect(db: Session, *, do_not_contact: bool = False, reason: str | None = None) -> ProspectDB:
    prospect = ProspectDB(
        name="Carprog86",
        category="Garage",
        source="search",
        confidence=2,
        user_id=_USER_ID,
        email="carprog86@hotmail.com",
        do_not_contact=do_not_contact,
        do_not_contact_reason=reason,
    )
    db.add(prospect)
    db.commit()
    return prospect


def _pending_follow_up(db: Session, prospect: ProspectDB) -> EmailQueue:
    follow_up = EmailQueue(
        user_id=_USER_ID,
        campaign_id=27,
        prospect_id=prospect.id,
        queue_type="followup",
        follow_up_index=1,
        scheduled_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=5),
        status="pending",
    )
    db.add(follow_up)
    db.commit()
    return follow_up


def _sent_email(db: Session, prospect: ProspectDB, status: str) -> EmailLog:
    email_log = EmailLog(
        user_id=_USER_ID,
        prospect_id=prospect.id,
        campaign_id=27,
        recipient_email="carprog86@hotmail.com",
        subject="le site de Carprog86",
        body_html="<p>Bonjour</p>",
        status=status,
        provider="resend",
        provider_message_id=_MESSAGE_ID,
    )
    db.add(email_log)
    db.commit()
    return email_log


def _report_spam(db: Session) -> int:
    application = FastAPI()
    application.include_router(webhooks_module.router)
    application.dependency_overrides[get_db] = lambda: db
    response = TestClient(application).post(
        "/webhooks/resend", json={"type": "email.complained", "data": {"email_id": _MESSAGE_ID}}
    )
    return response.status_code


def test_a_spam_report_flags_the_prospect_and_holds_back_its_follow_up(db: Session) -> None:
    prospect = _prospect(db)
    follow_up = _pending_follow_up(db, prospect)

    flagged = asyncio.run(prospect_service.stop_contact_after_spam_report(db, prospect.id, user_id=_USER_ID))

    assert flagged is True
    db.refresh(prospect)
    db.refresh(follow_up)
    assert prospect.do_not_contact is True
    assert prospect.do_not_contact_reason == SPAM_REPORT_REASON
    assert follow_up.status == "skipped"
    assert follow_up.skip_reason == f"Ne plus contacter — {SPAM_REPORT_REASON}"


def test_a_prospect_already_flagged_keeps_its_first_reason(db: Session) -> None:
    prospect = _prospect(db, do_not_contact=True, reason="Pas chaud au téléphone")

    flagged = asyncio.run(prospect_service.stop_contact_after_spam_report(db, prospect.id, user_id=_USER_ID))

    assert flagged is False
    db.refresh(prospect)
    assert prospect.do_not_contact_reason == "Pas chaud au téléphone"


def test_an_email_sent_to_no_prospect_flags_nobody(db: Session) -> None:
    assert asyncio.run(prospect_service.stop_contact_after_spam_report(db, None, user_id=_USER_ID)) is False


def test_the_resend_complaint_webhook_stops_all_contact(db: Session) -> None:
    prospect = _prospect(db)
    follow_up = _pending_follow_up(db, prospect)
    email_log = _sent_email(db, prospect, EmailStatus.DELIVERED.value)

    assert _report_spam(db) == 204

    db.refresh(email_log)
    db.refresh(prospect)
    db.refresh(follow_up)
    assert email_log.status == EmailStatus.COMPLAINED.value
    assert email_log.complained_at is not None
    assert prospect.do_not_contact is True
    assert follow_up.status == "skipped"


def test_a_report_on_an_email_already_replied_to_still_stops_all_contact(db: Session) -> None:
    prospect = _prospect(db)
    email_log = _sent_email(db, prospect, EmailStatus.REPLIED.value)

    assert _report_spam(db) == 204

    db.refresh(email_log)
    db.refresh(prospect)
    assert email_log.status == EmailStatus.REPLIED.value
    assert prospect.do_not_contact is True
