"""
An address that bounced on every try is never written to again: the dispatch skips it, a new bounce holds back
the prospect's pending emails at once, and the rows planned before that change are held back by a migration.
The prospect's SMS sends are left alone, since the phone may still reach him.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import services.campaign_queue_service as cqs
from migrations.hold_back_undeliverable_pending_emails import SKIP_REASON, run_migration
from models.campaign import Campaign
from models.email_queue import EmailQueue
from models.prospect_db import ProspectDB
from services.bounce_fallback_service import BounceFallbackService
from services.campaign_queue_service import CampaignQueueService

_USER_ID = 7
_IN_THREE_DAYS: datetime = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=3)


class _FakeDB:
    """Counts commits, the only database call left on the paths under test."""

    def __init__(self) -> None:
        self.commits = 0

    def add(self, _row: object) -> None:
        return None

    def commit(self) -> None:
        self.commits += 1


def _prospect(db: Session, name: str, *, undeliverable: bool) -> ProspectDB:
    prospect = ProspectDB(
        user_id=_USER_ID,
        name=name,
        category="Garage",
        source="google_maps",
        email=f"{name.lower()}@example.com",
        email_undeliverable=undeliverable,
    )
    db.add(prospect)
    db.flush()
    return prospect


def _campaign(db: Session, channel: str) -> Campaign:
    campaign = Campaign(user_id=_USER_ID, name=f"Vague 4 {channel}", channel=channel)
    db.add(campaign)
    db.flush()
    return campaign


def _queued(db: Session, campaign: Campaign, prospect: ProspectDB, queue_type: str, status: str) -> EmailQueue:
    item = EmailQueue(
        user_id=_USER_ID,
        campaign_id=campaign.id,
        prospect_id=prospect.id,
        queue_type=queue_type,
        scheduled_at=_IN_THREE_DAYS,
        status=status,
    )
    db.add(item)
    db.flush()
    return item


def test_the_dispatch_skips_a_prospect_whose_every_address_bounced(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cqs.unsubscribe_service, "is_unsubscribed", lambda _db, _email: False)
    prospect = SimpleNamespace(
        id=299,
        name="Les Jardins d'Amalur",
        email="amalur@example.com",
        do_not_contact=False,
        is_dismissed=False,
        email_undeliverable=True,
    )
    item = SimpleNamespace(
        id=416,
        prospect=prospect,
        campaign=SimpleNamespace(channel="email"),
        template=None,
        status="sending",
        skip_reason=None,
    )
    db = _FakeDB()

    asyncio.run(CampaignQueueService(db)._dispatch(item))

    assert item.status == "skipped"
    assert item.skip_reason == "Adresse en échec (rebond)"
    assert db.commits == 1


def test_holding_back_skips_the_pending_emails_and_leaves_the_sms_and_the_sent(db: Session) -> None:
    prospect = _prospect(db, "Mousse", undeliverable=True)
    email_campaign = _campaign(db, "email")
    sms_campaign = _campaign(db, "sms")
    sent = _queued(db, email_campaign, prospect, "initial", "sent")
    follow_up = _queued(db, email_campaign, prospect, "followup", "pending")
    sms = _queued(db, sms_campaign, prospect, "initial", "pending")
    db.commit()

    held_back = CampaignQueueService(db).skip_pending_emails_for_prospect(prospect.id)

    assert held_back == 1
    assert (follow_up.status, follow_up.skip_reason) == ("skipped", "Adresse en échec (rebond)")
    assert sent.status == "sent"
    assert sms.status == "pending"


def test_flagging_a_dead_address_holds_back_its_pending_emails(monkeypatch: pytest.MonkeyPatch) -> None:
    held_back: list[int] = []
    monkeypatch.setattr(
        CampaignQueueService,
        "skip_pending_emails_for_prospect",
        lambda _self, prospect_id: held_back.append(prospect_id),
    )
    prospect = SimpleNamespace(id=305, email_undeliverable=False)

    BounceFallbackService._mark_undeliverable(_FakeDB(), prospect, "hard bounce")

    assert prospect.email_undeliverable is True
    assert held_back == [305]


def test_an_address_already_flagged_is_not_held_back_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    held_back: list[int] = []
    monkeypatch.setattr(
        CampaignQueueService,
        "skip_pending_emails_for_prospect",
        lambda _self, prospect_id: held_back.append(prospect_id),
    )

    BounceFallbackService._mark_undeliverable(
        _FakeDB(), SimpleNamespace(id=121, email_undeliverable=True), "hard bounce"
    )

    assert held_back == []


def test_the_migration_holds_back_the_emails_planned_before_the_guard(engine: Engine, db: Session) -> None:
    dead = _prospect(db, "Amalur", undeliverable=True)
    alive = _prospect(db, "AutoCinq", undeliverable=False)
    email_campaign = _campaign(db, "email")
    sms_campaign = _campaign(db, "sms")
    dead_follow_up = _queued(db, email_campaign, dead, "followup", "pending")
    dead_sms = _queued(db, sms_campaign, dead, "initial", "pending")
    alive_follow_up = _queued(db, email_campaign, alive, "followup", "pending")
    db.commit()

    run_migration(engine)
    db.expire_all()

    held = db.get(EmailQueue, dead_follow_up.id)
    assert held is not None
    assert (held.status, held.skip_reason) == ("skipped", SKIP_REASON)
    assert db.get(EmailQueue, dead_sms.id).status == "pending"
    assert db.get(EmailQueue, alive_follow_up.id).status == "pending"
