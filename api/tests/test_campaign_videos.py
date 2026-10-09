"""
The videos of a campaign's demo sites, read and asked from the iPad: where each one stands, and the missing ones (or all
of them) asked from the owner's PC.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import services.campaign_videos_service as campaign_videos_module
from api.v1.routes.campaigns import router as campaigns_router
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from enums.demo_video_status import DemoVideoStatus
from models.campaign import Campaign, CampaignStatus
from models.campaign_follow_up import CampaignFollowUp
from models.demo_site import DemoSite
from models.email_template import EmailTemplate
from models.presenter_video import PresenterVideo
from models.prospect_db import ProspectDB
from services import video_pipeline
from services.auth_service import get_current_user
from services.campaign_queue_service import CampaignQueueService
from services.campaign_videos_service import ALREADY_REQUESTED_REASON, CampaignVideosService
from services.demo_video_service import demo_video_service
from services.prospect_search.desktop_app_presence import DesktopAppPresence
from services.video_pipeline import DesktopVideoBuilds

_USER_ID = 7
_OTHER_USER_ID = 8
_CLIP_CHOSEN_AT = datetime(2026, 10, 9, 8, 0)


@pytest.fixture(autouse=True)
def builds(monkeypatch: pytest.MonkeyPatch) -> DesktopVideoBuilds:
    """No build under way at the start of a test."""
    fresh_builds = DesktopVideoBuilds()
    monkeypatch.setattr(video_pipeline, "desktop_video_builds", fresh_builds)
    return fresh_builds


@pytest.fixture(autouse=True)
def presence(monkeypatch: pytest.MonkeyPatch) -> DesktopAppPresence:
    """The owner's PC was never seen."""
    fresh_presence = DesktopAppPresence()
    monkeypatch.setattr(campaign_videos_module, "desktop_app_presence", fresh_presence)
    return fresh_presence


def _clip_in_use(db: Session) -> None:
    db.add(
        PresenterVideo(
            user_id=_USER_ID,
            module="websites",
            is_active=True,
            file_path="videos/presenter/websites.mp4",
            duration_seconds=30.0,
            intro_seconds=5.0,
            outro_seconds=5.0,
            in_use_since=_CLIP_CHOSEN_AT,
        )
    )
    db.commit()


def _campaign(db: Session, *, include_video: bool = True, channel: str = "email") -> Campaign:
    template = EmailTemplate(
        user_id=_USER_ID, name="Votre site en vidéo", subject="Pour vous", body_html="<p>{vignette_video}</p>"
    )
    db.add(template)
    db.flush()
    campaign = Campaign(
        user_id=_USER_ID,
        name="Vague 5",
        status=CampaignStatus.DRAFT,
        channel=channel,
        template_id=template.id,
        include_video=include_video,
    )
    db.add(campaign)
    db.commit()
    return campaign


def _site_for(
    db: Session,
    campaign: Campaign,
    name: str,
    *,
    video_status: str | None = None,
    generated_at: datetime | None = None,
    requested: bool = False,
    storyblok_space_id: int | None = 287465,
    demo_url: str | None = "https://demo.dibodev.fr/site",
) -> DemoSite:
    prospect = ProspectDB(name=name, category="plombier", source="google", confidence=2, user_id=campaign.user_id)
    db.add(prospect)
    db.flush()
    campaign.prospects.append(prospect)
    site = DemoSite(
        user_id=campaign.user_id,
        prospect_id=prospect.id,
        slug=name.lower().replace(" ", "-"),
        business_name=name,
        status=DemoSiteStatus.ACTIVE.value,
        demo_url=demo_url,
        storyblok_space_id=storyblok_space_id,
        expires_at=datetime.now(UTC) + timedelta(days=21),
        video_status=video_status,
        video_generated_at=generated_at,
        video_desktop_requested_at=datetime(2026, 10, 9, 9, 0) if requested else None,
    )
    db.add(site)
    db.commit()
    return site


def _names(listed_sites: list[Any]) -> list[str]:
    return [listed_site.business_name for listed_site in listed_sites]


