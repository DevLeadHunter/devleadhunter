"""Local scraping sidecar shipped inside the desktop app.

Google blocks datacenter IPs, so the browser-driven scraping (nodriver/Chrome)
must run on the USER's machine, with their residential IP — never on the VPS.
This module is the entrypoint the Tauri shell spawns: a minimal FastAPI app
exposing only the scraping endpoints that need a real browser.

It deliberately carries **no database and no background worker**: every endpoint
here is purely functional (scrape → return JSON), so the packaged binary needs
no credentials. Persisting the result stays the remote API's job.

Run: ``python scraper_sidecar.py --port 8765`` (Tauri passes the port and a
one-shot token; see ``web/src-tauri/src/scraper_sidecar.rs``).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import multiprocessing
import os
import shutil
import sys
import time

import uvicorn
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.win32_asyncio import ensure_proactor_event_loop
from models.prospect import (
    ProspectCreate,
    ProspectEnrichRequest,
    ProspectSearchSuggestion,
    ProspectSearchSuggestionsRequest,
)
from scrappers.chrome_provisioning import ensure_chrome, find_installed_chrome
from scrappers.email_scraper import email_scraper
from scrappers.enrichment_scraper import EnrichmentData, enrichment_scraper
from scrappers.google_scraper import close_maps_suggestion_session
from services.prospect_enrichment_service import prospect_enrichment_service

logger = logging.getLogger(__name__)


def _resolve_bundled_ffmpeg() -> str:
    """
    Path to ffmpeg: the copy bundled in the frozen sidecar, else FFMPEG_PATH / PATH.

    Keeps desktop video generation plug-and-play — a user never installs ffmpeg.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        candidate = os.path.join(meipass, name)
        if os.path.isfile(candidate):
            return candidate
    return os.environ.get("FFMPEG_PATH") or "ffmpeg"


# Resolve ffmpeg once, before any service reads FFMPEG_PATH (the Storyblok editor clip
# service and the montage both honour it), so the bundled binary is used when frozen.
_FFMPEG_PATH = _resolve_bundled_ffmpeg()
os.environ["FFMPEG_PATH"] = _FFMPEG_PATH

# Current phase of each local video build, keyed by demo-site slug — polled by the
# app's progress modal so long builds stop looking frozen.
_VIDEO_BUILD_PROGRESS: dict[str, dict[str, object]] = {}

_VIDEO_BUILD_STEP_MESSAGES: dict[str, str] = {
    "preparing": "Préparation (clip présentateur, session Storyblok)…",
    "site_capture": "Capture du site (défilement)…",
    "editor_capture": "Séquence éditeur Storyblok…",
    "background_assemble": "Assemblage du fond…",
    "montage": "Montage final (webcam + habillage)…",
    "done": "Vidéo prête.",
}


def _set_video_build_progress(slug: str, step: str, message: str | None = None) -> None:
    """Record the current phase of a local video build (read by /video/build-progress)."""
    _VIDEO_BUILD_PROGRESS[slug] = {
        "step": step,
        "message": message if message is not None else _VIDEO_BUILD_STEP_MESSAGES.get(step, step),
        "updated_at": time.time(),
    }


class SidecarEnrichmentRequest(BaseModel):
    """Business to enrich, as the desktop app asks for it."""

    business_name: str
    city: str | None = None
    # Maps place URL persisted at discovery — anchors the scrape on the exact
    # listing instead of re-searching by name (homonym safety).
    google_maps_url: str | None = None
    # Facebook page URL — enrichment anchor used when there is no Google listing.
    facebook_url: str | None = None


class StoryblokBackgroundClipRequest(BaseModel):
    """Everything the sidecar needs to render a prospect's video background."""

    slug: str
    demo_url: str
    space_id: str
    story_id: str
    # Trade-aware hero line typed in the editor demo (e.g. a landscaper phrase for a
    # landscaper site); empty falls back to a neutral default in the clip service.
    accroche: str = ""
    site_seconds: float = 14.0
    hold_seconds: float = 1.0
    total_seconds: float | None = None
    out_width: int = 1280
    out_height: int = 720
    fps: int = 30


