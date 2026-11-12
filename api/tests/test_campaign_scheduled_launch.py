"""A draft campaign launched at a scheduled date and time: scheduling, cancelling, the launch itself, never twice, and the failures that leave a draft."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import services.campaign_scheduled_launch_service as scheduled_launch_module
import services.campaign_service as campaign_service_module
from api.v1.routes.campaigns import router as campaigns_router
from core.clock import naive_utc_now
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from migrations.add_campaign_scheduled_launch import run_migration
from models.campaign import Campaign, CampaignStatus
from models.demo_site import DemoSite
from models.email_queue import EmailQueue
from models.email_template import EmailTemplate
from models.prospect_db import ProspectDB
from models.resend_config import ResendConfig
from models.sms_config import SmsConfig
from schemas.campaign import CampaignUpdate
from services.auth_service import get_current_user
from services.campaign_launch_service import campaign_launch_service
from services.campaign_queue_service import CampaignQueueService
from services.campaign_scheduled_launch_service import (
    CampaignLaunchUnderwayError,
    CampaignScheduledLaunchError,
    CampaignScheduledLaunchService,
)
from services.campaign_service import campaign_service

_USER_ID = 7
_OTHER_USER_ID = 8


@pytest.fixture
def notified_errors(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """The error notifications the service raised, none of them really sent."""
    notify_error = AsyncMock()
    monkeypatch.setattr(scheduled_launch_module.notification_service, "notify_error", notify_error)
    return notify_error


@pytest.fixture
def service(
    engine: Engine, monkeypatch: pytest.MonkeyPatch, notified_errors: AsyncMock
) -> CampaignScheduledLaunchService:
    """The service, its loop sessions bound to the test database and its activity feed silenced."""
    monkeypatch.setattr(scheduled_launch_module, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(scheduled_launch_module.activity_log_service, "record", lambda **_entry: None)
    return CampaignScheduledLaunchService()


def _resend_sender(db: Session, user_id: int) -> ResendConfig | None:
    return db.execute(select(ResendConfig).where(ResendConfig.user_id == user_id)).scalar_one_or_none()


def _prospect(db: Session, campaign: Campaign, name: str, *, phone: str | None = None) -> ProspectDB:
    prospect = ProspectDB(
        name=name,
        email=f"{name.lower().replace(' ', '-')}@example.com",
        phone=phone,
        category="garage",
        source="google",
        confidence=2,
        user_id=campaign.user_id,
    )
    db.add(prospect)
    db.flush()
    campaign.prospects.append(prospect)
    return prospect


def _email_draft(
    db: Session, *, user_id: int = _USER_ID, prospect_names: tuple[str, ...] = ("Garage Lefort", "Jardins Morel")
) -> Campaign:
    """An email draft ready to launch: a first template without any link, a sender, and its prospects."""
    template = EmailTemplate(user_id=user_id, name="Dernier rappel", subject="Votre site", body_html="<p>Bonjour</p>")
    db.add(template)
    db.flush()
    campaign = Campaign(
        user_id=user_id,
        name="Derniers rappels",
        status=CampaignStatus.DRAFT,
        channel="email",
        template_id=template.id,
    )
    db.add(campaign)
    db.flush()
    for name in prospect_names:
        _prospect(db, campaign, name)
    if _resend_sender(db, user_id) is None:
        db.add(ResendConfig(user_id=user_id, api_key="re_test", from_email="jean@mail.example.com"))
    db.commit()
    return campaign


def _schedule_in_the_past(db: Session, campaign: Campaign) -> None:
    """A launch whose time has come (the service itself refuses a time in the past)."""
    campaign.scheduled_launch_at = naive_utc_now() - timedelta(minutes=2)
    db.commit()


def _queued_sends(db: Session, campaign: Campaign) -> int:
    return db.execute(
        select(func.count()).select_from(EmailQueue).where(EmailQueue.campaign_id == campaign.id)
    ).scalar_one()


def _status(db: Session, campaign: Campaign) -> CampaignStatus:
    db.refresh(campaign)
    return campaign.status


def test_scheduling_keeps_the_chosen_time_as_naive_utc(db: Session, service: CampaignScheduledLaunchService) -> None:
    campaign = _email_draft(db)
    paris_time = (datetime.now(UTC) + timedelta(days=7)).astimezone(timezone(timedelta(hours=1)))

    service.schedule(db, campaign, paris_time)

    assert campaign.scheduled_launch_at == paris_time.astimezone(UTC).replace(tzinfo=None)
    assert campaign.scheduled_launch_error is None
    assert _status(db, campaign) is CampaignStatus.DRAFT


def test_scheduling_is_refused_in_the_past_and_beyond_ninety_days(
    db: Session, service: CampaignScheduledLaunchService
) -> None:
    campaign = _email_draft(db)

    with pytest.raises(CampaignScheduledLaunchError, match="dans le futur"):
        service.schedule(db, campaign, naive_utc_now() - timedelta(minutes=5))
    with pytest.raises(CampaignScheduledLaunchError, match="90 jours"):
        service.schedule(db, campaign, naive_utc_now() + timedelta(days=91))

    assert campaign.scheduled_launch_at is None


def test_scheduling_is_refused_when_the_launch_itself_would_be(
    db: Session, service: CampaignScheduledLaunchService
) -> None:
    tomorrow = naive_utc_now() + timedelta(days=1)
    without_template = _email_draft(db)
    without_template.template_id = None
    without_sender = _email_draft(db, user_id=_OTHER_USER_ID)
    db.delete(_resend_sender(db, _OTHER_USER_ID))
    sms_without_sender = Campaign(user_id=_USER_ID, name="SMS", status=CampaignStatus.DRAFT, channel="sms")
    already_running = _email_draft(db)
    already_running.status = CampaignStatus.ACTIVE
    db.add(sms_without_sender)
    db.commit()

    with pytest.raises(CampaignScheduledLaunchError, match="template J1"):
        service.schedule(db, without_template, tomorrow)
    with pytest.raises(CampaignScheduledLaunchError, match="Configuration Resend manquante"):
        service.schedule(db, without_sender, tomorrow)
    with pytest.raises(CampaignScheduledLaunchError, match="Expéditeur SMS manquant"):
        service.schedule(db, sms_without_sender, tomorrow)
    with pytest.raises(CampaignScheduledLaunchError, match="brouillon"):
        service.schedule(db, already_running, tomorrow)


def test_scheduling_again_moves_the_launch(db: Session, service: CampaignScheduledLaunchService) -> None:
    campaign = _email_draft(db)
    service.schedule(db, campaign, naive_utc_now() + timedelta(days=1))
    later = naive_utc_now() + timedelta(days=3)

    service.schedule(db, campaign, later)

    assert campaign.scheduled_launch_at == later


def test_cancelling_drops_the_scheduled_launch_and_leaves_the_draft(
    db: Session, service: CampaignScheduledLaunchService
) -> None:
    campaign = _email_draft(db)
    service.schedule(db, campaign, naive_utc_now() + timedelta(days=1))

    service.cancel(db, campaign)
    launched = asyncio.run(service.launch_due())

    assert launched == 0
    assert campaign.scheduled_launch_at is None
    assert _status(db, campaign) is CampaignStatus.DRAFT
    assert _queued_sends(db, campaign) == 0


def test_a_launch_waits_for_its_time_then_starts_the_campaign(
    db: Session, service: CampaignScheduledLaunchService, monkeypatch: pytest.MonkeyPatch, notified_errors: AsyncMock
) -> None:
    campaign = _email_draft(db)
    scheduled_at = naive_utc_now() + timedelta(hours=3)
    service.schedule(db, campaign, scheduled_at)

    assert asyncio.run(service.launch_due()) == 0
    assert _status(db, campaign) is CampaignStatus.DRAFT

    monkeypatch.setattr(scheduled_launch_module, "naive_utc_now", lambda: scheduled_at + timedelta(seconds=20))
    assert asyncio.run(service.launch_due()) == 1

    assert _status(db, campaign) is CampaignStatus.ACTIVE
    assert campaign.started_at is not None
    assert campaign.scheduled_launch_at is None
    assert campaign.scheduled_launch_claimed_at is None
    assert campaign.scheduled_launch_error is None
    assert _queued_sends(db, campaign) == 2
    notified_errors.assert_not_awaited()


def test_the_guards_of_the_queue_apply_when_the_launch_starts(
    db: Session, service: CampaignScheduledLaunchService
) -> None:
    campaign = _email_draft(db, prospect_names=("Garage Lefort", "Jardins Morel", "Garage Tessier"))
    refused, _reader, _other_reader = campaign.prospects
    service.schedule(db, campaign, naive_utc_now() + timedelta(days=1))
    refused.do_not_contact = True
    _schedule_in_the_past(db, campaign)

    asyncio.run(service.launch_due())

    queued_prospect_ids = set(
        db.execute(select(EmailQueue.prospect_id).where(EmailQueue.campaign_id == campaign.id)).scalars()
    )
    assert _status(db, campaign) is CampaignStatus.ACTIVE
    assert refused.id not in queued_prospect_ids
    assert len(queued_prospect_ids) == 2


def test_an_sms_campaign_starts_at_its_time_too(db: Session, service: CampaignScheduledLaunchService) -> None:
    campaign = Campaign(user_id=_USER_ID, name="SMS de premier contact", status=CampaignStatus.DRAFT, channel="sms")
    db.add(campaign)
    db.flush()
    prospect = _prospect(db, campaign, "Paysages Renaud", phone="06 12 34 56 78")
    db.add(SmsConfig(user_id=_USER_ID, sender="Dibodev", enabled=True))
    db.add(
        DemoSite(
            user_id=_USER_ID,
            prospect_id=prospect.id,
            slug="paysages-renaud",
            business_name="Paysages Renaud",
            status=DemoSiteStatus.ACTIVE.value,
            demo_url="https://demo.example.com/paysages-renaud",
            expires_at=naive_utc_now() + timedelta(days=21),
        )
    )
    db.commit()
    service.schedule(db, campaign, naive_utc_now() + timedelta(days=1))
    _schedule_in_the_past(db, campaign)

    asyncio.run(service.launch_due())

    assert _status(db, campaign) is CampaignStatus.ACTIVE
    assert _queued_sends(db, campaign) == 1


def test_a_due_launch_is_taken_only_once(db: Session, engine: Engine, service: CampaignScheduledLaunchService) -> None:
    campaign = _email_draft(db)
    _schedule_in_the_past(db, campaign)
    first_loop, second_loop = sessionmaker(bind=engine)(), sessionmaker(bind=engine)()

    try:
        assert service._claim(first_loop, campaign.id) is True
        assert service._claim(second_loop, campaign.id) is False
    finally:
        first_loop.close()
        second_loop.close()


def test_two_ticks_never_queue_a_campaign_twice(db: Session, service: CampaignScheduledLaunchService) -> None:
    campaign = _email_draft(db)
    _schedule_in_the_past(db, campaign)

    assert asyncio.run(service.launch_due()) == 1
    assert asyncio.run(service.launch_due()) == 0

    assert _queued_sends(db, campaign) == 2


def test_a_restart_after_the_sends_were_queued_does_not_queue_them_again(
    db: Session,
    service: CampaignScheduledLaunchService,
    monkeypatch: pytest.MonkeyPatch,
    notified_errors: AsyncMock,
) -> None:
    campaign = _email_draft(db)
    _schedule_in_the_past(db, campaign)
    assert service._claim(db, campaign.id) is True
    db.refresh(campaign)
    campaign_launch_service.launch(db, campaign)
    launched_again = Mock()
    monkeypatch.setattr(campaign_launch_service, "launch", launched_again)

    assert asyncio.run(service.resume_interrupted()) == 1

    launched_again.assert_not_called()

    assert _status(db, campaign) is CampaignStatus.ACTIVE
    assert campaign.scheduled_launch_at is None
    assert campaign.scheduled_launch_claimed_at is None
    assert _queued_sends(db, campaign) == 2
    assert asyncio.run(service.launch_due()) == 0
    notified_errors.assert_not_awaited()


def test_a_restart_before_anything_was_queued_launches_once(
    db: Session, service: CampaignScheduledLaunchService
) -> None:
    cut_before_activation = _email_draft(db)
    cut_after_activation = _email_draft(db, user_id=_OTHER_USER_ID)
    for campaign in (cut_before_activation, cut_after_activation):
        _schedule_in_the_past(db, campaign)
        assert service._claim(db, campaign.id) is True
        db.refresh(campaign)
    cut_after_activation.status = CampaignStatus.ACTIVE
    db.commit()

    assert asyncio.run(service.resume_interrupted()) == 2

    for campaign in (cut_before_activation, cut_after_activation):
        assert _status(db, campaign) is CampaignStatus.ACTIVE
        assert campaign.scheduled_launch_claimed_at is None
        assert _queued_sends(db, campaign) == 2


def test_a_running_tick_only_takes_back_a_claim_that_outlived_it(
    db: Session, service: CampaignScheduledLaunchService
) -> None:
    campaign = _email_draft(db)
    _schedule_in_the_past(db, campaign)
    assert service._claim(db, campaign.id) is True
    stale_before = naive_utc_now() - timedelta(minutes=10)

    assert asyncio.run(service.resume_interrupted(claimed_before=stale_before)) == 0
    assert _queued_sends(db, campaign) == 0

    campaign.scheduled_launch_claimed_at = stale_before - timedelta(minutes=1)
    db.commit()
    assert asyncio.run(service.resume_interrupted(claimed_before=stale_before)) == 1
    assert _status(db, campaign) is CampaignStatus.ACTIVE


def test_a_refused_launch_leaves_a_draft_with_its_reason_and_notifies(
    db: Session, service: CampaignScheduledLaunchService, notified_errors: AsyncMock
) -> None:
    campaign = _email_draft(db)
    scheduled_at = naive_utc_now() + timedelta(days=1)
    service.schedule(db, campaign, scheduled_at)
    db.delete(_resend_sender(db, _USER_ID))
    _schedule_in_the_past(db, campaign)
    missed_at = campaign.scheduled_launch_at

    assert asyncio.run(service.launch_due()) == 1
    assert asyncio.run(service.launch_due()) == 0

    assert _status(db, campaign) is CampaignStatus.DRAFT
    assert campaign.started_at is None
    assert campaign.scheduled_launch_at == missed_at
    assert campaign.scheduled_launch_claimed_at is None
    assert campaign.scheduled_launch_error == "Configuration Resend manquante — Paramètres → Configuration Resend"
    assert _queued_sends(db, campaign) == 0
    notified_errors.assert_awaited_once()
    notification = notified_errors.await_args.kwargs
    assert "Derniers rappels" in notification["context"]
    assert notification["message"] == campaign.scheduled_launch_error


def test_a_launch_that_queues_nothing_goes_back_to_draft(
    db: Session, service: CampaignScheduledLaunchService, notified_errors: AsyncMock
) -> None:
    campaign = _email_draft(db)
    for prospect in campaign.prospects:
        prospect.do_not_contact = True
    _schedule_in_the_past(db, campaign)

    asyncio.run(service.launch_due())

    assert _status(db, campaign) is CampaignStatus.DRAFT
    assert campaign.started_at is None
    assert campaign.scheduled_launch_error is not None
    assert campaign.scheduled_launch_error.startswith("Aucun envoi mis en file")
    notified_errors.assert_awaited_once()


def test_a_crash_while_queueing_leaves_a_draft_and_nothing_queued(
    db: Session, service: CampaignScheduledLaunchService, monkeypatch: pytest.MonkeyPatch, notified_errors: AsyncMock
) -> None:
    campaign = _email_draft(db)
    _schedule_in_the_past(db, campaign)

    def crash(_self: CampaignQueueService, *_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("base de données injoignable")

    monkeypatch.setattr(CampaignQueueService, "enqueue_campaign", crash)

    asyncio.run(service.launch_due())

    assert _status(db, campaign) is CampaignStatus.DRAFT
    assert campaign.scheduled_launch_claimed_at is None
    assert campaign.scheduled_launch_error == "Erreur pendant le lancement : base de données injoignable"
    assert _queued_sends(db, campaign) == 0
    notified_errors.assert_awaited_once()


def test_scheduling_again_after_a_missed_launch_clears_its_reason(
    db: Session, service: CampaignScheduledLaunchService
) -> None:
    campaign = _email_draft(db)
    campaign.scheduled_launch_at = naive_utc_now() - timedelta(hours=1)
    campaign.scheduled_launch_error = "Configuration Resend manquante"
    db.commit()

    service.schedule(db, campaign, naive_utc_now() + timedelta(days=1))
    _schedule_in_the_past(db, campaign)
    asyncio.run(service.launch_due())

    assert _status(db, campaign) is CampaignStatus.ACTIVE
    assert campaign.scheduled_launch_error is None


def test_the_scheduled_time_cannot_change_while_the_loop_starts_the_campaign(
    db: Session, service: CampaignScheduledLaunchService
) -> None:
    campaign = _email_draft(db)
    _schedule_in_the_past(db, campaign)
    assert service._claim(db, campaign.id) is True
    db.refresh(campaign)

    with pytest.raises(CampaignLaunchUnderwayError):
        service.schedule(db, campaign, naive_utc_now() + timedelta(days=1))
    with pytest.raises(CampaignLaunchUnderwayError):
        service.cancel(db, campaign)


def test_a_status_change_drops_the_scheduled_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    scheduled_draft = SimpleNamespace(
        id=31,
        name="Derniers rappels",
        status=CampaignStatus.DRAFT.value,
        scheduled_launch_at=naive_utc_now() + timedelta(days=1),
        scheduled_launch_claimed_at=None,
        scheduled_launch_error=None,
    )
    monkeypatch.setattr(campaign_service, "get_campaign", lambda _db, _campaign_id, _user_id: scheduled_draft)
    monkeypatch.setattr(campaign_service_module.activity_log_service, "record", lambda **_entry: None)
    session: Any = SimpleNamespace(commit=lambda: None, refresh=lambda _campaign: None)

    campaign_service.update_campaign(session, 31, _USER_ID, CampaignUpdate(status=CampaignStatus.PAUSED.value))

    assert scheduled_draft.scheduled_launch_at is None


def _client(db: Session, user_id: int = _USER_ID) -> TestClient:
    """The campaign routes, called by a signed-in user on the test database."""
    application = FastAPI()
    application.include_router(campaigns_router)
    signed_in_user: Any = SimpleNamespace(id=user_id)
    application.dependency_overrides[get_current_user] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def test_the_campaign_page_schedules_moves_and_cancels_the_launch(db: Session) -> None:
    campaign = _email_draft(db)
    prefix = campaigns_router.prefix
    client = _client(db)
    scheduled_at = (datetime.now(UTC) + timedelta(days=2)).replace(microsecond=0)

    scheduled = client.put(f"{prefix}/{campaign.id}/scheduled-launch", json={"scheduled_at": scheduled_at.isoformat()})
    listed = client.get(prefix).json()["campaigns"][0]
    too_early = client.put(
        f"{prefix}/{campaign.id}/scheduled-launch",
        json={"scheduled_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat()},
    )
    not_theirs = _client(db, _OTHER_USER_ID).put(
        f"{prefix}/{campaign.id}/scheduled-launch", json={"scheduled_at": scheduled_at.isoformat()}
    )
    cancelled = client.delete(f"{prefix}/{campaign.id}/scheduled-launch")

    naive_utc_text = scheduled_at.replace(tzinfo=None).isoformat()
    assert scheduled.status_code == 200
    assert scheduled.json()["scheduled_launch_at"] == naive_utc_text
    assert scheduled.json()["status"] == "draft"
    assert listed["scheduled_launch_at"] == naive_utc_text
    assert too_early.status_code == 422
    assert too_early.json()["detail"] == "Choisissez une date et une heure dans le futur."
    assert not_theirs.status_code == 404
    assert cancelled.status_code == 200
    assert cancelled.json()["scheduled_launch_at"] is None


def test_launching_by_hand_replaces_the_scheduled_launch(db: Session, service: CampaignScheduledLaunchService) -> None:
    campaign = _email_draft(db)
    service.schedule(db, campaign, naive_utc_now() + timedelta(days=1))
    prefix = campaigns_router.prefix

    launched = _client(db).post(f"{prefix}/{campaign.id}/launch", json={})

    assert launched.status_code == 200
    assert launched.json()["enqueued"] == 2
    assert launched.json()["message"] == "2 email(s) mis en file — 1 toutes les 20 min"
    assert _status(db, campaign) is CampaignStatus.ACTIVE
    assert campaign.scheduled_launch_at is None
    assert asyncio.run(service.launch_due()) == 0
    assert _queued_sends(db, campaign) == 2


def test_launching_by_hand_is_refused_while_the_loop_starts_the_campaign(
    db: Session, service: CampaignScheduledLaunchService
) -> None:
    campaign = _email_draft(db)
    _schedule_in_the_past(db, campaign)
    assert service._claim(db, campaign.id) is True
    db.refresh(campaign)

    launched = _client(db).post(f"{campaigns_router.prefix}/{campaign.id}/launch", json={})

    assert launched.status_code == 409
    assert _queued_sends(db, campaign) == 0


_SCHEDULED_LAUNCH_COLUMNS = {"scheduled_launch_at", "scheduled_launch_claimed_at", "scheduled_launch_error"}


def _campaign_columns(engine: Engine) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns("campaigns")}


def test_the_migration_adds_the_scheduled_launch_to_an_existing_campaigns_table(engine: Engine, db: Session) -> None:
    campaign = _email_draft(db)
    with engine.begin() as connection:
        for column_name in _SCHEDULED_LAUNCH_COLUMNS:
            connection.execute(text(f"ALTER TABLE campaigns DROP COLUMN {column_name}"))
    assert _SCHEDULED_LAUNCH_COLUMNS.isdisjoint(_campaign_columns(engine))

    run_migration(engine)
    run_migration(engine)

    assert _campaign_columns(engine) >= _SCHEDULED_LAUNCH_COLUMNS
    db.expire_all()
    assert db.get(Campaign, campaign.id).scheduled_launch_at is None
