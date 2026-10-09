"""Every prospection video waits for the owner's desktop app, which takes it, builds it and closes it: sites and receptionists alike."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import api.v1.routes.ai_assistants as ai_assistants_routes
import api.v1.routes.demo_sites as demo_sites_routes
from api.v1.routes.ai_assistants import router as ai_assistants_router
from api.v1.routes.demo_sites import router as demo_sites_router
from core.database import get_db
from enums.ai_assistant_status import AiAssistantStatus
from enums.demo_site_status import DemoSiteStatus
from enums.demo_video_status import DemoVideoStatus
from models.ai_assistant import AiAssistant
from models.demo_site import DemoSite
from services import video_pipeline
from services.ai_assistant.assistant_service import ai_assistant_service
from services.assistant_video_service import assistant_video_service
from services.auth_service import get_current_active_user
from services.demo_site_service import DemoSiteService, demo_site_service
from services.demo_site_verification_service import DemoSiteVerificationResult, demo_site_verification_service
from services.demo_video_service import demo_video_service
from services.prospect_search.desktop_app_presence import DesktopAppPresence
from services.prospection_video_desktop_relay import NO_REQUEST_MESSAGE, ProspectionVideoDesktopRelay
from services.prospection_video_service import ALREADY_BUILDING_MESSAGE
from services.r2_storage_service import r2_storage
from services.storyblok_service import StoryblokProvisionError, storyblok_service
from services.video_pipeline import DesktopVideoBuilds

_USER_ID = 1
_OTHER_USER_ID = 2
_STORYBLOK_SPACE_ID = 287465


def _presenter_clip(*, auto_generate: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        duration_seconds=30.0, intro_seconds=5.0, outro_seconds=5.0, auto_generate=auto_generate, in_use_since=None
    )


@pytest.fixture(autouse=True)
def presenter_clip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every user has a presenter clip long enough to show a site or a receptionist."""
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user",
        lambda *args, **kwargs: _presenter_clip(),
    )


@pytest.fixture(autouse=True)
def builds(monkeypatch: pytest.MonkeyPatch) -> DesktopVideoBuilds:
    """No build under way at the start of a test."""
    fresh_builds = DesktopVideoBuilds()
    monkeypatch.setattr(video_pipeline, "desktop_video_builds", fresh_builds)
    return fresh_builds


@pytest.fixture(autouse=True)
def public_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """The published videos have their public address, without a configured storage."""
    monkeypatch.setattr(r2_storage, "public_url", lambda key: f"https://cdn/{key}")


def _site(
    db: Session,
    slug: str,
    user_id: int = _USER_ID,
    video_status: str | None = None,
    storyblok_space_id: int | None = _STORYBLOK_SPACE_ID,
) -> DemoSite:
    site = DemoSite(
        user_id=user_id,
        slug=slug,
        business_name=slug.replace("-", " ").title(),
        status=DemoSiteStatus.ACTIVE.value,
        demo_url=f"https://demo.dibodev.fr/{slug}",
        storyblok_space_id=storyblok_space_id,
        expires_at=datetime.now(UTC) + timedelta(days=21),
        video_status=video_status,
    )
    db.add(site)
    db.commit()
    return site


def _assistant(db: Session, user_id: int = _USER_ID, video_status: str | None = None) -> AiAssistant:
    assistant = ai_assistant_service.create(
        db, user_id=user_id, business_name="Toitures Morel", prospect_id=None, country="FR", use_brand_color=False
    )
    assistant.video_status = video_status
    db.commit()
    return assistant


def _site_relay() -> ProspectionVideoDesktopRelay[DemoSite]:
    return ProspectionVideoDesktopRelay(demo_video_service)


def _assistant_relay() -> ProspectionVideoDesktopRelay[AiAssistant]:
    return ProspectionVideoDesktopRelay(assistant_video_service)


