"""
Tests for the desktop app presence — the iPad learns whether the PC is on to read the Facebook pages.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import api.v1.routes.prospect_searches as prospect_searches_routes
import services.prospect_search.desktop_app_presence as presence_module
from api.v1.routes.prospect_searches import router as prospect_searches_router
from core.database import get_db
from services.auth_service import require_auth
from services.prospect_search.desktop_app_presence import DesktopAppPresence

USER_ID = 7
OTHER_USER_ID = 8


class _Clock:
    """A clock the test moves forward by hand."""

    def __init__(self) -> None:
        self.now = datetime(2026, 10, 5, 9, 0, 0)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    """Freeze the time the presence reads."""
    frozen_clock = _Clock()
    monkeypatch.setattr(presence_module, "naive_utc_now", frozen_clock)
    return frozen_clock


@pytest.fixture
def presence(monkeypatch: pytest.MonkeyPatch) -> DesktopAppPresence:
    """A presence of its own for the routes, so no test sees another one's desktop app."""
    fresh_presence = DesktopAppPresence(online_window=timedelta(minutes=3))
    monkeypatch.setattr(prospect_searches_routes, "desktop_app_presence", fresh_presence)
    return fresh_presence


def _client(db: Session, user_id: int) -> TestClient:
    """The prospect search routes, called by a signed-in user on the test database."""
    application = FastAPI()
    application.include_router(prospect_searches_router)
    signed_in_user: Any = SimpleNamespace(id=user_id)
    application.dependency_overrides[require_auth] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def test_a_desktop_app_never_seen_is_offline() -> None:
    assert DesktopAppPresence().is_online(USER_ID) is False


def test_a_desktop_app_stays_online_while_it_keeps_looking(clock: _Clock) -> None:
    presence = DesktopAppPresence(online_window=timedelta(minutes=3))

    presence.mark_seen(USER_ID)
    clock.now += timedelta(minutes=3)

    assert presence.is_online(USER_ID) is True
    assert presence.is_online(OTHER_USER_ID) is False


def test_a_desktop_app_silent_for_longer_than_the_window_is_offline(clock: _Clock) -> None:
    presence = DesktopAppPresence(online_window=timedelta(minutes=3))

    presence.mark_seen(USER_ID)
    clock.now += timedelta(minutes=3, seconds=1)

    assert presence.is_online(USER_ID) is False


def test_the_activity_tells_the_ipad_the_desktop_app_is_on(
    clock: _Clock, presence: DesktopAppPresence, db: Session
) -> None:
    ipad, desktop_app = _client(db, USER_ID), _client(db, USER_ID)

    before = ipad.get("/prospect-searches/activity").json()
    desktop_app.get("/prospect-searches/activity", params={"from_desktop_app": "true"})
    after = ipad.get("/prospect-searches/activity").json()
    someone_else = _client(db, OTHER_USER_ID).get("/prospect-searches/activity").json()

    assert (before["is_desktop_app_online"], after["is_desktop_app_online"]) == (False, True)
    assert someone_else["is_desktop_app_online"] is False


def test_the_ipad_looking_at_the_activity_does_not_pass_for_the_desktop_app(
    clock: _Clock, presence: DesktopAppPresence, db: Session
) -> None:
    ipad = _client(db, USER_ID)

    ipad.get("/prospect-searches/activity")

    assert ipad.get("/prospect-searches/activity").json()["is_desktop_app_online"] is False
