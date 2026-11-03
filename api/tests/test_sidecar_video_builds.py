"""The desktop video builds of the sidecar: a checked payload, one detached build for both videos, and its failures."""

from __future__ import annotations

import asyncio
import io
import json
import logging
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi import HTTPException, UploadFile
from pydantic import ValidationError

import scraper_sidecar as sidecar
from services import video_pipeline
from services.assistant_widget_clip_service import AssistantWidgetClipError, assistant_widget_clip_service
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
# The context the API sends for a receptionist video, with the calibration preview's extras.
_RECEPTIONIST_CONTEXT: dict[str, Any] = {
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
    receptionist = sidecar._parse_video_build_request(
        sidecar.DesktopVideoBuildRequest, json.dumps(_RECEPTIONIST_CONTEXT)
    )

    assert (site.story_id, site.total_seconds, site.preview) == ("61234567", 28.5, False)
    assert (receptionist.slug, receptionist.presenter_intro, receptionist.preview) == ("toitures-morel", 5.0, True)


@pytest.mark.parametrize("slug", ["../../Windows/Temp/x", "garage martin", "", "-garage", "a" * 121])
def test_a_slug_that_could_leave_the_build_folder_is_refused(slug: str) -> None:
    assert _invalid_fields(sidecar.DesktopVideoBuildRequest, {**_RECEPTIONIST_CONTEXT, "slug": slug}) == (
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


def _receptionist_request(slug: str) -> sidecar.DesktopVideoBuildRequest:
    return sidecar.DesktopVideoBuildRequest(**{**_RECEPTIONIST_CONTEXT, "slug": slug, "preview": False})


def _run_receptionist_build(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, slug: str, capture: Any) -> None:
    async def montage(**kwargs: Any) -> None:
        Path(kwargs["output_video"]).write_bytes(b"video")
        Path(kwargs["output_thumb"]).write_bytes(b"thumbnail")

    monkeypatch.setattr(assistant_widget_clip_service, "build_widget_clip", capture)
    monkeypatch.setattr(sidecar, "_compose_desktop_montage", montage)
    monkeypatch.setattr(sidecar, "_chrome_path", "chrome.exe")
    asyncio.run(sidecar._run_assistant_video_build(_receptionist_request(slug), tmp_path))


def test_a_capture_error_ends_the_build_with_its_message(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def capture(**kwargs: Any) -> None:
        raise AssistantWidgetClipError("L'exemple ne s'est pas joué pendant la capture.")

    _run_receptionist_build(monkeypatch, tmp_path, "garage-echec", capture)

    progress = sidecar._VIDEO_BUILD_PROGRESS["garage-echec"]
    assert (progress["step"], progress["message"]) == ("error", "L'exemple ne s'est pas joué pendant la capture.")
    assert not tmp_path.exists()
    assert "garage-echec" not in sidecar._VIDEO_BUILD_RESULTS


def test_an_unexpected_crash_still_ends_the_build(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def capture(**kwargs: Any) -> None:
        raise KeyError("total_seconds")

    _run_receptionist_build(monkeypatch, tmp_path, "garage-crash", capture)

    progress = sidecar._VIDEO_BUILD_PROGRESS["garage-crash"]
    assert (progress["step"], progress["message"]) == ("error", "Erreur inattendue : 'total_seconds'")


def test_a_build_longer_than_the_app_waits_is_stopped(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(video_pipeline, "MAXIMUM_GENERATION_SECONDS", 0.05)

    def capture(**kwargs: Any) -> None:
        time.sleep(0.5)

    _run_receptionist_build(monkeypatch, tmp_path, "garage-lent", capture)

    progress = sidecar._VIDEO_BUILD_PROGRESS["garage-lent"]
    assert (progress["step"], progress["message"]) == ("error", video_pipeline.GENERATION_OVERRUN_MESSAGE)


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


def test_the_start_saves_the_uploads_and_keeps_the_detached_build(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    builds: list[tuple[str, Path, Path | None]] = []

    async def build(request: sidecar.DesktopVideoBuildRequest, work_dir: Path, photo_path: Path | None) -> None:
        builds.append((request.slug, work_dir, photo_path))
        assert (work_dir / "presenter.mp4").read_bytes() == b"clip"
        raise RuntimeError("bug after the start")

    monkeypatch.setattr(sidecar, "_run_assistant_video_build", build)

    async def start() -> dict[str, object]:
        response = await sidecar.video_build_assistant_full(
            payload=json.dumps(_RECEPTIONIST_CONTEXT),
            presenter=UploadFile(file=io.BytesIO(b"clip"), filename="presenter.mp4"),
            presenter_photo=None,
        )
        assert len(sidecar._VIDEO_BUILD_TASKS) == 1
        await asyncio.sleep(0.01)
        return response

    with caplog.at_level(logging.ERROR, logger="scraper_sidecar"):
        response = asyncio.run(start())

    assert response == {"started": True, "slug": "toitures-morel"}
    [(slug, work_dir, photo_path)] = builds
    assert (slug, photo_path) == ("toitures-morel", None)
    assert not sidecar._VIDEO_BUILD_TASKS
    assert any(record.getMessage() == "Detached video build died" for record in caplog.records)
    sidecar._discard_video_build_result(slug)
    sidecar._VIDEO_BUILD_PROGRESS.pop(slug, None)
    for leftover in work_dir.iterdir():
        leftover.unlink()
    work_dir.rmdir()


def test_an_invalid_payload_starts_nothing() -> None:
    async def start() -> None:
        await sidecar.video_build_assistant_full(
            payload=json.dumps({**_RECEPTIONIST_CONTEXT, "slug": "../../x"}),
            presenter=UploadFile(file=io.BytesIO(b"clip"), filename="presenter.mp4"),
            presenter_photo=None,
        )

    with pytest.raises(HTTPException) as refusal:
        asyncio.run(start())

    assert refusal.value.status_code == 422
    assert "../../x" not in sidecar._VIDEO_BUILD_PROGRESS