def test_a_request_waits_for_the_desktop_app_and_leaves_a_published_video_online(db: Session) -> None:
    relay = _site_relay()
    site = _site(db, "garage-martin", video_status=DemoVideoStatus.READY.value)

    relay.request(db, site, _USER_ID)

    assert site.video_desktop_requested_at is not None
    assert site.video_status == DemoVideoStatus.READY.value
    assert [waiting.slug for waiting in relay.waiting_subjects(db, _USER_ID)] == ["garage-martin"]
    assert demo_video_service.is_desktop_build_started(site) is False


def test_a_request_is_refused_for_a_site_that_cannot_be_filmed(db: Session) -> None:
    site = _site(db, "garage-martin")
    site.status = DemoSiteStatus.EXPIRED.value
    db.commit()

    with pytest.raises(ValueError, match="site démo actif"):
        _site_relay().request(db, site, _USER_ID)

    assert site.video_desktop_requested_at is None


def test_a_request_is_refused_without_a_presenter_clip(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user", lambda *args, **kwargs: None
    )
    site = _site(db, "garage-martin")

    with pytest.raises(ValueError):
        _site_relay().request(db, site, _USER_ID)


def test_the_desktop_app_gets_its_own_requests_oldest_first(db: Session) -> None:
    relay = _site_relay()
    first = _site(db, "premier")
    second = _site(db, "second")
    someone_else = _site(db, "autre-compte", user_id=_OTHER_USER_ID)
    deleted = _site(db, "supprime")
    for site in (second, first, someone_else, deleted):
        relay.request(db, site, site.user_id)
    first.video_desktop_requested_at = datetime(2026, 10, 5, 8, 0)
    second.video_desktop_requested_at = datetime(2026, 10, 5, 9, 0)
    deleted.status = DemoSiteStatus.DELETED.value
    db.commit()

    assert [site.slug for site in relay.waiting_subjects(db, _USER_ID)] == ["premier", "second"]


def test_a_site_without_its_storyblok_space_waits_then_is_handed_over_once_it_has_one(db: Session) -> None:
    relay = _site_relay()
    site = _site(db, "jardins-exemple", storyblok_space_id=None)

    relay.request(db, site, _USER_ID)

    assert site.video_desktop_requested_at is not None
    assert demo_video_service.is_waiting_for_storyblok_space(site) is True
    assert relay.waiting_subjects(db, _USER_ID) == []

    site.storyblok_space_id = _STORYBLOK_SPACE_ID
    db.commit()

    assert demo_video_service.is_waiting_for_storyblok_space(site) is False
    assert [waiting.slug for waiting in relay.waiting_subjects(db, _USER_ID)] == ["jardins-exemple"]


def test_a_claimed_request_is_not_offered_again_while_the_build_runs(db: Session) -> None:
    relay = _site_relay()
    site = _site(db, "garage-martin")
    relay.request(db, site, _USER_ID)

    relay.claim(site)

    assert demo_video_service.is_desktop_build_started(site) is True
    assert relay.waiting_subjects(db, _USER_ID) == []
    with pytest.raises(ValueError, match=ALREADY_BUILDING_MESSAGE):
        relay.claim(site)


def test_a_request_is_refused_while_the_desktop_app_builds(db: Session) -> None:
    relay = _site_relay()
    site = _site(db, "garage-martin")
    relay.request(db, site, _USER_ID)
    relay.claim(site)

    with pytest.raises(ValueError, match=ALREADY_BUILDING_MESSAGE):
        relay.request(db, site, _USER_ID)

    assert demo_video_service.is_desktop_build_started(site) is True


def test_a_claim_needs_a_request(db: Session) -> None:
    site = _site(db, "garage-martin")

    with pytest.raises(ValueError, match=NO_REQUEST_MESSAGE):
        _site_relay().claim(site)


def test_a_build_abandoned_by_a_closed_desktop_app_is_offered_again(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        video_pipeline, "desktop_video_builds", DesktopVideoBuilds(build_lifetime=timedelta(seconds=-1))
    )
    relay = _site_relay()
    site = _site(db, "garage-martin")
    relay.request(db, site, _USER_ID)

    relay.claim(site)

    assert demo_video_service.is_desktop_build_started(site) is False
    assert [waiting.slug for waiting in relay.waiting_subjects(db, _USER_ID)] == ["garage-martin"]


