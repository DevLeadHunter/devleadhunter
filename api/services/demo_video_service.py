"""Prospection video generation for demo sites.

Assembles, per prospect, a short (~30-45 s) video from:
  - the user's generic presenter clip (webcam + voice, uploaded once —
    see ``presenter_video_service``), full-screen for the intro/outro;
  - an automated scroll capture of the prospect's OWN generated demo site
    (Playwright records the page while a script scrolls it smoothly);
  - a text greeting « Bonjour {Prénom} » overlaid on the intro (text, not
    cloned voice — decision from the reflection ticket);
  - a personalised email thumbnail (site screenshot + play button) used by
    the ``{vignette_video}`` template variable.

Timeline (D = presenter clip duration):
  0 ─ intro ──────────── D-outro ───────── D
  webcam plein écran │ site + webcam PiP │ webcam plein écran (CTA)

The voice stays 100 % generic — personalisation is visual only (his site,
his first name) so ONE recording works for every prospect.

Rendering happens in a temp directory, then the mp4 + jpg are pushed to
Cloudflare R2 (``videos/websites/{slug}.mp4`` / ``images/websites/{slug}.jpg``)
and served straight from Cloudflare — the VPS never streams a byte. The player
page lives on the demo host at ``/v/{slug}`` (PostHog-tracked, same identity as
the demo).
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.orm import Session

from core.config import settings
from enums.demo_site_status import DemoSiteStatus
from enums.demo_video_status import DemoVideoStatus
from models.demo_site import DemoSite
from models.presenter_video import PresenterVideo
from services import video_montage
from services.r2_storage_service import r2_storage

logger = logging.getLogger(__name__)

# Un seul rendu à la fois : Playwright + ffmpeg sont lourds pour la machine
# qui héberge aussi les scrapers.
_generation_semaphore = asyncio.Semaphore(1)

# Durée minimale du segment « site qui défile » pour que la capture ait un sens.
_MIN_SCROLL_SECONDS = 6.0

# Garde-fou mémoire du fallback serveur : capturer le site en headless (Chromium)
# puis monter avec ffmpeg dépasse facilement le plafond du service sur un VPS chargé.
# En dessous de ce seuil de mémoire disponible, on refuse proprement plutôt que de
# laisser l'OOM killer emporter toute l'API.
_MIN_FREE_MEMORY_MB_FOR_CAPTURE = 1200.0

# The ffmpeg montage is lighter than a headless capture, but it still OOM-killed the
# whole API on a starved box. Refuse it (fail clean) below this floor — this covers
# the desktop path too, where the montage is the only server-side step.
_MIN_FREE_MEMORY_MB_FOR_MONTAGE = 500.0


def _available_memory_mb() -> float | None:
    """
    Available system memory in MB, read from Linux ``/proc/meminfo``.

    Returns:
        The available memory in MB, or None when it cannot be read (e.g. on a
        non-Linux host, where the server-side capture never runs anyway).
    """
    try:
        with open("/proc/meminfo", encoding="ascii") as meminfo:
            for line in meminfo:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1024
    except (OSError, ValueError):
        return None
    return None


def video_object_key(slug: str) -> str:
    """R2 key of a demo site's generated prospection video."""
    return r2_storage.website_video_key(slug)


def thumbnail_object_key(slug: str) -> str:
    """R2 key of a demo site's email thumbnail."""
    return r2_storage.website_thumbnail_key(slug)


def video_page_url(slug: str) -> str:
    """Public player-page URL on the demo host (PostHog-tracked)."""
    return f"{settings.demo_host_base_url.rstrip('/')}/v/{slug}"


def public_video_file_url(slug: str) -> str:
    """Public R2 URL of the mp4 (served by Cloudflare, never by the API)."""
    return r2_storage.public_url(video_object_key(slug))


