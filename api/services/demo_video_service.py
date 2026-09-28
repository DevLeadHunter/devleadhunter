"""Prospection video generation for demo sites.

Assembles, per prospect, a short (~30-45 s) video from:
  - the user's generic presenter clip (webcam + voice, uploaded once —
    see ``presenter_video_service``), full-screen for the intro/outro;
  - a capture of the prospect's OWN generated demo site: the background the desktop
    app rendered (site scroll + Storyblok editor, which needs the owner's session),
    or, without it, a headless scroll of the site recorded on the VPS;
  - a text greeting « Bonjour {Prénom} » overlaid on the intro (text, not
    cloned voice — decision from the reflection ticket);
  - a personalised email thumbnail (site screenshot + play button) used by
    the ``{vignette_video}`` template variable.

Timeline (D = presenter clip duration):
  0 ─ intro ──────────── D-outro ───────── D
  webcam plein écran │ site + webcam PiP │ webcam plein écran (CTA)

The voice stays 100 % generic — personalisation is visual only (his site,
his first name) so ONE recording works for every prospect.

The generation itself (render, publication, statuses) is shared with the receptionist's video in
:class:`services.prospection_video_service.ProspectionVideoService`. The mp4 + jpg live on Cloudflare R2
(``videos/websites/{slug}.mp4`` / ``images/websites/{slug}.jpg``), served straight from Cloudflare — the VPS
never streams a byte. The player page lives on the demo host at ``/v/{slug}`` (PostHog-tracked, same identity
as the demo).
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path

from core.config import settings
from enums.demo_site_status import DemoSiteStatus
from enums.demo_video_status import DemoVideoStatus
from models.demo_site import DemoSite
from services import video_montage
from services.capture_page import CapturePage
from services.prospection_video_service import CapturedSegment, ProspectionVideoService
from services.r2_storage_service import r2_storage
from services.video_pipeline import VideoGenerationError as DemoVideoGenerationError

logger = logging.getLogger(__name__)

# The presenter clip the site video uses (the generic speech about the site).
SITE_PRESENTER_MODULE = "websites"


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


def public_thumbnail_url(slug: str, generated_at: datetime | None = None) -> str:
    """Public R2 URL of the email thumbnail (absolute — embedded in emails).

    The R2 key never changes for a site, so a regenerated thumbnail kept showing the previous
    image from the browser cache: the generation instant is appended as a version query so every
    regeneration yields a new URL.
    """
    url = r2_storage.public_url(thumbnail_object_key(slug))
    if generated_at is None:
        return url
    return f"{url}?v={int(generated_at.timestamp())}"


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


class DemoVideoService(ProspectionVideoService[DemoSite]):
    """The prospection video of a demo site: its capture (desktop background, else a headless scroll) and its files."""

    subject_model = DemoSite
    kind = "site"
    presenter_module = SITE_PRESENTER_MODULE
    shown_subject = "le site"
    already_running_message = "Une génération est déjà en cours pour ce site."
    missing_presenter_message = (
        "Aucun clip de présentation. Enregistrez d'abord votre vidéo webcam "
        "(voix générique) dans « Vidéo de présentation »."
    )
    thumbnail_label = video_montage.THUMBNAIL_LABEL_SITE
    pip_corner = video_montage.PIP_CORNER_LEFT

    def _check_can_generate(self, site: DemoSite) -> None:
        """
        Refuse a site that is not active or has no public page.

        Args:
            site: The demo site.

        Raises:
            ValueError: with the reason the dashboard shows.
        """
        if site.status != DemoSiteStatus.ACTIVE.value:
            raise ValueError("La vidéo ne peut être générée que pour un site démo actif.")
        if not site.demo_url:
            raise ValueError("Ce site démo n'a pas d'URL publique.")

    def _video_key(self, slug: str) -> str:
        """
        The R2 key of the site video.

        Args:
            slug: The site's slug.

        Returns:
            The object key.
        """
        return video_object_key(slug)

    def _thumbnail_key(self, slug: str) -> str:
        """
        The R2 key of the site video's email thumbnail.

        Args:
            slug: The site's slug.

        Returns:
            The object key.
        """
        return thumbnail_object_key(slug)

    def _delete_files(self, slug: str) -> None:
        """
        Delete the site video's files, its desktop background included.

        Args:
            slug: The site's slug.
        """
        delete_files_for_slug(slug)

    async def _capture_middle(self, site: DemoSite, middle_seconds: float, work_dir: Path) -> CapturedSegment:
        """
        Use the background the desktop app rendered, or record the site scrolling in a headless browser.

        Args:
            site: The demo site.
            middle_seconds: How long the site shows.
            work_dir: The generation's temporary folder.

        Returns:
            The recording and the top-of-site still.

        Raises:
            DemoVideoGenerationError: when the box is low on memory or the site cannot be captured.
        """
        background = await self._download_background(site.slug, work_dir)
        if background is not None:
            return background
        # The heavy fallback: refused when the box is already low on memory.
        self._guard_capture_memory()
        return await asyncio.to_thread(self._capture_site_sync, site.demo_url or "", middle_seconds, work_dir)

    async def _download_background(self, slug: str, work_dir: Path) -> CapturedSegment | None:
        """
        Fetch the background the desktop app rendered, if one is stored on R2.

        The background (site scroll + Storyblok editor) is rendered on the sidecar because it needs the owner's
        Storyblok session; here we just materialise it, with its first frame as the thumbnail still.

        Args:
            slug: The site's slug.
            work_dir: The generation's temporary folder.

        Returns:
            The background, or None to fall back to a plain site capture.
        """
        key = r2_storage.website_background_key(slug)
        try:
            if not r2_storage.exists(key):
                return None
            recording_path = await r2_storage.download_to_path_async(key, work_dir / "background.mp4")
        except Exception:
            logger.warning("[Video] background fetch failed for slug=%s", slug, exc_info=True)
            return None
        screenshot_path = work_dir / "top.png"
        await asyncio.to_thread(
            video_montage.extract_first_frame, settings.ffmpeg_path, recording_path, screenshot_path
        )
        return CapturedSegment(recording_path=recording_path, start_seconds=0.0, screenshot_path=screenshot_path)

    @staticmethod
    def _capture_site_sync(url: str, scroll_seconds: float, work_dir: Path) -> CapturedSegment:
        """
        Record the demo site scrolling smoothly for ``scroll_seconds`` (blocking: run it in a worker thread).

        ⚠️ Uses Playwright's SYNC API inside a worker thread: the uvicorn
        reload worker may run a SelectorEventLoop on Windows, where asyncio
        subprocess support (needed to spawn the browser) raises
        ``NotImplementedError``. A plain thread has no event loop, so the
        sync API works everywhere.

        Args:
            url: The demo site; visited with ``?internal=1``.
            scroll_seconds: How long the scroll lasts.
            work_dir: Temp directory receiving the recording + screenshot.

        Returns:
            The recording, the offset of the scroll start inside it, and the top-of-page screenshot.

        Raises:
            DemoVideoGenerationError: when the page cannot be captured.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover — dependency guard
            raise DemoVideoGenerationError(
                "Playwright n'est pas installé (pip install playwright && playwright install chromium)."
            ) from exc

        screenshot_path = work_dir / "top.png"
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

                CapturePage.open(page, CapturePage.internal_url(url))
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
                recording_path = Path(video.path())
        except DemoVideoGenerationError:
            raise
        except Exception as exc:
            raise DemoVideoGenerationError(f"Échec de la capture du site ({url}) : {exc}") from exc

        if not recording_path.is_file():
            raise DemoVideoGenerationError("Fichier de capture introuvable après l'enregistrement.")
        return CapturedSegment(
            recording_path=recording_path, start_seconds=scroll_offset, screenshot_path=screenshot_path
        )


demo_video_service = DemoVideoService()