def test_a_new_request_forgets_the_previous_build(db: Session) -> None:
    relay = _site_relay()
    site = _site(db, "garage-martin")
    relay.request(db, site, _USER_ID)
    relay.claim(site)

    relay.clear_request(db, site)
    relay.request(db, site, _USER_ID)

    assert demo_video_service.is_desktop_build_started(site) is False


def test_a_failure_marks_the_video_failed_with_its_reason(db: Session) -> None:
    relay = _site_relay()
    site = _site(db, "garage-martin")
    relay.request(db, site, _USER_ID)
    relay.claim(site)

    relay.record_failure(db, site, "Storyblok est déconnecté sur l'ordinateur.")

    assert site.video_status == DemoVideoStatus.FAILED.value
    assert site.video_error == "Storyblok est déconnecté sur l'ordinateur."
    assert site.video_desktop_requested_at is None
    assert demo_video_service.is_desktop_build_started(site) is False


def test_a_failed_regeneration_keeps_the_published_video(db: Session) -> None:
    relay = _site_relay()
    site = _site(db, "garage-martin", video_status=DemoVideoStatus.READY.value)
    relay.request(db, site, _USER_ID)

    relay.record_failure(db, site, "x" * 1500)

    assert site.video_status == DemoVideoStatus.READY.value
    assert site.video_error == "x" * 1000
    assert site.video_desktop_requested_at is None


def test_a_failure_needs_a_request(db: Session) -> None:
    site = _site(db, "garage-martin")

    with pytest.raises(ValueError, match=NO_REQUEST_MESSAGE):
        _site_relay().record_failure(db, site, "Échec")


def test_the_builds_of_a_site_and_a_receptionist_with_the_same_id_stay_apart(db: Session) -> None:
    site = _site(db, "garage-martin")
    assistant = _assistant(db)
    assert assistant.id == site.id
    _site_relay().request(db, site, _USER_ID)
    _assistant_relay().request(db, assistant, _USER_ID)

    _site_relay().claim(site)

    assert demo_video_service.is_desktop_build_started(site) is True
    assert assistant_video_service.is_desktop_build_started(assistant) is False


def test_a_receptionist_request_waits_then_the_desktop_app_takes_and_fails_it(db: Session) -> None:
    relay = _assistant_relay()
    assistant = _assistant(db, video_status=DemoVideoStatus.READY.value)

    relay.request(db, assistant, _USER_ID)
    waiting = relay.waiting_subjects(db, _USER_ID)
    relay.claim(assistant)
    waiting_while_built = relay.waiting_subjects(db, _USER_ID)
    relay.record_failure(db, assistant, "Le widget ne s'est pas ouvert.")

    assert [subject.id for subject in waiting] == [assistant.id]
    assert waiting_while_built == []
    assert (assistant.video_status, assistant.video_error) == (
        DemoVideoStatus.READY.value,
        "Le widget ne s'est pas ouvert.",
    )
    assert assistant.video_desktop_requested_at is None


def test_an_inactive_receptionist_is_neither_asked_nor_handed_over(db: Session) -> None:
    relay = _assistant_relay()
    assistant = _assistant(db)
    relay.request(db, assistant, _USER_ID)

    assistant.status = AiAssistantStatus.EXPIRED.value
    db.commit()

    assert relay.waiting_subjects(db, _USER_ID) == []
    with pytest.raises(ValueError, match="réceptionniste active"):
        relay.request(db, assistant, _USER_ID)


def test_a_new_site_asks_the_pc_for_its_video_when_its_clip_generates_on_its_own(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user",
        lambda *args, **kwargs: _presenter_clip(auto_generate=True),
    )
    site = _site(db, "garage-martin")

    assert _site_relay().request_if_auto_generating(db, site, _USER_ID) is True
    assert site.video_desktop_requested_at is not None


