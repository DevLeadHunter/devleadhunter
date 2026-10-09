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
import functools
import logging
import multiprocessing
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import urlparse

import uvicorn
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError, field_validator

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
from scrappers.facebook_enrichment_scraper import facebook_enrichment_scraper
from scrappers.google_scraper import close_maps_suggestion_session
from services.country_profiles import DEFAULT_COUNTRY_CODE
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
    "widget_capture": "Capture de la réceptionniste (réponse en direct)…",
    "widget_assemble": "Assemblage de la séquence réceptionniste…",
    "montage": "Montage final (webcam + habillage)…",
    "done": "Vidéo prête.",
}


def _set_video_build_progress(slug: str, step: str, message: str | None = None, reason: str | None = None) -> None:
    """Record the current phase of a local video build (read by /video/build-progress)."""
    _VIDEO_BUILD_PROGRESS[slug] = {
        "step": step,
        "message": message if message is not None else _VIDEO_BUILD_STEP_MESSAGES.get(step, step),
        "reason": reason,
        "updated_at": time.time(),
    }


# Finished builds waiting to be fetched via /video/build-result, keyed by slug.
# The webview kills a single multi-minute HTTP response (surfacing as a CORS error),
# so builds run detached: POST starts them, the app polls progress, then fetches this.
_VIDEO_BUILD_RESULTS: dict[str, dict[str, object]] = {}

# Strong references to running build tasks — asyncio only keeps weak ones, and a
# garbage-collected task dies silently mid-build.
_VIDEO_BUILD_TASKS: set[asyncio.Task[None]] = set()

_PRESENTER_FILE_NAME = "presenter.mp4"
_PRESENTER_PHOTO_FILE_NAME = "presenter-photo.jpg"
_SCREENSHOT_FILE_NAME = "top.png"

_SLUG_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,119}$"
_STORYBLOK_ID_PATTERN = r"^\d{1,20}$"


def _keep_video_build(task: asyncio.Task[None]) -> None:
    """Hold a detached build until it ends, logging the exception it may die with."""
    _VIDEO_BUILD_TASKS.add(task)
    task.add_done_callback(_forget_video_build)


def _forget_video_build(task: asyncio.Task[None]) -> None:
    """Drop a finished build; a build records its own failures, so an exception here is a bug worth a log."""
    _VIDEO_BUILD_TASKS.discard(task)
    if not task.cancelled() and task.exception() is not None:
        logger.error("Detached video build died", exc_info=task.exception())


def _discard_video_build_result(slug: str) -> None:
    """Drop a previous build's result (and its files) before starting a new one."""
    entry = _VIDEO_BUILD_RESULTS.pop(slug, None)
    if entry is not None:
        shutil.rmtree(str(entry["work_dir"]), ignore_errors=True)


class SidecarEnrichmentRequest(BaseModel):
    """Business to enrich, as the desktop app asks for it."""

    business_name: str
    city: str | None = None
    # Maps place URL persisted at discovery — anchors the scrape on the exact
    # listing instead of re-searching by name (homonym safety).
    google_maps_url: str | None = None
    # Facebook page URL — enrichment anchor used when there is no Google listing.
    facebook_url: str | None = None
    country: str = DEFAULT_COUNTRY_CODE


class SidecarFacebookContactRequest(BaseModel):
    """Facebook page whose contact block the prospect search asks to read."""

    business_name: str
    facebook_url: str
    country: str = DEFAULT_COUNTRY_CODE


class SidecarFacebookContact(BaseModel):
    """Contact block read on a Facebook page (``is_readable`` false when it opened without a readable block)."""

    is_readable: bool
    emails: list[str]
    phone: str | None
    website: str | None