async def close_transient_browsers() -> None:
    """Close the throwaway Chrome windows a request opened.

    ``email_scraper`` is a shared singleton whose browser is never closed by its
    own code paths. On a server that only wastes memory; on the user's desktop it
    leaves visible Chrome windows piling up after every action, so the sidecar
    cleans up once each request is done.
    """
    try:
        if email_scraper.browser:
            await email_scraper.close()
    except Exception:
        logger.warning("Could not close the transient email-scraper browser", exc_info=True)


async def close_autocomplete_session() -> None:
    """Drop the autocomplete tab once the user has picked their business."""
    try:
        await close_maps_suggestion_session()
    except Exception:
        logger.warning("Could not close the autocomplete session", exc_info=True)


# État de l'approvisionnement Chrome, exposé par ``/health``.
_chrome_state: str = "unknown"
_chrome_path: str | None = None
# Why the last provisioning attempt failed — surfaced to the app so the user sees
# the actual cause (firewall, network…) instead of a bare « unavailable ».
_chrome_error: str = ""

# Le sidecar n'écoute que la boucle locale : il ne doit jamais être joignable
# depuis le réseau, même sur une machine partagée.
LOOPBACK_HOST = "127.0.0.1"

# Origines de la coquille Tauri (Windows/WebView2 sert l'app depuis tauri.localhost).
_ALLOWED_ORIGINS: list[str] = [
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
    "http://localhost:1420",
]