def test_no_request_is_left_when_the_clip_does_not_generate_on_its_own_or_is_missing(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = _site(db, "garage-martin")
    assistant = _assistant(db)

    assert _site_relay().request_if_auto_generating(db, site, _USER_ID) is False
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user", lambda *args, **kwargs: None
    )
    assert _assistant_relay().request_if_auto_generating(db, assistant, _USER_ID) is False
    assert (site.video_desktop_requested_at, assistant.video_desktop_requested_at) == (None, None)


def test_a_video_that_cannot_be_asked_never_fails_the_creation(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user",
        lambda *args, **kwargs: _presenter_clip(auto_generate=True),
    )
    site = _site(db, "garage-martin")
    site.demo_url = None
    db.commit()

    assert _site_relay().request_if_auto_generating(db, site, _USER_ID) is False
    assert site.video_desktop_requested_at is None


def test_a_site_created_without_its_storyblok_space_still_asks_the_pc_for_its_video(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Storyblok's daily limit leaves a new site without its space: its video request waits for the space."""
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user",
        lambda *args, **kwargs: _presenter_clip(auto_generate=True),
    )

    async def daily_limit_reached(**kwargs: Any) -> None:
        raise StoryblokProvisionError("Storyblok API error (429)")

    async def online(db: Session, site: DemoSite) -> DemoSiteVerificationResult:
        return DemoSiteVerificationResult(
            public_api_ok=True, demo_url_live=True, local_demo_url=None, local_demo_url_live=False, message="En ligne"
        )

    monkeypatch.setattr(storyblok_service, "provision_space", daily_limit_reached)
    monkeypatch.setattr(demo_site_verification_service, "verify", online)
    monkeypatch.setattr(DemoSiteService, "_log_generation", lambda *args, **kwargs: None)

    site = asyncio.run(
        demo_site_service.create_demo_site(
            db,
            user=SimpleNamespace(id=_USER_ID),
            business_name="Jardins Exemple",
            template_id="plumber-signature",
            phone=None,
            email=None,
            city=None,
            description=None,
        )
    )

    assert (site.status, site.storyblok_space_id) == (DemoSiteStatus.ACTIVE.value, None)
    assert site.video_desktop_requested_at is not None
    assert _site_relay().waiting_subjects(db, _USER_ID) == []


def test_a_new_receptionist_asks_the_pc_for_its_video_when_its_clip_generates_on_its_own(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user",
        lambda *args, **kwargs: _presenter_clip(auto_generate=True),
    )

    assistant = _assistant(db)

    assert assistant.video_desktop_requested_at is not None
    assert [subject.id for subject in _assistant_relay().waiting_subjects(db, _USER_ID)] == [assistant.id]


def _client(db: Session, router: Any, user_id: int = _USER_ID) -> TestClient:
    """The given routes, called by a signed-in user on the test database."""
    application = FastAPI()
    application.include_router(router)
    signed_in_user: Any = SimpleNamespace(id=user_id)
    application.dependency_overrides[get_current_active_user] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


@pytest.fixture
def presence(monkeypatch: pytest.MonkeyPatch) -> DesktopAppPresence:
    """A fresh desktop presence behind the site and receptionist routes."""
    fresh_presence = DesktopAppPresence()
    monkeypatch.setattr(demo_sites_routes, "desktop_app_presence", fresh_presence)
    monkeypatch.setattr(ai_assistants_routes, "desktop_app_presence", fresh_presence)
    return fresh_presence


def test_a_tablet_asks_and_the_desktop_app_takes_the_request(db: Session, presence: DesktopAppPresence) -> None:
    site = _site(db, "garage-martin")
    prefix = demo_sites_router.prefix
    client = _client(db, demo_sites_router)

    asked = client.post(f"{prefix}/{site.id}/video/desktop-request")
    waiting = client.get(f"{prefix}/video/desktop-requests")
    claimed = client.post(f"{prefix}/{site.id}/video/desktop-claim")
    claimed_twice = client.post(f"{prefix}/{site.id}/video/desktop-claim")

    assert asked.status_code == 202
    assert asked.json()["video_desktop_requested_at"] is not None
    assert asked.json()["is_video_desktop_build_started"] is False
    assert [request["slug"] for request in waiting.json()] == ["garage-martin"]
    assert presence.is_online(_USER_ID) is True
    assert claimed.status_code == 200
    assert claimed.json()["is_video_desktop_build_started"] is True
    assert claimed_twice.status_code == 409
    assert client.get(f"{prefix}/video/desktop-requests").json() == []