class SidecarVideoTarget(BaseModel):
    """The page a desktop video build films, and the size of the clip it renders."""

    # The slug names the build's temporary folder and files.
    slug: str = Field(pattern=_SLUG_PATTERN)
    demo_url: str
    out_width: int = Field(default=1280, gt=0)
    out_height: int = Field(default=720, gt=0)
    fps: int = Field(default=30, gt=0, le=60)

    @field_validator("demo_url")
    @classmethod
    def require_web_address(cls, demo_url: str) -> str:
        """
        Accept only an http(s) address with a host: the capture opens it in a browser.

        Args:
            demo_url: The page to film.

        Returns:
            The address, unchanged.

        Raises:
            ValueError: for any other scheme (``file:``, ``javascript:``…) or an address without a host.
        """
        parts = urlparse(demo_url)
        if parts.scheme not in ("http", "https") or not parts.netloc:
            raise ValueError("demo_url doit être une adresse http(s)")
        return demo_url


class StoryblokEditorSequence(BaseModel):
    """The Storyblok editor sequence of a site video: the story to open and the hero line typed into it."""

    space_id: str = Field(pattern=_STORYBLOK_ID_PATTERN)
    story_id: str = Field(pattern=_STORYBLOK_ID_PATTERN)
    # Trade-aware hero line typed in the editor demo (e.g. a landscaper phrase for a
    # landscaper site); empty falls back to a neutral default in the clip service.
    accroche: str = ""
    site_seconds: float = Field(default=14.0, gt=0)
    hold_seconds: float = Field(default=1.0, ge=0)


class DesktopVideoBuildRequest(SidecarVideoTarget):
    """A complete desktop build: the page to film, and the presenter clip's timings the montage needs."""

    total_seconds: float = Field(gt=0)
    presenter_duration: float = Field(gt=0)
    presenter_intro: float = Field(ge=0)
    presenter_outro: float = Field(ge=0)
    first_name: str | None = None
    # A calibration preview (unsaved timings, from the video settings) comes back as a bare mp4, never uploaded.
    preview: bool = False


class SiteVideoBuildRequest(StoryblokEditorSequence, DesktopVideoBuildRequest):
    """A complete desktop build of a site video, whose middle ends on the Storyblok editor sequence."""


BuildRequestT = TypeVar("BuildRequestT", bound=DesktopVideoBuildRequest)


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
        request: Business name, optional city, and the prospect's country deciding the
            postal code and phone shapes read.

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
            country=request.country,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        await close_transient_browsers()
        await close_autocomplete_session()


@app.post(
    "/scraper/facebook-contact",
    response_model=SidecarFacebookContact,
    dependencies=[Depends(require_sidecar_token)],
)
async def facebook_contact(request: SidecarFacebookContactRequest) -> SidecarFacebookContact:
    """Read the contact block of a public Facebook page for the prospect search.

    A quick read (email, phone, website): photos and reviews are left to the full
    enrichment, which only runs on the prospects the search keeps.

    Args:
        request: Candidate name, Facebook page URL and country.

    Returns:
        What the page publishes; ``is_readable`` is false when the page opened without a readable block.

    Raises:
        HTTPException: 503 when the browser could not do the read (the candidate must stay waiting).
    """
    try:
        page = await facebook_enrichment_scraper.read_contact(
            business_name=request.business_name,
            facebook_url=request.facebook_url,
            country=request.country,
        )
    finally:
        await close_transient_browsers()
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le navigateur n'a pas pu lire cette page Facebook. Réessayez dans un instant.",
        )
    return SidecarFacebookContact(
        is_readable=page.place_title is not None,
        emails=list(page.emails),
        phone=page.phone,
        website=page.website,
    )


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


@app.get("/video/build-progress", dependencies=[Depends(require_sidecar_token)])
async def video_build_progress(slug: str) -> dict[str, object]:
    """Current phase of a local video build, for the app's progress modal."""
    return _VIDEO_BUILD_PROGRESS.get(slug, {"step": "unknown", "message": "", "updated_at": 0})