def test_the_campaign_sites_are_sorted_by_where_their_video_stands(
    db: Session, builds: DesktopVideoBuilds, presence: DesktopAppPresence
) -> None:
    _clip_in_use(db)
    campaign = _campaign(db)
    _site_for(db, campaign, "Pret", video_status="ready", generated_at=_CLIP_CHOSEN_AT + timedelta(hours=1))
    _site_for(db, campaign, "Ancien clip", video_status="ready", generated_at=_CLIP_CHOSEN_AT - timedelta(hours=1))
    _site_for(db, campaign, "Attend le PC", requested=True)
    _site_for(db, campaign, "Attend Storyblok", requested=True, storyblok_space_id=None)
    built = _site_for(db, campaign, "En cours", requested=True)
    _site_for(db, campaign, "Echec", video_status="failed")
    _site_for(db, campaign, "Sans video")
    demo_video_service.mark_desktop_build_started(built)
    presence.mark_seen(_USER_ID)

    summary = CampaignVideosService.summarize(db, campaign)

    assert (summary.uses_video, summary.is_desktop_app_online) == (True, True)
    assert _names(summary.ready) == ["Pret"]
    assert _names(summary.ready_with_older_clip) == ["Ancien clip"]
    assert _names(summary.waiting_for_desktop) == ["Attend le PC"]
    assert _names(summary.waiting_for_storyblok_space) == ["Attend Storyblok"]
    assert _names(summary.building) == ["En cours"]
    assert _names(summary.failed) == ["Echec"]
    assert _names(summary.not_requested) == ["Sans video"]
    assert summary.building[0].demo_site_id == built.id


def test_a_prospect_without_an_active_demo_site_is_left_out(db: Session) -> None:
    campaign = _campaign(db)
    _site_for(db, campaign, "Actif")
    expired = _site_for(db, campaign, "Expire")
    expired.status = DemoSiteStatus.EXPIRED.value
    db.commit()

    summary = CampaignVideosService.summarize(db, campaign)

    assert _names(summary.not_requested) == ["Actif"]
    assert summary.is_desktop_app_online is False


def test_a_campaign_uses_the_video_through_its_templates_and_its_switch(db: Session) -> None:
    with_video = _campaign(db)
    switched_off = _campaign(db, include_video=False)
    without_video = _campaign(db)
    plain_template = EmailTemplate(user_id=_USER_ID, name="Démo", subject="Votre site", body_html="<p>{lien_demo}</p>")
    db.add(plain_template)
    db.flush()
    without_video.template_id = plain_template.id
    follow_up_with_video = _campaign(db)
    follow_up_with_video.template_id = plain_template.id
    db.add(CampaignFollowUp(campaign_id=follow_up_with_video.id, template_id=with_video.template_id, delay_days=5))
    sms_with_video = _campaign(db, channel="sms")
    sms_with_video.sms_template_key = "video"
    db.commit()
    db.refresh(follow_up_with_video)
    queue = CampaignQueueService(db)

    assert queue.uses_site_video(with_video) is True
    assert queue.uses_site_video(switched_off) is False
    assert queue.uses_site_video(without_video) is False
    assert queue.uses_site_video(follow_up_with_video) is True
    assert queue.uses_site_video(sms_with_video) is True


@pytest.fixture
def presenter_clip(monkeypatch: pytest.MonkeyPatch) -> None:
    """A presenter clip long enough to show a site, in use since the campaign's new clip was chosen."""
    clip = SimpleNamespace(
        duration_seconds=30.0, intro_seconds=5.0, outro_seconds=5.0, auto_generate=False, in_use_since=_CLIP_CHOSEN_AT
    )
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user", lambda *args, **kwargs: clip
    )


