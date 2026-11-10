"""The desktop video builds of the sidecar: a checked payload, the detached site build, and its failures."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import scraper_sidecar as sidecar
from services.storyblok_editor_clip_service import StoryblokEditorClipError, storyblok_editor_clip_service
from services.storyblok_session_service import storyblok_session_service

# The context the API sends for a site video (``GET /demo-sites/{id}/video-background-context``).
_SITE_CONTEXT: dict[str, Any] = {
    "slug": "garage-martin",
    "demo_url": "https://demo.dibodev.fr/garage-martin",
    "space_id": "287465",
    "story_id": "61234567",
    "accroche": "Votre garage à Clermont-Ferrand",
    "first_name": "Claire",
    "presenter_duration": 42.5,
    "presenter_intro": 6.0,
    "presenter_outro": 8.0,
    "site_seconds": 11.5,
    "hold_seconds": 1.0,
    "total_seconds": 28.5,
    "out_width": 1280,
    "out_height": 720,
    "fps": 30,
}
# The context a product module's API sends for its own video (the receptionist's), with the calibration preview's
# extras.
_MODULE_CONTEXT: dict[str, Any] = {
    "slug": "toitures-morel",
    "demo_url": "https://demo.dibodev.fr/ia/toitures-morel",
    "first_name": None,
    "presenter_duration": 40,
    "presenter_intro": 5,
    "presenter_outro": 9,
    "total_seconds": 26,
    "out_width": 1280,
    "out_height": 720,
    "fps": 30,
    "preview": True,
}


def _invalid_fields(request_model: type[sidecar.DesktopVideoBuildRequest], payload: dict[str, Any]) -> str:
    with pytest.raises(HTTPException) as refusal:
        sidecar._parse_video_build_request(request_model, json.dumps(payload))
    assert refusal.value.status_code == 422
    return str(refusal.value.detail)


def test_the_contexts_the_api_sends_are_accepted() -> None:
    site = sidecar._parse_video_build_request(sidecar.SiteVideoBuildRequest, json.dumps(_SITE_CONTEXT))
    module_video = sidecar._parse_video_build_request(sidecar.DesktopVideoBuildRequest, json.dumps(_MODULE_CONTEXT))

    assert (site.story_id, site.total_seconds, site.preview) == ("61234567", 28.5, False)
    assert (module_video.slug, module_video.presenter_intro, module_video.preview) == ("toitures-morel", 5.0, True)


@pytest.mark.parametrize("slug", ["../../Windows/Temp/x", "garage martin", "", "-garage", "a" * 121])
def test_a_slug_that_could_leave_the_build_folder_is_refused(slug: str) -> None:
    assert _invalid_fields(sidecar.DesktopVideoBuildRequest, {**_MODULE_CONTEXT, "slug": slug}) == (
        "Demande de génération invalide (slug)."
    )


@pytest.mark.parametrize(
    "demo_url", ["file:///C:/Windows/win.ini", "javascript:alert(1)", "https://", "demo.dibodev.fr"]
)
def test_a_page_that_is_not_a_web_address_is_refused(demo_url: str) -> None:
    assert "demo_url" in _invalid_fields(sidecar.SiteVideoBuildRequest, {**_SITE_CONTEXT, "demo_url": demo_url})


def test_missing_or_nonsense_timings_are_refused_before_anything_starts() -> None:
    payload = {**_SITE_CONTEXT, "total_seconds": "trente", "presenter_intro": -1}
    del payload["presenter_duration"]

    assert _invalid_fields(sidecar.SiteVideoBuildRequest, payload) == (
        "Demande de génération invalide (presenter_duration, presenter_intro, total_seconds)."
    )


def test_a_payload_that_is_not_json_is_refused() -> None:
    with pytest.raises(HTTPException) as refusal:
        sidecar._parse_video_build_request(sidecar.DesktopVideoBuildRequest, "{slug:")
    assert refusal.value.detail == "Demande de génération invalide (payload)."


def test_the_site_build_request_checks_its_slug_and_story() -> None:
    with pytest.raises(ValidationError):
        sidecar.SiteVideoBuildRequest(**{**_SITE_CONTEXT, "slug": "../x"})
    with pytest.raises(ValidationError):
        sidecar.SiteVideoBuildRequest(**{**_SITE_CONTEXT, "space_id": "287465/../1"})
    assert sidecar.SiteVideoBuildRequest(**_SITE_CONTEXT).site_seconds == 11.5


def _run_site_build_failing_with(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, error_message: str, saved_login_state_written_at: str
) -> list[str | None]:
    """Run a site build whose capture raises *error_message*; return the saved logins it marked expired."""

    def capture(**kwargs: Any) -> None:
        raise StoryblokEditorClipError(error_message)

    marked_expired: list[str | None] = []

    def mark_session_expired(*, login_state_written_at: str | None) -> bool:
        marked_expired.append(login_state_written_at)
        return True

    monkeypatch.setattr(storyblok_editor_clip_service, "build_background", capture)
    monkeypatch.setattr(storyblok_session_service, "mark_session_expired", mark_session_expired)
    monkeypatch.setattr(sidecar, "_chrome_path", "chrome.exe")
    request = sidecar.SiteVideoBuildRequest(**_SITE_CONTEXT)
    asyncio.run(
        sidecar._run_video_build(
            request, None, "profile", tmp_path, login_state_written_at=saved_login_state_written_at
        )
    )
    return marked_expired


def test_a_storyblok_session_lost_during_the_site_build_asks_to_reconnect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    marked_expired = _run_site_build_failing_with(
        monkeypatch,
        tmp_path,
        "needs_login: session Storyblok expirée ou absente — reconnecte-toi.",
        saved_login_state_written_at="2026-10-18T17:40:58.693302+00:00",
    )

    assert sidecar._VIDEO_BUILD_PROGRESS["garage-martin"]["reason"] == "needs_login"
    assert marked_expired == ["2026-10-18T17:40:58.693302+00:00"]


def test_another_editor_failure_leaves_the_storyblok_login_alone(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    marked_expired = _run_site_build_failing_with(
        monkeypatch,
        tmp_path,
        "L'éditeur Storyblok ne s'est pas ouvert.",
        saved_login_state_written_at="2026-11-03T18:44:44+00:00",
    )

    assert sidecar._VIDEO_BUILD_PROGRESS["garage-martin"]["message"] == "L'éditeur Storyblok ne s'est pas ouvert."
    assert marked_expired == []
