"""A prospection video asked from a tablet waits for the owner's desktop app, which takes it, builds it and closes it."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import api.v1.routes.demo_sites as demo_sites_routes
from api.v1.routes.demo_sites import router as demo_sites_router
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from enums.demo_video_status import DemoVideoStatus
from models.demo_site import DemoSite
from services.auth_service import get_current_active_user
from services.demo_video_desktop_relay import (
    ALREADY_BUILDING_MESSAGE,
    NO_REQUEST_MESSAGE,
    DemoVideoDesktopRelay,
)
from services.prospect_search.desktop_app_presence import DesktopAppPresence

_USER_ID = 1
_OTHER_USER_ID = 2


@pytest.fixture(autouse=True)
def presenter_clip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every user has a presenter clip long enough to show a site."""
    clip = SimpleNamespace(duration_seconds=30.0, intro_seconds=5.0, outro_seconds=5.0, auto_generate=False)
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user",
        lambda *args, **kwargs: clip,
    )


def _site(db: Session, slug: str, user_id: int = _USER_ID, video_status: str | None = None) -> DemoSite:
    site = DemoSite(
        user_id=user_id,
        slug=slug,
        business_name=slug.replace("-", " ").title(),
        status=DemoSiteStatus.ACTIVE.value,
        demo_url=f"https://demo.dibodev.fr/{slug}",
        expires_at=datetime.now(UTC) + timedelta(days=21),
        video_status=video_status,
    )
    db.add(site)
    db.commit()
    return site


def test_a_request_waits_for_the_desktop_app_and_leaves_a_published_video_online(db: Session) -> None:
    relay = DemoVideoDesktopRelay()
    site = _site(db, "garage-martin", video_status=DemoVideoStatus.READY.value)

    relay.request(db, site, _USER_ID)

    assert site.video_desktop_requested_at is not None
    assert site.video_status == DemoVideoStatus.READY.value
    assert [waiting.slug for waiting in relay.waiting_sites(db, _USER_ID)] == ["garage-martin"]
    assert relay.is_build_started(site) is False


def test_a_request_is_refused_while_the_server_generates_the_video(db: Session) -> None:
    relay = DemoVideoDesktopRelay()
    site = _site(db, "garage-martin", video_status=DemoVideoStatus.PENDING.value)

    with pytest.raises(ValueError):
        relay.request(db, site, _USER_ID)

    assert site.video_desktop_requested_at is None


def test_a_request_is_refused_without_a_presenter_clip(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user", lambda *args, **kwargs: None
    )
    site = _site(db, "garage-martin")

    with pytest.raises(ValueError):
        DemoVideoDesktopRelay().request(db, site, _USER_ID)


def test_the_desktop_app_gets_its_own_requests_oldest_first(db: Session) -> None:
    relay = DemoVideoDesktopRelay()
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

    assert [site.slug for site in relay.waiting_sites(db, _USER_ID)] == ["premier", "second"]


def test_a_claimed_request_is_not_offered_again_while_the_build_runs(db: Session) -> None:
    relay = DemoVideoDesktopRelay()
    site = _site(db, "garage-martin")
    relay.request(db, site, _USER_ID)

    relay.claim(site)

    assert relay.is_build_started(site) is True
    assert relay.waiting_sites(db, _USER_ID) == []
    with pytest.raises(ValueError, match=ALREADY_BUILDING_MESSAGE):
        relay.claim(site)


def test_a_request_is_refused_while_the_desktop_app_builds(db: Session) -> None:
    relay = DemoVideoDesktopRelay()
    site = _site(db, "garage-martin")
    relay.request(db, site, _USER_ID)
    relay.claim(site)

    with pytest.raises(ValueError, match=ALREADY_BUILDING_MESSAGE):
        relay.request(db, site, _USER_ID)

    assert relay.is_build_started(site) is True


def test_a_claim_needs_a_request(db: Session) -> None:
    site = _site(db, "garage-martin")

    with pytest.raises(ValueError, match=NO_REQUEST_MESSAGE):
        DemoVideoDesktopRelay().claim(site)


