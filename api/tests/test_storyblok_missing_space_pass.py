"""
Storyblok creates about ten spaces a day (8 Oct 2026, wave 4: 101 sites generated past the limit): the worker gives
new sites their space one at a time, the outreach that comes first served first, and pauses after a refusal.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from models.campaign import Campaign, CampaignStatus
from models.demo_site import DemoSite
from models.email_queue import EmailQueue
from models.prospect_db import ProspectDB
from services import storyblok_preswap_service as preswap_module
from services.storyblok_preswap_service import StoryblokPreswapService

USER_ID = 7
NOW = datetime(2026, 10, 9, 0, 5, tzinfo=UTC)


def _site(db: Session, slug: str, *, created_at: datetime, space_id: int | None = None, sent: bool = False) -> int:
    prospect = ProspectDB(name=slug, category="paysagiste", source="google", confidence=2, user_id=USER_ID)
    db.add(prospect)
    db.flush()
    db.add(
        DemoSite(
            user_id=USER_ID,
            prospect_id=prospect.id,
            slug=slug,
            business_name=slug,
            status="active",
            storyblok_space_id=space_id,
            demo_link_sent_at=created_at if sent else None,
            expires_at=created_at + timedelta(days=21),
            created_at=created_at,
        )
    )
    db.flush()
    return prospect.id


def _pending(db: Session, prospect_id: int, at: datetime) -> None:
    campaign = Campaign(user_id=USER_ID, name="Vague 4", status=CampaignStatus.ACTIVE.value, channel="email")
    db.add(campaign)
    db.flush()
    db.add(
        EmailQueue(
            user_id=USER_ID,
            campaign_id=campaign.id,
            prospect_id=prospect_id,
            queue_type="initial",
            follow_up_index=0,
            scheduled_at=at,
            status="pending",
        )
    )
    db.flush()


def test_the_site_whose_outreach_comes_first_gets_its_space_first(db: Session) -> None:
    today = NOW.replace(tzinfo=None)
    _site(db, "jamais-envoye", created_at=today - timedelta(hours=5))
    later = _site(db, "envoi-mardi", created_at=today - timedelta(hours=4))
    sooner = _site(db, "envoi-lundi", created_at=today - timedelta(hours=3))
    _pending(db, later, today + timedelta(days=4))
    _pending(db, sooner, today + timedelta(days=3))

    assert StoryblokPreswapService.next_site_without_space(db, NOW).slug == "envoi-lundi"


def test_without_outreach_the_oldest_new_site_never_sent_comes_first(db: Session) -> None:
    today = NOW.replace(tzinfo=None)
    _site(db, "vague-3", created_at=today - timedelta(days=18))
    _site(db, "deja-envoye", created_at=today - timedelta(hours=6), sent=True)
    _site(db, "a-deja-son-espace", created_at=today - timedelta(hours=6), space_id=42)
    _site(db, "nouveau-2", created_at=today - timedelta(hours=2))
    _site(db, "nouveau-1", created_at=today - timedelta(hours=3))

    assert StoryblokPreswapService.next_site_without_space(db, NOW).slug == "nouveau-1"


def test_a_refusal_pauses_the_pass_for_an_hour(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []

    async def refused(db: object, site: object) -> object:
        attempts.append("try")
        raise ValueError("Storyblok API error (429)")

    class _Rollback:
        def rollback(self) -> None:
            return None

    monkeypatch.setattr(
        StoryblokPreswapService, "next_site_without_space", classmethod(lambda cls, db, now: SimpleNamespace(id=1))
    )
    monkeypatch.setattr(preswap_module.demo_site_service, "provision_missing_storyblok_space", refused)
    service = StoryblokPreswapService()

    assert asyncio.run(service.run_missing_space_pass(_Rollback())) is False
    assert asyncio.run(service.run_missing_space_pass(_Rollback())) is False
    assert attempts == ["try"]
    assert service._next_missing_space_pass_at is not None
    assert service._next_missing_space_pass_at - datetime.now(UTC) > timedelta(minutes=50)