def test_the_server_renders_no_video_any_more(db: Session) -> None:
    site = _site(db, "garage-martin")
    prefix = demo_sites_router.prefix
    client = _client(db, demo_sites_router)

    assert client.post(f"{prefix}/{site.id}/video").status_code == 405
    assert client.post(f"{prefix}/{site.id}/video-background").status_code == 404


def test_a_tablet_withdraws_its_request(db: Session, presence: DesktopAppPresence) -> None:
    site = _site(db, "garage-martin", video_status=DemoVideoStatus.READY.value)
    prefix = demo_sites_router.prefix
    client = _client(db, demo_sites_router)
    client.post(f"{prefix}/{site.id}/video/desktop-request")

    withdrawn = client.delete(f"{prefix}/{site.id}/video/desktop-request")

    assert withdrawn.status_code == 200
    assert withdrawn.json()["video_desktop_requested_at"] is None
    assert withdrawn.json()["video_status"] == DemoVideoStatus.READY.value
    assert client.get(f"{prefix}/video/desktop-requests").json() == []


def test_a_video_the_desktop_app_builds_cannot_be_withdrawn_asked_again_or_deleted(
    db: Session, presence: DesktopAppPresence
) -> None:
    site = _site(db, "garage-martin", video_status=DemoVideoStatus.READY.value)
    prefix = demo_sites_router.prefix
    client = _client(db, demo_sites_router)
    client.post(f"{prefix}/{site.id}/video/desktop-request")
    client.post(f"{prefix}/{site.id}/video/desktop-claim")

    withdrawn = client.delete(f"{prefix}/{site.id}/video/desktop-request")
    asked_again = client.post(f"{prefix}/{site.id}/video/desktop-request")
    deleted = client.delete(f"{prefix}/{site.id}/video")

    assert [withdrawn.status_code, asked_again.status_code, deleted.status_code] == [409, 400, 409]
    assert withdrawn.json()["detail"] == ALREADY_BUILDING_MESSAGE
    assert asked_again.json()["detail"] == ALREADY_BUILDING_MESSAGE
    assert site.video_desktop_requested_at is not None
    assert site.video_status == DemoVideoStatus.READY.value


def test_the_dashboard_follows_the_video_while_it_waits_then_while_it_is_built(
    db: Session, presence: DesktopAppPresence
) -> None:
    site = _site(db, "garage-martin")
    prefix = demo_sites_router.prefix
    client = _client(db, demo_sites_router)

    before = client.get(f"{prefix}/{site.id}/video/state").json()
    client.post(f"{prefix}/{site.id}/video/desktop-request")
    waiting = client.get(f"{prefix}/{site.id}/video/state").json()
    client.post(f"{prefix}/{site.id}/video/desktop-claim")
    building = client.get(f"{prefix}/{site.id}/video/state").json()

    assert before["video_desktop_requested_at"] is None
    assert waiting["video_desktop_requested_at"] is not None
    assert waiting["is_video_desktop_build_started"] is False
    assert waiting["is_video_waiting_for_storyblok_space"] is False
    assert building["is_video_desktop_build_started"] is True
    assert building["video_page_url"] is None
    assert (
        _client(db, demo_sites_router, user_id=_OTHER_USER_ID).get(f"{prefix}/{site.id}/video/state").status_code == 404
    )


def test_the_site_page_tells_a_request_waits_for_the_storyblok_space(db: Session, presence: DesktopAppPresence) -> None:
    site = _site(db, "jardins-exemple", storyblok_space_id=None)
    prefix = demo_sites_router.prefix
    client = _client(db, demo_sites_router)

    asked = client.post(f"{prefix}/{site.id}/video/desktop-request").json()
    state = client.get(f"{prefix}/{site.id}/video/state").json()

    assert asked["is_video_waiting_for_storyblok_space"] is True
    assert state["is_video_waiting_for_storyblok_space"] is True
    assert client.get(f"{prefix}/video/desktop-requests").json() == []


