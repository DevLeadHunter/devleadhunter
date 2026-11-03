"""The Storyblok session must read as valid only for a present AND unexpired token."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import pytest

from services.storyblok_session_service import (
    StoryblokSessionSeed,
    StoryblokSessionService,
    _token_is_fresh,
)


def _jwt(exp_offset_seconds: int) -> str:
    """A minimal unsigned JWT carrying only an ``exp`` claim ``exp_offset_seconds`` from now."""
    payload = base64.urlsafe_b64encode(json.dumps({"exp": int(time.time()) + exp_offset_seconds}).encode())
    return f"header.{payload.decode().rstrip('=')}.signature"


def test_fresh_token_is_valid() -> None:
    assert _token_is_fresh(_jwt(3600)) is True


def test_expired_token_is_not_valid() -> None:
    assert _token_is_fresh(_jwt(-10)) is False


def test_token_within_margin_is_not_valid() -> None:
    # Expires in 60s but the safety margin is 120s → treat as stale.
    assert _token_is_fresh(_jwt(60)) is False


def test_empty_token_is_not_valid() -> None:
    assert _token_is_fresh("") is False


def test_opaque_non_jwt_token_is_assumed_usable() -> None:
    # No decodable exp → presence is the only signal; the capture-time login-page
    # detection is the authoritative backstop.
    assert _token_is_fresh("opaque-non-jwt-token") is True


def test_seed_is_valid_mirrors_token_freshness() -> None:
    assert StoryblokSessionSeed(local_storage={"token": _jwt(3600)}).is_valid is True
    assert StoryblokSessionSeed(local_storage={"token": _jwt(-10)}).is_valid is False
    assert StoryblokSessionSeed(local_storage={}).is_valid is False


def test_capture_source_prefers_dedicated_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    service = StoryblokSessionService()
    monkeypatch.setattr(service, "read_persisted_state", lambda: {"logged_in": True})
    monkeypatch.setattr(
        service, "resolve_machine_seed", lambda: StoryblokSessionSeed(local_storage={"token": _jwt(3600)})
    )
    seed, user_data_dir = service.resolve_capture_source()
    assert seed is None and user_data_dir is not None  # the in-app account wins


def test_capture_source_falls_back_to_machine_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    service = StoryblokSessionService()
    fresh = StoryblokSessionSeed(local_storage={"token": _jwt(3600)})
    monkeypatch.setattr(service, "read_persisted_state", lambda: None)
    monkeypatch.setattr(service, "resolve_machine_seed", lambda: fresh)
    seed, user_data_dir = service.resolve_capture_source()
    assert seed is fresh and user_data_dir is None


def test_capture_source_ignores_machine_seed_after_logout(monkeypatch: pytest.MonkeyPatch) -> None:
    service = StoryblokSessionService()
    monkeypatch.setattr(service, "read_persisted_state", lambda: {"logged_in": False, "ignore_machine_seed": True})
    monkeypatch.setattr(
        service, "resolve_machine_seed", lambda: StoryblokSessionSeed(local_storage={"token": _jwt(3600)})
    )
    seed, user_data_dir = service.resolve_capture_source()
    assert seed is None and user_data_dir is None  # explicit logout → needs a fresh in-app login


def test_a_session_storyblok_refused_asks_for_a_reconnect_and_keeps_the_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = StoryblokSessionService(dedicated_profile_dir=tmp_path)
    service.write_persisted_state(logged_in=True)
    (tmp_path / "Default").mkdir()
    monkeypatch.setattr(
        service, "resolve_machine_seed", lambda: StoryblokSessionSeed(local_storage={"token": _jwt(3600)})
    )
    assert service.state() == "ready"

    assert service.mark_session_expired(login_state_written_at=service.read_login_state_written_at()) is True

    assert service.state() == "needs_login"
    assert (tmp_path / "Default").is_dir()


def test_a_sign_in_made_after_the_capture_picked_its_session_is_kept(tmp_path: Path) -> None:
    service = StoryblokSessionService(dedicated_profile_dir=tmp_path)
    service.write_persisted_state(logged_in=True)

    assert service.mark_session_expired(login_state_written_at="2026-10-18T17:40:58.693302+00:00") is False

    assert service.state() == "ready"


def test_a_refused_browser_session_without_saved_login_asks_for_a_reconnect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = StoryblokSessionService(dedicated_profile_dir=tmp_path)
    monkeypatch.setattr(
        service, "resolve_machine_seed", lambda: StoryblokSessionSeed(local_storage={"token": "opaque-non-jwt-token"})
    )
    assert service.state() == "ready"

    assert service.mark_session_expired(login_state_written_at=None) is True

    assert service.state() == "needs_login"