def public_thumbnail_url(slug: str) -> str:
    """Public R2 URL of the email thumbnail (absolute — embedded in emails)."""
    return r2_storage.public_url(thumbnail_object_key(slug))


def has_ready_video(site: DemoSite) -> bool:
    """
    True when the site's prospection video is generated.

    Objects live on R2, so this trusts the DB status rather than doing a network
    round-trip on every email render; deletions go through
    :func:`delete_files_for_slug`, whose callers also reset the status.
    """
    return site.video_status == DemoVideoStatus.READY.value


def delete_files_for_slug(slug: str) -> None:
    """Remove the generated video + thumbnail from R2 (best effort)."""
    try:
        r2_storage.delete_many(
            [video_object_key(slug), thumbnail_object_key(slug), r2_storage.website_background_key(slug)]
        )
    except Exception:
        logger.warning("[Video] R2 cleanup failed for slug=%s", slug, exc_info=True)


class DemoVideoGenerationError(Exception):
    """Raised when a step of the video pipeline fails (message shown in-app)."""


class DemoVideoService:
    """Orchestrates capture + composition of prospection videos."""

    def request_generation(self, db: Session, site: DemoSite, user_id: int) -> DemoSite:
        """
        Validate and start a background generation for a demo site.

        Args:
            db: Active database session (request-scoped).
            site: Demo site owned by the user.
            user_id: Owner (used to fetch the presenter clip).

        Returns:
            The site with ``video_status`` set to ``pending``.

        Raises:
            ValueError: when the site or presenter clip is not ready.
        """
        from services.presenter_video_service import presenter_video_service

        if site.status != DemoSiteStatus.ACTIVE.value:
            raise ValueError("La vidéo ne peut être générée que pour un site démo actif.")
        if not site.demo_url:
            raise ValueError("Ce site démo n'a pas d'URL publique.")
        if site.video_status in (DemoVideoStatus.PENDING.value, DemoVideoStatus.GENERATING.value):
            raise ValueError("Une génération est déjà en cours pour ce site.")

        presenter = presenter_video_service.get_for_user(db, user_id)
        if presenter is None:
            raise ValueError(
                "Aucun clip de présentation. Enregistrez d'abord votre vidéo webcam "
                "(voix générique) dans « Vidéo de présentation »."
            )
        scroll_seconds = presenter.duration_seconds - presenter.intro_seconds - presenter.outro_seconds
        if scroll_seconds < _MIN_SCROLL_SECONDS:
            raise ValueError(
                "Intro + outro trop longues pour la durée du clip : il reste "
                f"{scroll_seconds:.0f}s pour montrer le site (minimum {_MIN_SCROLL_SECONDS:.0f}s)."
            )

        site.video_status = DemoVideoStatus.PENDING.value
        site.video_error = None
        db.commit()
        db.refresh(site)

        asyncio.create_task(self._run_generation(site.id, user_id))
        return site

    def maybe_start_auto_generation(self, db: Session, site: DemoSite, user_id: int) -> bool:
        """
        Best-effort auto-generation hook, called right after a demo site is
        created (single, bulk AND full-automation paths all go through
        ``demo_site_service.create_demo_site``).

        Fires only when the user has a presenter clip with ``auto_generate``
        enabled; never raises (a video failure must not fail site creation).

        Returns:
            True when a generation was started.
        """
        from services.presenter_video_service import presenter_video_service

        try:
            presenter = presenter_video_service.get_for_user(db, user_id)
            if presenter is None or not presenter.auto_generate:
                return False
            self.request_generation(db, site, user_id)
            logger.info("Auto video generation started for slug=%s", site.slug)
            return True
        except ValueError as exc:
            logger.info("Auto video generation skipped for slug=%s: %s", site.slug, exc)
            return False
        except Exception:
            logger.exception("Auto video generation hook failed for slug=%s", site.slug)
            return False

    def reconcile_orphaned(self, db: Session) -> int:
        """
        Mark demo sites left mid-generation as failed (called once at startup).

        A generation task lives only in memory, so a process restart — a crash, an
        OOM kill, a deploy — orphans any site still in ``pending``/``generating``:
        no task will ever finish it, and :meth:`request_generation` refuses to
        restart a site in those states, so the dashboard polls it forever.

        Args:
            db: Active database session.

        Returns:
            The number of sites reset to ``failed``.
        """
        orphaned: list[DemoSite] = (
            db.query(DemoSite)
            .filter(DemoSite.video_status.in_([DemoVideoStatus.PENDING.value, DemoVideoStatus.GENERATING.value]))
            .all()
        )
        for site in orphaned:
            site.video_status = DemoVideoStatus.FAILED.value
            site.video_error = "Génération interrompue (redémarrage du serveur) — relancez-la."
        if orphaned:
            db.commit()
        return len(orphaned)

    def clear_video(self, db: Session, site: DemoSite) -> DemoSite:
        """Delete the generated video files and reset the site's video state."""
        delete_files_for_slug(site.slug)
        site.video_status = None
        site.video_error = None
        site.video_generated_at = None
        db.commit()
        db.refresh(site)
        return site

    # ------------------------------------------------------------------ #
    # Background job
    # ------------------------------------------------------------------ #

    async def _run_generation(self, demo_site_id: int, user_id: int) -> None:
        """Background task: own DB session, serialized by a global semaphore."""
        from core.database import SessionLocal
        from services.presenter_video_service import presenter_video_service

        async with _generation_semaphore:
            db: Session = SessionLocal()
            try:
                site: DemoSite | None = db.query(DemoSite).filter(DemoSite.id == demo_site_id).first()
                if site is None:
                    return
                presenter = presenter_video_service.get_for_user(db, user_id)
                if presenter is None:
                    site.video_status = DemoVideoStatus.FAILED.value
                    site.video_error = "Aucun clip de présentation configuré."
                    db.commit()
                    return

                site.video_status = DemoVideoStatus.GENERATING.value
                db.commit()

                first_name = self._resolve_first_name(db, site)
                # Le clip source vit sur R2 : on le matérialise en temp pour ffmpeg.
                source_dir = Path(tempfile.mkdtemp(prefix=f"presenter-src-{user_id}-"))
                try:
                    presenter_path = await self._resolve_presenter_file(presenter, source_dir)
                    photo_path = await self._resolve_presenter_photo(db, user_id, source_dir)
                    await self._generate(site, presenter, presenter_path, first_name, photo_path)
                except DemoVideoGenerationError as exc:
                    site.video_status = DemoVideoStatus.FAILED.value
                    site.video_error = str(exc)[:1000]
                    db.commit()
                    logger.warning("Video generation failed for slug=%s: %s", site.slug, exc)
                    return
                except Exception as exc:
                    site.video_status = DemoVideoStatus.FAILED.value
                    site.video_error = f"Erreur inattendue : {exc}"[:1000]
                    db.commit()
                    logger.exception("Video generation crashed for slug=%s", site.slug)
                    return
                finally:
                    shutil.rmtree(source_dir, ignore_errors=True)

                site.video_status = DemoVideoStatus.READY.value
                site.video_error = None
                site.video_generated_at = datetime.now(UTC)
                db.commit()
                logger.info("Prospection video ready for slug=%s", site.slug)
            finally:
                db.close()

    @staticmethod
    def _resolve_first_name(db: Session, site: DemoSite) -> str | None:
        """First name of the resolved decision-maker (None when unknown)."""
        if not site.prospect_id:
            return None
        from services.email_variables import EmailVariables

        first, _last, _gender = EmailVariables.resolved_contact(db, site.prospect_id)
        return first or None

    # ------------------------------------------------------------------ #
    # Pipeline steps
    # ------------------------------------------------------------------ #

    @staticmethod
    async def _resolve_presenter_file(presenter: PresenterVideo, work_dir: Path) -> Path:
        """
        Materialise the presenter clip as a local file for ffmpeg.

        Clips live on R2 under ``videos/presenter/{user_id}.mp4``; rows written
        before the R2 migration still hold a local disk path and keep working.

        Args:
            presenter: The user's presenter clip row.
            work_dir: Temp directory receiving the download.

        Returns:
            Path to a readable local file.

        Raises:
            DemoVideoGenerationError: when the clip cannot be resolved.
        """
        stored = str(presenter.file_path or "").strip()
        if not stored:
            raise DemoVideoGenerationError("Clip de présentation introuvable.")

        if stored.startswith(r2_storage.VIDEOS_PRESENTER_PREFIX):
            try:
                return await r2_storage.download_to_path_async(stored, work_dir / "presenter.mp4")
            except Exception as exc:
                raise DemoVideoGenerationError("Clip de présentation illisible sur le stockage (R2).") from exc

        legacy = Path(stored)
        if legacy.is_file():
            return legacy
        raise DemoVideoGenerationError("Clip de présentation introuvable.")

    @staticmethod
    async def _resolve_presenter_photo(db: Session, user_id: int, work_dir: Path) -> Path | None:
        """
        Materialise the user's profile photo (thumbnail bubble) as a local file.

        The photo is optional and must never fail a generation: any resolution
        problem just means a thumbnail without the bubble.

        Args:
            db: Active database session.
            user_id: Owner of the photo.
            work_dir: Temp directory receiving the download.

        Returns:
            Path to a readable local file, or None when the user has no photo.
        """
        from models.user import User

        user = db.query(User).filter(User.id == user_id).first()
        stored = str(user.profile_photo_path or "").strip() if user else ""
        if not stored:
            return None
        try:
            return await r2_storage.download_to_path_async(stored, work_dir / "presenter-photo.jpg")
        except Exception:
            logger.warning("Presenter photo unavailable for user=%s — thumbnail without bubble", user_id)
            return None

    async def _generate(
        self,
        site: DemoSite,
        presenter: PresenterVideo,
        presenter_path: Path,
        first_name: str | None,
        presenter_photo_path: Path | None,
    ) -> None:
        """Capture the site, compose the video, build the thumbnail, publish to R2."""
        scroll_seconds = presenter.duration_seconds - presenter.intro_seconds - presenter.outro_seconds
        work_dir = Path(tempfile.mkdtemp(prefix=f"demo-video-{site.slug}-"))
        try:
            # Prefer the desktop-produced background (site scroll + Storyblok editor,
            # sized to scroll_seconds); fall back to a plain site capture otherwise.
            background = await self._resolve_background(site, work_dir)
            if background is not None:
                capture_path, scroll_offset, screenshot_path = background
            else:
                # No desktop-produced background → server-side headless capture (the
                # heavy fallback). Refuse it when the box is already low on memory so
                # a fallback generation can never OOM-kill the whole API.
                self._guard_capture_memory()
                capture_path, scroll_offset, screenshot_path = await self._capture_site(
                    site.demo_url or "", scroll_seconds, work_dir
                )
            output_path = work_dir / "output.mp4"
            thumbnail_path = work_dir / "thumbnail.jpg"
            # The montage runs on the VPS even in the desktop path — never let it OOM the box.
            self._guard_montage_memory()
            try:
                await asyncio.to_thread(
                    video_montage.compose_final,
                    ffmpeg_path=settings.ffmpeg_path,
                    presenter_duration=presenter.duration_seconds,
                    presenter_intro=presenter.intro_seconds,
                    presenter_outro=presenter.outro_seconds,
                    presenter_path=presenter_path,
                    capture_path=capture_path,
                    scroll_offset=scroll_offset,
                    scroll_seconds=scroll_seconds,
                    first_name=first_name,
                    screenshot_path=screenshot_path,
                    output_video=output_path,
                    output_thumbnail=thumbnail_path,
                    presenter_photo_path=presenter_photo_path,
                )
            except video_montage.VideoMontageError as exc:
                raise DemoVideoGenerationError(str(exc)) from exc

            # Publication sur R2 : c'est Cloudflare qui sert, plus le VPS.
            await r2_storage.upload_file_async(output_path, video_object_key(site.slug), "video/mp4")
            await r2_storage.upload_file_async(thumbnail_path, thumbnail_object_key(site.slug), "image/jpeg")
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    @staticmethod
    def _guard_capture_memory() -> None:
        """
        Refuse the server-side headless capture when the box is low on memory.

        This is the fallback path (no desktop background): headless Chromium plus
        the ffmpeg montage can exceed the service memory cap on a busy VPS, and an
        OOM kill there takes down the whole single-worker API. Failing cleanly with
        a clear message is always better than crashing the box.

        Raises:
            DemoVideoGenerationError: when available memory is below the floor.
        """
        available = _available_memory_mb()
        if available is not None and available < _MIN_FREE_MEMORY_MB_FOR_CAPTURE:
            raise DemoVideoGenerationError(
                f"Serveur momentanément trop chargé pour générer la vidéo ici ({available:.0f} Mo libres). "
                "Générez-la depuis l'application desktop, ou réessayez plus tard."
            )

    @staticmethod
    def _guard_montage_memory() -> None:
        """
        Refuse the ffmpeg montage when the box is low on memory.

        The montage runs on the VPS even when the (heavy) capture happened on the
        desktop, and it OOM-killed the whole single-worker API on a starved box.
        Failing cleanly is always better than taking the box down.

        Raises:
            DemoVideoGenerationError: when available memory is below the montage floor.
        """
        available = _available_memory_mb()
        if available is not None and available < _MIN_FREE_MEMORY_MB_FOR_MONTAGE:
            raise DemoVideoGenerationError(
                f"Serveur momentanément trop chargé pour assembler la vidéo ({available:.0f} Mo libres). "
                "Réessayez dans quelques minutes."
            )

    async def _capture_site(self, url: str, scroll_seconds: float, work_dir: Path) -> tuple[Path, float, Path]:
        """
        Record the demo site scrolling smoothly for ``scroll_seconds``.

        ⚠️ Uses Playwright's SYNC API inside a worker thread: the uvicorn
        reload worker may run a SelectorEventLoop on Windows, where asyncio
        subprocess support (needed to spawn the browser) raises
        ``NotImplementedError``. A plain thread has no event loop, so the
        sync API works everywhere.

        Returns:
            (capture webm path, offset of the scroll start inside the recording in seconds, top-of-page screenshot path).

        Raises:
            DemoVideoGenerationError: when the page cannot be captured.
        """
        return await asyncio.to_thread(self._capture_site_sync, url, scroll_seconds, work_dir)

    async def _resolve_background(self, site: DemoSite, work_dir: Path) -> tuple[Path, float, Path] | None:
        """
        Use the desktop-produced video background if one is stored on R2.

        The background (site scroll + Storyblok editor) is rendered on the sidecar
        because it needs the owner's Storyblok session; here we just materialise it.

        Returns:
            ``(capture_path, scroll_offset=0, screenshot_path)`` or ``None`` to fall
            back to a plain site capture.
        """
        key = r2_storage.website_background_key(site.slug)
        try:
            if not r2_storage.exists(key):
                return None
            capture_path = await r2_storage.download_to_path_async(key, work_dir / "background.mp4")
        except Exception:
            logger.warning("[Video] background fetch failed for slug=%s", site.slug, exc_info=True)
            return None
        screenshot_path = work_dir / "top.png"
        self._extract_first_frame(capture_path, screenshot_path)
        return capture_path, 0.0, screenshot_path

    @staticmethod
    def _extract_first_frame(video_path: Path, output_path: Path) -> None:
        """Grab the first frame of a video (top of the site) for the email thumbnail."""
        subprocess.run(
            [
                settings.ffmpeg_path,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-threads",
                video_montage.FFMPEG_THREADS,
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(output_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )

    @staticmethod
    def _as_internal_url(url: str) -> str:
        """Add ``internal=1`` so a capture visit is excluded from tracking/notifications."""
        parts = urlparse(url)
        query = dict(parse_qsl(parts.query))
        query["internal"] = "1"
        return urlunparse(parts._replace(query=urlencode(query)))

    def _capture_site_sync(self, url: str, scroll_seconds: float, work_dir: Path) -> tuple[Path, float, Path]:
        """Blocking Playwright capture (see ``_capture_site``)."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover — dependency guard
            raise DemoVideoGenerationError(
                "Playwright n'est pas installé (pip install playwright && playwright install chromium)."
            ) from exc

        screenshot_path = work_dir / "top.png"
        # ?internal=1 tags this as the owner's own visit so the capture never fires
        # prospect notifications / tracking events (guarded by DemoBeaconUtils).
        internal_url = self._as_internal_url(url)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": video_montage.WIDTH, "height": video_montage.HEIGHT},
                    record_video_dir=str(work_dir),
                    record_video_size={"width": video_montage.WIDTH, "height": video_montage.HEIGHT},
                )
                page = context.new_page()
                recording_start = time.monotonic()

                try:
                    page.goto(internal_url, wait_until="networkidle", timeout=45000)
                except Exception:
                    page.goto(internal_url, wait_until="load", timeout=45000)
                page.wait_for_timeout(1200)

                # Pré-scroll : déclenche les animations d'entrée + lazy-load,
                # puis retour en haut pour la passe enregistrée.
                page.evaluate(
                    """
                    async () => {
                      const step = window.innerHeight * 0.8;
                      const max = document.documentElement.scrollHeight - window.innerHeight;
                      for (let y = 0; y <= max; y += step) {
                        window.scrollTo(0, y);
                        await new Promise((r) => setTimeout(r, 120));
                      }
                      window.scrollTo(0, max);
                      await new Promise((r) => setTimeout(r, 250));
                      window.scrollTo(0, 0);
                    }
                    """
                )
                page.wait_for_timeout(800)
                page.screenshot(path=str(screenshot_path))

                # Passe enregistrée : scroll fluide (ease in/out) calé sur la
                # durée du segment site de la piste audio.
                scroll_start = time.monotonic()
                scroll_offset = scroll_start - recording_start
                page.evaluate(
                    """
                    async (durationMs) => {
                      const max = document.documentElement.scrollHeight - window.innerHeight;
                      if (max <= 0) {
                        await new Promise((r) => setTimeout(r, durationMs));
                        return;
                      }
                      const start = performance.now();
                      const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
                      await new Promise((resolve) => {
                        const tick = (now) => {
                          const progress = Math.min((now - start) / durationMs, 1);
                          window.scrollTo(0, max * ease(progress));
                          if (progress < 1) requestAnimationFrame(tick);
                          else resolve();
                        };
                        requestAnimationFrame(tick);
                      });
                    }
                    """,
                    int(scroll_seconds * 1000),
                )
                page.wait_for_timeout(400)

                video = page.video
                context.close()
                browser.close()
                if video is None:
                    raise DemoVideoGenerationError("Playwright n'a pas produit d'enregistrement vidéo.")
                capture_path = Path(video.path())
        except DemoVideoGenerationError:
            raise
        except Exception as exc:
            raise DemoVideoGenerationError(f"Échec de la capture du site ({url}) : {exc}") from exc

        if not capture_path.is_file():
            raise DemoVideoGenerationError("Fichier de capture introuvable après l'enregistrement.")
        return capture_path, scroll_offset, screenshot_path


demo_video_service = DemoVideoService()