def test_the_missing_videos_are_asked_from_the_pc(db: Session, presenter_clip: None) -> None:
    campaign = _campaign(db)
    current = _site_for(db, campaign, "Pret", video_status="ready", generated_at=_CLIP_CHOSEN_AT + timedelta(hours=1))
    older = _site_for(
        db, campaign, "Ancien clip", video_status="ready", generated_at=_CLIP_CHOSEN_AT - timedelta(hours=1)
    )
    failed = _site_for(db, campaign, "Echec", video_status="failed")
    missing = _site_for(db, campaign, "Sans video")
    without_space = _site_for(db, campaign, "Sans espace", storyblok_space_id=None)
    waiting = _site_for(db, campaign, "Attend le PC", requested=True)
    offline = _site_for(db, campaign, "Hors ligne", demo_url=None)

    outcome = CampaignVideosService.request_videos(db, campaign, redo=False)

    assert outcome.requested_count == 4
    for asked in (older, failed, missing, without_space):
        assert asked.video_desktop_requested_at is not None
    assert current.video_desktop_requested_at is None
    assert [(skipped.business_name, skipped.reason) for skipped in outcome.skipped] == [
        ("Attend le PC", ALREADY_REQUESTED_REASON),
        ("Hors ligne", "Ce site démo n'a pas d'URL publique."),
    ]
    assert waiting.video_desktop_requested_at == datetime(2026, 10, 9, 9, 0)
    assert offline.video_desktop_requested_at is None


def test_redoing_every_video_asks_for_the_ones_made_with_the_clip_in_use_too(
    db: Session, presenter_clip: None, builds: DesktopVideoBuilds
) -> None:
    campaign = _campaign(db)
    current = _site_for(db, campaign, "Pret", video_status="ready", generated_at=_CLIP_CHOSEN_AT + timedelta(hours=1))
    built = _site_for(db, campaign, "En cours", requested=True)
    demo_video_service.mark_desktop_build_started(built)

    outcome = CampaignVideosService.request_videos(db, campaign, redo=True)

    assert outcome.requested_count == 1
    assert current.video_desktop_requested_at is not None
    assert current.video_status == DemoVideoStatus.READY.value
    assert [skipped.business_name for skipped in outcome.skipped] == ["En cours"]
    assert demo_video_service.is_desktop_build_started(built) is True


def test_no_video_is_asked_without_a_presenter_clip(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user", lambda *args, **kwargs: None
    )
    campaign = _campaign(db)
    _site_for(db, campaign, "Sans video")

    outcome = CampaignVideosService.request_videos(db, campaign, redo=False)

    assert outcome.requested_count == 0
    assert outcome.skipped[0].reason.startswith("Aucun clip de présentation")


def _client(db: Session, user_id: int = _USER_ID) -> TestClient:
    """The campaign routes, called by a signed-in user on the test database."""
    application = FastAPI()
    application.include_router(campaigns_router)
    signed_in_user: Any = SimpleNamespace(id=user_id)
    application.dependency_overrides[get_current_user] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def test_the_campaign_page_reads_and_asks_the_videos_of_its_sites(db: Session, presenter_clip: None) -> None:
    campaign = _campaign(db)
    _site_for(db, campaign, "Sans video")
    _site_for(db, campaign, "Echec", video_status="failed")
    prefix = campaigns_router.prefix
    client = _client(db)

    before = client.get(f"{prefix}/{campaign.id}/videos").json()
    asked = client.post(f"{prefix}/{campaign.id}/videos/requests", json={"redo": False}).json()
    after = client.get(f"{prefix}/{campaign.id}/videos").json()

    assert before["uses_video"] is True
    assert [site["business_name"] for site in before["not_requested"]] == ["Sans video"]
    assert asked == {"requested_count": 2, "skipped": []}
    assert [site["business_name"] for site in after["waiting_for_desktop"]] == ["Sans video", "Echec"]
    assert after["not_requested"] == []
    assert after["failed"] == []


def test_another_account_cannot_reach_the_campaign_videos(db: Session) -> None:
    campaign = _campaign(db)
    prefix = campaigns_router.prefix
    stranger = _client(db, user_id=_OTHER_USER_ID)

    assert stranger.get(f"{prefix}/{campaign.id}/videos").status_code == 404
    assert stranger.post(f"{prefix}/{campaign.id}/videos/requests", json={"redo": True}).status_code == 404