def test_the_desktop_app_reports_why_it_gave_up(db: Session, presence: DesktopAppPresence) -> None:
    site = _site(db, "garage-martin")
    prefix = demo_sites_router.prefix
    client = _client(db, demo_sites_router)
    client.post(f"{prefix}/{site.id}/video/desktop-request")
    client.post(f"{prefix}/{site.id}/video/desktop-claim")

    failed = client.post(f"{prefix}/{site.id}/video/desktop-failure", json={"message": "Storyblok est déconnecté."})
    failed_again = client.post(f"{prefix}/{site.id}/video/desktop-failure", json={"message": "Encore"})

    assert failed.status_code == 200
    assert failed.json()["video_status"] == DemoVideoStatus.FAILED.value
    assert failed.json()["video_error"] == "Storyblok est déconnecté."
    assert failed_again.status_code == 409


def test_another_account_cannot_reach_the_request(db: Session, presence: DesktopAppPresence) -> None:
    site = _site(db, "garage-martin")
    prefix = demo_sites_router.prefix
    _client(db, demo_sites_router).post(f"{prefix}/{site.id}/video/desktop-request")
    stranger = _client(db, demo_sites_router, user_id=_OTHER_USER_ID)

    assert stranger.get(f"{prefix}/video/desktop-requests").json() == []
    assert stranger.post(f"{prefix}/{site.id}/video/desktop-claim").status_code == 404


def test_a_receptionist_video_goes_through_the_same_relay_routes(db: Session, presence: DesktopAppPresence) -> None:
    assistant = _assistant(db)
    prefix = ai_assistants_router.prefix
    client = _client(db, ai_assistants_router)

    asked = client.post(f"{prefix}/{assistant.id}/video/desktop-request")
    waiting = client.get(f"{prefix}/video/desktop-requests")
    claimed = client.post(f"{prefix}/{assistant.id}/video/desktop-claim")
    building = client.get(f"{prefix}/{assistant.id}/video/state")
    failed = client.post(
        f"{prefix}/{assistant.id}/video/desktop-failure", json={"message": "Le widget ne s'est pas ouvert."}
    )

    assert asked.status_code == 202
    assert asked.json()["video_desktop_requested_at"] is not None
    assert [request["assistant_id"] for request in waiting.json()] == [assistant.id]
    assert presence.is_online(_USER_ID) is True
    assert claimed.json()["is_video_desktop_build_started"] is True
    assert building.json()["is_video_desktop_build_started"] is True
    assert failed.json()["video_status"] == DemoVideoStatus.FAILED.value
    assert failed.json()["video_error"] == "Le widget ne s'est pas ouvert."
    assert client.post(f"{prefix}/{assistant.id}/video").status_code == 405


def test_a_receptionist_request_is_withdrawn_but_never_while_it_is_built(
    db: Session, presence: DesktopAppPresence
) -> None:
    withdrawn_assistant = _assistant(db)
    built_assistant = _assistant(db)
    prefix = ai_assistants_router.prefix
    client = _client(db, ai_assistants_router)
    client.post(f"{prefix}/{withdrawn_assistant.id}/video/desktop-request")
    client.post(f"{prefix}/{built_assistant.id}/video/desktop-request")
    client.post(f"{prefix}/{built_assistant.id}/video/desktop-claim")

    withdrawn = client.delete(f"{prefix}/{withdrawn_assistant.id}/video/desktop-request")
    refused = client.delete(f"{prefix}/{built_assistant.id}/video/desktop-request")
    deleted = client.delete(f"{prefix}/{built_assistant.id}/video")

    assert withdrawn.status_code == 200
    assert withdrawn.json()["video_desktop_requested_at"] is None
    assert [refused.status_code, deleted.status_code] == [409, 409]
    assert (
        _client(db, ai_assistants_router, user_id=_OTHER_USER_ID)
        .get(f"{prefix}/{built_assistant.id}/video/state")
        .status_code
        == 404
    )