def test_a_build_abandoned_by_a_closed_desktop_app_is_offered_again(db: Session) -> None:
    relay = DemoVideoDesktopRelay(claim_lifetime=timedelta(seconds=-1))
    site = _site(db, "garage-martin")
    relay.request(db, site, _USER_ID)

    relay.claim(site)

    assert relay.is_build_started(site) is False
    assert [waiting.slug for waiting in relay.waiting_sites(db, _USER_ID)] == ["garage-martin"]


def test_a_new_request_forgets_the_previous_build(db: Session) -> None:
    relay = DemoVideoDesktopRelay()
    site = _site(db, "garage-martin")
    relay.request(db, site, _USER_ID)
    relay.claim(site)

    relay.clear_request(db, site)
    relay.request(db, site, _USER_ID)

    assert relay.is_build_started(site) is False


def test_a_failure_marks_the_video_failed_with_its_reason(db: Session) -> None:
    relay = DemoVideoDesktopRelay()
    site = _site(db, "garage-martin")
    relay.request(db, site, _USER_ID)
    relay.claim(site)

    relay.record_failure(db, site, "Storyblok est déconnecté sur l'ordinateur.")

    assert site.video_status == DemoVideoStatus.FAILED.value
    assert site.video_error == "Storyblok est déconnecté sur l'ordinateur."
    assert site.video_desktop_requested_at is None
    assert relay.is_build_started(site) is False


def test_a_failed_regeneration_keeps_the_published_video(db: Session) -> None:
    relay = DemoVideoDesktopRelay()
    site = _site(db, "garage-martin", video_status=DemoVideoStatus.READY.value)
    relay.request(db, site, _USER_ID)

    relay.record_failure(db, site, "x" * 1500)

    assert site.video_status == DemoVideoStatus.READY.value
    assert site.video_error == "x" * 1000
    assert site.video_desktop_requested_at is None


def test_a_failure_needs_a_request(db: Session) -> None:
    site = _site(db, "garage-martin")

    with pytest.raises(ValueError, match=NO_REQUEST_MESSAGE):
        DemoVideoDesktopRelay().record_failure(db, site, "Échec")


def _client(db: Session, user_id: int = _USER_ID) -> TestClient:
    """The demo site routes, called by a signed-in user on the test database."""
    application = FastAPI()
    application.include_router(demo_sites_router)
    signed_in_user: Any = SimpleNamespace(id=user_id)
    application.dependency_overrides[get_current_active_user] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