app = FastAPI(
    title="DevLeadHunter — scraping sidecar",
    description="Local browser-driven scraping, executed on the user's machine.",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


def require_sidecar_token(x_sidecar_token: str = Header(default="")) -> None:
    """Reject anything that does not carry the token Tauri generated at startup.

    Loopback alone is not enough: any local process — including a web page the
    user has open — could otherwise drive the scraper.

    Args:
        x_sidecar_token: Token sent by the desktop app on every call.

    Raises:
        HTTPException: 401 when the token is missing or wrong.
    """
    expected = os.environ.get("SIDECAR_TOKEN", "")
    if not expected or x_sidecar_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Jeton sidecar invalide.")


@app.on_event("startup")
async def provision_chrome() -> None:
    """Make sure a Chrome is available, downloading one on first launch if needed.

    Runs in a worker thread so the sidecar answers ``/health`` immediately: the
    very first launch may spend minutes fetching Chrome for Testing, and the
    desktop app must be able to show that state rather than look frozen.
    """

    if find_installed_chrome():
        _provision()
        return

    global _chrome_state
    _chrome_state = "installing"
    asyncio.get_running_loop().run_in_executor(None, _provision)


def _provision() -> None:
    """Find or download Chrome, recording the outcome (and the failure cause)."""
    global _chrome_state, _chrome_path, _chrome_error
    try:
        _chrome_path = ensure_chrome()
        _chrome_state = "ready"
        _chrome_error = ""
    except Exception as exc:
        _chrome_state = "unavailable"
        _chrome_error = str(exc)
        logger.exception("Chrome provisioning failed: %s", exc)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe the desktop shell polls before routing any call.

    ``chrome`` is ``ready``, ``installing`` (first-launch download) or
    ``unavailable`` — the app surfaces it instead of failing on the first scrape.
    """
    return {
        "status": "ok",
        "chrome": _chrome_state,
        "chrome_path": _chrome_path or "",
        "chrome_error": _chrome_error,
    }


@app.post("/chrome/provision", dependencies=[Depends(require_sidecar_token)])
async def retry_chrome_provisioning() -> dict[str, str]:
    """Retry finding or downloading Chrome without restarting the app.

    The startup attempt can fail transiently (network refusal, firewall prompt
    denied); the app calls this before a browser-driven run so the user is never
    stuck on « unavailable » until the next restart.

    Returns:
        The chrome state after (or while) retrying.
    """
    global _chrome_state, _chrome_error
    if _chrome_state in ("ready", "installing"):
        return {"chrome": _chrome_state}
    _chrome_state = "installing"
    _chrome_error = ""
    asyncio.get_running_loop().run_in_executor(None, _provision)
    return {"chrome": _chrome_state}


@app.post(
    "/scraper/search-suggestions",
    response_model=list[ProspectSearchSuggestion],
    dependencies=[Depends(require_sidecar_token)],
)
async def search_suggestions(request: ProspectSearchSuggestionsRequest) -> list[ProspectSearchSuggestion]:
    """Google Maps autocomplete for the « add a prospect » drawer.

    Args:
        request: Business name, optional city and result cap.

    Returns:
        The matching business suggestions.

    Raises:
        HTTPException: 400 when the search itself fails (Chrome, network, blocking).
    """
    try:
        return await prospect_enrichment_service.search_suggestions(
            query=request.query,
            city=request.city,
            max_results=request.max_results,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post(
    "/scraper/enrich",
    response_model=ProspectCreate,
    dependencies=[Depends(require_sidecar_token)],
)
async def enrich(request: ProspectEnrichRequest) -> ProspectCreate:
    """Pre-fill a prospect from its Google Maps listing, without saving it.

    Args:
        request: Business name and/or Google Maps URL, optional city.

    Returns:
        The prospect draft the drawer displays.

    Raises:
        HTTPException: 400 when the listing cannot be read.
    """
    try:
        return await prospect_enrichment_service.enrich_from_google(
            business_name=request.business_name,
            google_maps_url=request.google_maps_url,
            city=request.city,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        await close_transient_browsers()
        await close_autocomplete_session()


@app.post(
    "/scraper/enrichment",
    response_model=EnrichmentData,
    dependencies=[Depends(require_sidecar_token)],
)
async def enrichment(request: SidecarEnrichmentRequest) -> EnrichmentData:
    """Scrape the full enrichment of a business (photos, reviews, hours, socials).

    Returns the raw result: persisting it stays the remote API's job, which is
    why nothing here touches a database.

    Args:
        request: Business name and optional city.

    Returns:
        The scraped enrichment payload.

    Raises:
        HTTPException: 400 when the enrichment cannot be scraped.
    """
    try:
        return await enrichment_scraper.enrich(
            business_name=request.business_name,
            city=request.city,
            google_maps_url=request.google_maps_url,
            facebook_url=request.facebook_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        await close_transient_browsers()
        await close_autocomplete_session()


@app.get("/storyblok/session", dependencies=[Depends(require_sidecar_token)])
async def storyblok_session() -> dict[str, object]:
    """Current Storyblok connection state for the config card (ready/needs_login/busy)."""
    from services.storyblok_login_helper import storyblok_login_helper

    return await storyblok_login_helper.state()


@app.post("/storyblok/open-login", dependencies=[Depends(require_sidecar_token)])
async def storyblok_open_login() -> dict[str, object]:
    """Open a visible window for a one-time Storyblok sign-in (dedicated profile)."""
    from services.storyblok_login_helper import storyblok_login_helper

    return await storyblok_login_helper.open_login(executable_path=_chrome_path or find_installed_chrome())


@app.post("/storyblok/close-login", dependencies=[Depends(require_sidecar_token)])
async def storyblok_close_login() -> dict[str, bool]:
    """Close the login window if the user opened it and is done."""
    from services.storyblok_login_helper import storyblok_login_helper

    await storyblok_login_helper.close()
    return {"closed": True}


@app.post("/storyblok/logout", dependencies=[Depends(require_sidecar_token)])
async def storyblok_logout() -> dict[str, bool]:
    """Forget the Storyblok session (wrong account?) so the user can reconnect."""
    from services.storyblok_login_helper import storyblok_login_helper
    from services.storyblok_session_service import storyblok_session_service

    await storyblok_login_helper.close()
    storyblok_session_service.logout()
    return {"logged_out": True}


@app.post("/storyblok/background-clip", dependencies=[Depends(require_sidecar_token)])
async def storyblok_background_clip(request: StoryblokBackgroundClipRequest) -> object:
    """
    Render the video background (linear site scroll + Storyblok editor edit).

    Resolves the session cascade (machine browser → dedicated profile). Returns the
    mp4 file; when no session is available, returns ``{"skipped": true}`` so the
    caller composes the video without the editor sequence.
    """
    import tempfile
    from pathlib import Path

    from fastapi.responses import FileResponse, JSONResponse
    from starlette.background import BackgroundTask

    from services.storyblok_editor_clip_service import StoryblokEditorClipError, storyblok_editor_clip_service
    from services.storyblok_session_service import storyblok_session_service

    # Dedicated in-app profile wins; machine (Firefox) seed is the fallback, skipped
    # after an explicit logout — so the user really chooses the account.
    seed, user_data_dir = storyblok_session_service.resolve_capture_source()
    if seed is None and user_data_dir is None:
        return JSONResponse({"skipped": True, "reason": "needs_login"}, status_code=status.HTTP_409_CONFLICT)

    work_dir = Path(tempfile.mkdtemp(prefix=f"sb-bg-{request.slug}-"))
    output_path = work_dir / "background.mp4"
    try:
        await asyncio.to_thread(
            storyblok_editor_clip_service.build_background,
            demo_url=request.demo_url,
            space_id=request.space_id,
            story_id=request.story_id,
            output_path=output_path,
            seed=seed,
            user_data_dir=user_data_dir,
            accroche=request.accroche,
            executable_path=_chrome_path or find_installed_chrome(),
            site_seconds=request.site_seconds,
            hold_seconds=request.hold_seconds,
            total_seconds=request.total_seconds,
            out_width=request.out_width,
            out_height=request.out_height,
            fps=request.fps,
        )
    except StoryblokEditorClipError as exc:
        shutil.rmtree(work_dir, ignore_errors=True)
        message = str(exc)
        # A session that expired mid-capture is a reconnect prompt, not a hard error.
        if message.startswith("needs_login:"):
            return JSONResponse({"skipped": True, "reason": "needs_login"}, status_code=status.HTTP_409_CONFLICT)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc

    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename=f"{request.slug}-background.mp4",
        background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
    )


@app.get("/video/build-progress", dependencies=[Depends(require_sidecar_token)])
async def video_build_progress(slug: str) -> dict[str, object]:
    """Current phase of a local video build, for the app's progress modal."""
    return _VIDEO_BUILD_PROGRESS.get(slug, {"step": "unknown", "message": "", "updated_at": 0})


@app.post("/video/build-full", dependencies=[Depends(require_sidecar_token)])
async def video_build_full(payload: str = Form(...), presenter: UploadFile = File(...)) -> object:
    """
    Produce the COMPLETE prospection video on the desktop (capture + montage).

    Captures the background (site scroll + Storyblok editor) with the owner's session,
    then montages it with the uploaded presenter clip (webcam PiP, greeting, thumbnail)
    using the bundled ffmpeg — the VPS is never involved. Returns a zip
    (``video.mp4`` + ``thumbnail.jpg``); ``409 {reason: needs_login}`` when the Storyblok
    session is missing so the caller prompts a reconnect.
    """
    import json
    import tempfile
    import zipfile
    from pathlib import Path

    from fastapi.responses import FileResponse, JSONResponse
    from starlette.background import BackgroundTask

    from services import video_montage
    from services.storyblok_editor_clip_service import StoryblokEditorClipError, storyblok_editor_clip_service
    from services.storyblok_session_service import storyblok_session_service

    data = json.loads(payload)
    seed, user_data_dir = storyblok_session_service.resolve_capture_source()
    if seed is None and user_data_dir is None:
        return JSONResponse({"skipped": True, "reason": "needs_login"}, status_code=status.HTTP_409_CONFLICT)

    slug = str(data["slug"])
    total_seconds = float(data["total_seconds"])
    _set_video_build_progress(slug, "preparing")
    work_dir = Path(tempfile.mkdtemp(prefix=f"video-full-{slug}-"))
    background_path = work_dir / "background.mp4"
    presenter_path = work_dir / "presenter.mp4"
    screenshot_path = work_dir / "top.png"
    output_video = work_dir / "video.mp4"
    output_thumb = work_dir / "thumbnail.jpg"
    bundle_path = work_dir / f"{slug}-video.zip"
    try:
        with open(presenter_path, "wb") as buffer:
            shutil.copyfileobj(presenter.file, buffer)

        await asyncio.to_thread(
            storyblok_editor_clip_service.build_background,
            demo_url=data["demo_url"],
            space_id=data["space_id"],
            story_id=data["story_id"],
            output_path=background_path,
            seed=seed,
            user_data_dir=user_data_dir,
            accroche=data.get("accroche", ""),
            executable_path=_chrome_path or find_installed_chrome(),
            site_seconds=float(data.get("site_seconds", 14.0)),
            hold_seconds=float(data.get("hold_seconds", 1.0)),
            total_seconds=total_seconds,
            out_width=int(data.get("out_width", 1280)),
            out_height=int(data.get("out_height", 720)),
            fps=int(data.get("fps", 30)),
            on_progress=lambda step: _set_video_build_progress(slug, step),
        )
        _set_video_build_progress(slug, "montage")
        await asyncio.to_thread(video_montage.extract_first_frame, _FFMPEG_PATH, background_path, screenshot_path)
        await asyncio.to_thread(
            video_montage.compose_final,
            ffmpeg_path=_FFMPEG_PATH,
            presenter_duration=float(data["presenter_duration"]),
            presenter_intro=float(data["presenter_intro"]),
            presenter_outro=float(data["presenter_outro"]),
            presenter_path=presenter_path,
            capture_path=background_path,
            scroll_offset=0.0,
            scroll_seconds=total_seconds,
            first_name=data.get("first_name") or None,
            screenshot_path=screenshot_path,
            output_video=output_video,
            output_thumbnail=output_thumb,
        )
        # preview=true → the caller only wants to WATCH the result (timing calibration):
        # return the mp4 alone, nothing gets uploaded or published.
        if not bool(data.get("preview")):
            with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_STORED) as archive:
                archive.write(output_video, "video.mp4")
                archive.write(output_thumb, "thumbnail.jpg")
    except StoryblokEditorClipError as exc:
        shutil.rmtree(work_dir, ignore_errors=True)
        message = str(exc)
        if message.startswith("needs_login:"):
            _set_video_build_progress(slug, "error", "Session Storyblok expirée — reconnexion nécessaire.")
            return JSONResponse({"skipped": True, "reason": "needs_login"}, status_code=status.HTTP_409_CONFLICT)
        _set_video_build_progress(slug, "error", message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message) from exc
    except video_montage.VideoMontageError as exc:
        shutil.rmtree(work_dir, ignore_errors=True)
        _set_video_build_progress(slug, "error", str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    _set_video_build_progress(slug, "done")
    if bool(data.get("preview")):
        return FileResponse(
            output_video,
            media_type="video/mp4",
            filename=f"{slug}-preview.mp4",
            background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
        )
    return FileResponse(
        bundle_path,
        media_type="application/zip",
        filename=f"{slug}-video.zip",
        background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
    )


def main() -> None:
    """Start the sidecar on the loopback port the desktop shell picked."""
    parser = argparse.ArgumentParser(description="DevLeadHunter local scraping sidecar")
    parser.add_argument("--port", type=int, default=int(os.environ.get("SIDECAR_PORT", "8765")))
    args = parser.parse_args()

    if sys.platform == "win32":
        # PyInstaller One-File respawns the process; without this it forks forever.
        multiprocessing.freeze_support()
        ensure_proactor_event_loop()

    logging.basicConfig(level=logging.INFO)
    logger.info("Scraping sidecar listening on http://%s:%s", LOOPBACK_HOST, args.port)
    uvicorn.run(app, host=LOOPBACK_HOST, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