@app.post("/video/build-full", dependencies=[Depends(require_sidecar_token)])
async def video_build_full(
    payload: str = Form(...),
    presenter: UploadFile = File(...),
    presenter_photo: UploadFile | None = File(default=None),
) -> object:
    """
    START the complete desktop video build (capture + montage) and return at once.

    A single multi-minute HTTP response gets killed by the webview (it surfaces as a
    CORS error while the build is still running), so the build is detached: this
    returns ``{"started": true}`` immediately, the app polls ``/video/build-progress``
    until ``done``/``error``, then fetches the file from ``/video/build-result``.
    ``409 {reason: needs_login}`` when the Storyblok session is missing, ``422`` when the payload is invalid.
    """
    from fastapi.responses import JSONResponse

    from services.storyblok_session_service import storyblok_session_service

    request = _parse_video_build_request(SiteVideoBuildRequest, payload)
    seed, user_data_dir = storyblok_session_service.resolve_capture_source()
    if seed is None and user_data_dir is None:
        return JSONResponse({"skipped": True, "reason": "needs_login"}, status_code=status.HTTP_409_CONFLICT)
    return await _start_detached_video_build(
        request,
        presenter,
        presenter_photo,
        run_build=functools.partial(_run_video_build, request, seed, user_data_dir),
    )


@app.post("/video/build-assistant-full", dependencies=[Depends(require_sidecar_token)])
async def video_build_assistant_full(
    payload: str = Form(...),
    presenter: UploadFile = File(...),
    presenter_photo: UploadFile | None = File(default=None),
) -> object:
    """
    START the complete desktop assistant-video build (widget capture + montage) and return at once.

    Same detached contract as ``/video/build-full`` (a single multi-minute response gets killed by the
    webview): returns ``{"started": true}``, the app polls ``/video/build-progress`` until
    ``done``/``error``, then fetches the file from ``/video/build-result``. Unlike the site build there
    is no Storyblok session to resolve — the assistant widget is public, so this never needs a login.
    ``422`` when the payload is invalid.
    """
    request = _parse_video_build_request(DesktopVideoBuildRequest, payload)
    return await _start_detached_video_build(
        request,
        presenter,
        presenter_photo,
        run_build=functools.partial(_run_assistant_video_build, request),
        # The default message names a Storyblok session, which only the site build opens.
        preparing_message="Préparation (clip présentateur)…",
    )


def _parse_video_build_request(request_model: type[BuildRequestT], payload: str) -> BuildRequestT:
    """
    Read and check the JSON payload of a build (a form field, sent next to the uploaded files).

    Args:
        request_model: The model of the payload.
        payload: The raw JSON.

    Returns:
        The validated build request.

    Raises:
        HTTPException: 422 naming the invalid fields, in words the app shows as the build's error.
    """
    try:
        return request_model.model_validate_json(payload)
    except ValidationError as exc:
        invalid_fields = sorted({".".join(str(part) for part in error["loc"]) or "payload" for error in exc.errors()})
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Demande de génération invalide ({', '.join(invalid_fields)}).",
        ) from exc


async def _start_detached_video_build(
    request: DesktopVideoBuildRequest,
    presenter: UploadFile,
    presenter_photo: UploadFile | None,
    *,
    run_build: Callable[[Path, Path | None], Coroutine[Any, Any, None]],
    preparing_message: str | None = None,
) -> dict[str, object]:
    """
    Save the uploads, then start a build detached from the request and return at once.

    Args:
        request: The validated build.
        presenter: The presenter clip upload.
        presenter_photo: The optional profile photo upload.
        run_build: The build, given its folder and the saved photo (None without one).
        preparing_message: The first progress message; the default one when None.

    Returns:
        ``{"started": True, "slug": …}``.
    """
    slug = request.slug
    _discard_video_build_result(slug)
    _set_video_build_progress(slug, "preparing", preparing_message)
    work_dir = Path(tempfile.mkdtemp(prefix=f"video-build-{slug}-"))
    try:
        # The upload's temp file dies with this request — materialise it before detaching.
        (work_dir / _PRESENTER_FILE_NAME).write_bytes(await presenter.read())
        presenter_photo_path = await _save_presenter_photo(presenter_photo, work_dir)
    except Exception:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    _keep_video_build(asyncio.create_task(run_build(work_dir, presenter_photo_path)))
    return {"started": True, "slug": slug}