@pytest.fixture
def relay_routes(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """The routes on a fresh relay and a fresh desktop presence."""
    relay = DemoVideoDesktopRelay()
    presence = DesktopAppPresence()
    monkeypatch.setattr(demo_sites_routes, "demo_video_desktop_relay", relay)
    monkeypatch.setattr(demo_sites_routes, "desktop_app_presence", presence)
    return SimpleNamespace(relay=relay, presence=presence)


def test_a_tablet_asks_and_the_desktop_app_takes_the_request(db: Session, relay_routes: SimpleNamespace) -> None:
    site = _site(db, "garage-martin")
    prefix = _router_prefix()
    client = _client(db)

    asked = client.post(f"{prefix}/{site.id}/video/desktop-request")
    waiting = client.get(f"{prefix}/video/desktop-requests")
    claimed = client.post(f"{prefix}/{site.id}/video/desktop-claim")
    claimed_twice = client.post(f"{prefix}/{site.id}/video/desktop-claim")

    assert asked.status_code == 202
    assert asked.json()["video_desktop_requested_at"] is not None
    assert asked.json()["is_video_desktop_build_started"] is False
    assert [request["slug"] for request in waiting.json()] == ["garage-martin"]
    assert relay_routes.presence.is_online(_USER_ID) is True
    assert claimed.status_code == 200
    assert claimed.json()["is_video_desktop_build_started"] is True
    assert claimed_twice.status_code == 409
    assert client.get(f"{prefix}/video/desktop-requests").json() == []


def test_a_tablet_withdraws_its_request(db: Session, relay_routes: SimpleNamespace) -> None:
    site = _site(db, "garage-martin", video_status=DemoVideoStatus.READY.value)
    prefix = _router_prefix()
    client = _client(db)
    client.post(f"{prefix}/{site.id}/video/desktop-request")

    withdrawn = client.delete(f"{prefix}/{site.id}/video/desktop-request")

    assert withdrawn.status_code == 200
    assert withdrawn.json()["video_desktop_requested_at"] is None
    assert withdrawn.json()["video_status"] == DemoVideoStatus.READY.value
    assert client.get(f"{prefix}/video/desktop-requests").json() == []


def test_a_video_the_desktop_app_builds_cannot_be_withdrawn_replaced_or_deleted(
    db: Session, relay_routes: SimpleNamespace
) -> None:
    site = _site(db, "garage-martin", video_status=DemoVideoStatus.READY.value)
    prefix = _router_prefix()
    client = _client(db)
    client.post(f"{prefix}/{site.id}/video/desktop-request")
    client.post(f"{prefix}/{site.id}/video/desktop-claim")

    withdrawn = client.delete(f"{prefix}/{site.id}/video/desktop-request")
    replaced = client.post(f"{prefix}/{site.id}/video")
    deleted = client.delete(f"{prefix}/{site.id}/video")

    assert [withdrawn.status_code, replaced.status_code, deleted.status_code] == [409, 409, 409]
    assert withdrawn.json()["detail"] == ALREADY_BUILDING_MESSAGE
    assert site.video_desktop_requested_at is not None
    assert site.video_status == DemoVideoStatus.READY.value


def test_the_dashboard_follows_the_video_while_it_waits_then_while_it_is_built(
    db: Session, relay_routes: SimpleNamespace
) -> None:
    site = _site(db, "garage-martin")
    prefix = _router_prefix()
    client = _client(db)

    before = client.get(f"{prefix}/{site.id}/video/state").json()
    client.post(f"{prefix}/{site.id}/video/desktop-request")
    waiting = client.get(f"{prefix}/{site.id}/video/state").json()
    client.post(f"{prefix}/{site.id}/video/desktop-claim")
    building = client.get(f"{prefix}/{site.id}/video/state").json()

    assert before["video_desktop_requested_at"] is None
    assert waiting["video_desktop_requested_at"] is not None
    assert waiting["is_video_desktop_build_started"] is False
    assert building["is_video_desktop_build_started"] is True
    assert building["video_page_url"] is None
    assert _client(db, user_id=_OTHER_USER_ID).get(f"{prefix}/{site.id}/video/state").status_code == 404


def test_the_desktop_app_reports_why_it_gave_up(db: Session, relay_routes: SimpleNamespace) -> None:
    site = _site(db, "garage-martin")
    prefix = _router_prefix()
    client = _client(db)
    client.post(f"{prefix}/{site.id}/video/desktop-request")
    client.post(f"{prefix}/{site.id}/video/desktop-claim")

    failed = client.post(f"{prefix}/{site.id}/video/desktop-failure", json={"message": "Storyblok est déconnecté."})
    failed_again = client.post(f"{prefix}/{site.id}/video/desktop-failure", json={"message": "Encore"})

    assert failed.status_code == 200
    assert failed.json()["video_status"] == DemoVideoStatus.FAILED.value
    assert failed.json()["video_error"] == "Storyblok est déconnecté."
    assert failed_again.status_code == 409


def test_another_account_cannot_reach_the_request(db: Session, relay_routes: SimpleNamespace) -> None:
    site = _site(db, "garage-martin")
    prefix = _router_prefix()
    _client(db).post(f"{prefix}/{site.id}/video/desktop-request")
    stranger = _client(db, user_id=_OTHER_USER_ID)

    assert stranger.get(f"{prefix}/video/desktop-requests").json() == []
    assert stranger.post(f"{prefix}/{site.id}/video/desktop-claim").status_code == 404


def _router_prefix() -> str:
    return demo_sites_router.prefix