async def _save_presenter_photo(presenter_photo: UploadFile | None, work_dir: Path) -> Path | None:
    """
    Save the optional profile photo of the thumbnail bubble.

    Args:
        presenter_photo: The upload, None when the owner has no photo.
        work_dir: The build's folder.

    Returns:
        The saved photo, or None when there is none.
    """
    if presenter_photo is None:
        return None
    photo_bytes = await presenter_photo.read()
    if not photo_bytes:
        return None
    photo_path = work_dir / _PRESENTER_PHOTO_FILE_NAME
    photo_path.write_bytes(photo_bytes)
    return photo_path


async def _compose_desktop_montage(
    *,
    request: DesktopVideoBuildRequest,
    presenter_path: Path,
    capture_path: Path,
    screenshot_path: Path,
    output_video: Path,
    output_thumb: Path,
    presenter_photo_path: Path | None,
    thumbnail_label: str,
    pip_corner: str,
) -> None:
    """Run the shared ffmpeg montage for a desktop build (site or assistant), off the event loop.

    Both builds compose the same way — presenter clip + captured middle segment + « Bonjour {Prénom} »
    — and differ only in the captured ``capture_path``, the email ``thumbnail_label`` and the corner of the
    webcam bubble (``pip_corner``).
    """
    from services import video_montage

    await asyncio.to_thread(
        video_montage.compose_final,
        ffmpeg_path=_FFMPEG_PATH,
        presenter_duration=request.presenter_duration,
        presenter_intro=request.presenter_intro,
        presenter_outro=request.presenter_outro,
        presenter_path=presenter_path,
        capture_path=capture_path,
        scroll_offset=0.0,
        scroll_seconds=request.total_seconds,
        first_name=request.first_name or None,
        screenshot_path=screenshot_path,
        output_video=output_video,
        output_thumbnail=output_thumb,
        presenter_photo_path=presenter_photo_path,
        # Desktop: let ffmpeg use every idle core (the below-normal priority keeps the PC responsive).
        threads=video_montage.FFMPEG_THREADS_AUTO,
        thumbnail_label=thumbnail_label,
        pip_corner=pip_corner,
    )


def _store_video_bundle(slug: str, work_dir: Path, output_video: Path, output_thumb: Path) -> None:
    """Zip the finished video + thumbnail and register it for pickup by /video/build-result."""
    import zipfile

    bundle_path = work_dir / f"{slug}-video.zip"
    with zipfile.ZipFile(bundle_path, "w", zipfile.ZIP_STORED) as archive:
        archive.write(output_video, "video.mp4")
        archive.write(output_thumb, "thumbnail.jpg")
    _VIDEO_BUILD_RESULTS[slug] = {
        "path": bundle_path,
        "media_type": "application/zip",
        "filename": f"{slug}-video.zip",
        "work_dir": work_dir,
    }


def _store_video_preview(slug: str, work_dir: Path, output_video: Path) -> None:
    """Register a calibration preview's bare mp4 for pickup by /video/build-result: nothing is published."""
    _VIDEO_BUILD_RESULTS[slug] = {
        "path": output_video,
        "media_type": "video/mp4",
        "filename": f"{slug}-preview.mp4",
        "work_dir": work_dir,
    }


async def _run_video_build(
    request: SiteVideoBuildRequest,
    seed: object,
    user_data_dir: str | None,
    work_dir: Path,
    presenter_photo_path: Path | None = None,
) -> None:
    """
    Detached site build: the background (site scroll + Storyblok editor), then the shared montage.

    Args:
        request: The validated build.
        seed: The machine's Storyblok session to inject, if any.
        user_data_dir: The dedicated Storyblok profile, if any.
        work_dir: The build's folder, holding the presenter clip.
        presenter_photo_path: The profile photo of the thumbnail bubble, if any.
    """
    from services import video_montage

    await _run_desktop_video_build(
        request,
        work_dir,
        presenter_photo_path,
        capture=functools.partial(_capture_site_background, request, seed, user_data_dir, work_dir),
        thumbnail_label=video_montage.THUMBNAIL_LABEL_SITE,
        pip_corner=video_montage.PIP_CORNER_LEFT,
    )


async def _run_assistant_video_build(
    request: DesktopVideoBuildRequest,
    work_dir: Path,
    presenter_photo_path: Path | None = None,
) -> None:
    """
    Detached receptionist build: the widget answering (then the example space), then the shared montage.

    Args:
        request: The validated build.
        work_dir: The build's folder, holding the presenter clip.
        presenter_photo_path: The profile photo of the thumbnail bubble, if any.
    """
    from services import video_montage

    await _run_desktop_video_build(
        request,
        work_dir,
        presenter_photo_path,
        capture=functools.partial(_capture_receptionist_widget, request, work_dir),
        thumbnail_label=video_montage.THUMBNAIL_LABEL_ASSISTANT,
        pip_corner=video_montage.PIP_CORNER_RIGHT,
    )


async def _run_desktop_video_build(
    request: DesktopVideoBuildRequest,
    work_dir: Path,
    presenter_photo_path: Path | None,
    *,
    capture: Callable[[], Coroutine[Any, Any, tuple[Path, Path]]],
    thumbnail_label: str,
    pip_corner: str,
) -> None:
    """
    Capture the middle, montage, then leave the result for pickup; every failure ends in an ``error`` step.

    Progress goes to ``_VIDEO_BUILD_PROGRESS`` (polled by the app's modal) and the finished file to
    ``_VIDEO_BUILD_RESULTS`` (served once by /video/build-result). A build still running when the app stops
    waiting for it is abandoned.

    Args:
        request: The validated build.
        work_dir: The build's folder, holding the presenter clip.
        presenter_photo_path: The profile photo of the thumbnail bubble, if any.
        capture: Films the middle, returning its recording and the thumbnail still.
        thumbnail_label: The words after « Bonjour {Prénom} » on the thumbnail.
        pip_corner: The bottom corner of the webcam bubble.
    """
    from services import video_montage
    from services.assistant_widget_clip_service import AssistantWidgetClipError
    from services.storyblok_editor_clip_service import StoryblokEditorClipError
    from services.video_pipeline import GENERATION_OVERRUN_MESSAGE, MAXIMUM_GENERATION_SECONDS

    slug = request.slug
    output_video = work_dir / "video.mp4"
    output_thumb = work_dir / "thumbnail.jpg"
    try:
        async with asyncio.timeout(MAXIMUM_GENERATION_SECONDS):
            capture_path, screenshot_path = await capture()
            _set_video_build_progress(slug, "montage")
            await _compose_desktop_montage(
                request=request,
                presenter_path=work_dir / _PRESENTER_FILE_NAME,
                capture_path=capture_path,
                screenshot_path=screenshot_path,
                output_video=output_video,
                output_thumb=output_thumb,
                presenter_photo_path=presenter_photo_path,
                thumbnail_label=thumbnail_label,
                pip_corner=pip_corner,
            )
        if request.preview:
            _store_video_preview(slug, work_dir, output_video)
        else:
            _store_video_bundle(slug, work_dir, output_video, output_thumb)
        _set_video_build_progress(slug, "done")
    except TimeoutError:
        shutil.rmtree(work_dir, ignore_errors=True)
        _set_video_build_progress(slug, "error", GENERATION_OVERRUN_MESSAGE)
    except (StoryblokEditorClipError, AssistantWidgetClipError, video_montage.VideoMontageError) as exc:
        shutil.rmtree(work_dir, ignore_errors=True)
        message = str(exc)
        # A Storyblok session that expired mid-capture is a reconnect prompt, not a hard error.
        if message.startswith("needs_login:"):
            _set_video_build_progress(
                slug, "error", "Session Storyblok expirée — reconnexion nécessaire.", reason="needs_login"
            )
        else:
            _set_video_build_progress(slug, "error", message)
    except Exception as exc:  # a detached task must never die silently
        shutil.rmtree(work_dir, ignore_errors=True)
        logger.exception("Video build crashed for slug=%s", slug)
        _set_video_build_progress(slug, "error", f"Erreur inattendue : {exc}")


async def _capture_site_background(
    request: SiteVideoBuildRequest, seed: object, user_data_dir: str | None, work_dir: Path
) -> tuple[Path, Path]:
    """
    Film the middle of a site video (site scroll + Storyblok editor), with its first frame as the thumbnail still.

    Args:
        request: The validated build.
        seed: The machine's Storyblok session to inject, if any.
        user_data_dir: The dedicated Storyblok profile, if any.
        work_dir: The build's folder.

    Returns:
        The background mp4 and the still.

    Raises:
        StoryblokEditorClipError: when the site or the editor cannot be filmed (``needs_login:`` for a lost session).
    """
    from services import video_montage
    from services.storyblok_editor_clip_service import storyblok_editor_clip_service

    background_path = work_dir / "background.mp4"
    screenshot_path = work_dir / _SCREENSHOT_FILE_NAME
    await asyncio.to_thread(
        storyblok_editor_clip_service.build_background,
        demo_url=request.demo_url,
        space_id=request.space_id,
        story_id=request.story_id,
        output_path=background_path,
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
        on_progress=functools.partial(_set_video_build_progress, request.slug),
    )
    await asyncio.to_thread(
        video_montage.extract_first_frame,
        _FFMPEG_PATH,
        background_path,
        screenshot_path,
        video_montage.FFMPEG_THREADS_AUTO,
    )
    return background_path, screenshot_path


async def _capture_receptionist_widget(request: DesktopVideoBuildRequest, work_dir: Path) -> tuple[Path, Path]:
    """
    Film the middle of a receptionist video (the widget answering), with the chat before the scene as the still.

    Args:
        request: The validated build.
        work_dir: The build's folder.

    Returns:
        The widget mp4 and the still.

    Raises:
        AssistantWidgetClipError: when the widget cannot be filmed or its example did not play.
    """
    from services.assistant_widget_clip_service import assistant_widget_clip_service

    widget_path = work_dir / "widget.mp4"
    screenshot_path = work_dir / _SCREENSHOT_FILE_NAME
    await asyncio.to_thread(
        assistant_widget_clip_service.build_widget_clip,
        demo_url=request.demo_url,
        output_path=widget_path,
        screenshot_path=screenshot_path,
        executable_path=_chrome_path or find_installed_chrome(),
        total_seconds=request.total_seconds,
        out_width=request.out_width,
        out_height=request.out_height,
        fps=request.fps,
        on_progress=functools.partial(_set_video_build_progress, request.slug),
    )
    return widget_path, screenshot_path


@app.get("/video/build-result", dependencies=[Depends(require_sidecar_token)])
async def video_build_result(slug: str) -> object:
    """Serve (once) the file produced by a finished build, then clean it up."""
    from fastapi.responses import FileResponse
    from starlette.background import BackgroundTask

    entry = _VIDEO_BUILD_RESULTS.pop(slug, None)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun résultat de build pour ce site.")
    return FileResponse(
        str(entry["path"]),
        media_type=str(entry["media_type"]),
        filename=str(entry["filename"]),
        background=BackgroundTask(shutil.rmtree, str(entry["work_dir"]), ignore_errors=True),
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
