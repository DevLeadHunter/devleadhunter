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

Files land in ``settings.demo_video_dir`` as ``{slug}.mp4`` / ``{slug}.jpg``
and are served by the public demo-site routes; the player page lives on the
demo host at ``/v/{slug}`` (PostHog-tracked, same identity as the demo).
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from core.config import settings
from enums.demo_site_status import DemoSiteStatus
from enums.demo_video_status import DemoVideoStatus
from models.demo_site import DemoSite
from models.presenter_video import PresenterVideo

logger = logging.getLogger(__name__)

# Un seul rendu à la fois : Playwright + ffmpeg sont lourds pour la machine
# qui héberge aussi les scrapers.
_generation_semaphore = asyncio.Semaphore(1)

# Durée minimale du segment « site qui défile » pour que la capture ait un sens.
_MIN_SCROLL_SECONDS = 6.0

# Canvas de sortie (16:9, léger pour un email → une page player).
_WIDTH = 1280
_HEIGHT = 720
_FPS = 30

# Pastille webcam (picture-in-picture) pendant le segment site.
_PIP_SIZE = 260
_PIP_MARGIN = 24

_FONT_CANDIDATES: tuple[str, ...] = (
    "C:/Windows/Fonts/seguisb.ttf",   # Segoe UI Semibold
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


def video_file_path(slug: str) -> Path:
    """Local path of a demo site's generated prospection video."""
    return Path(settings.demo_video_dir) / f"{slug}.mp4"


def thumbnail_file_path(slug: str) -> Path:
    """Local path of a demo site's email thumbnail."""
    return Path(settings.demo_video_dir) / f"{slug}.jpg"


def video_page_url(slug: str) -> str:
    """Public player-page URL on the demo host (PostHog-tracked)."""
    return f"{settings.demo_host_base_url.rstrip('/')}/v/{slug}"


def public_video_file_url(slug: str) -> str:
    """Public URL streaming the mp4 from the API."""
    return f"{settings.api_base_url.rstrip('/')}{settings.api_prefix}/demo-sites/public/{slug}/video.mp4"


def public_thumbnail_url(slug: str) -> str:
    """Public URL of the email thumbnail (absolute — embedded in emails)."""
    return (
        f"{settings.api_base_url.rstrip('/')}{settings.api_prefix}"
        f"/demo-sites/public/{slug}/video-thumbnail.jpg"
    )


def has_ready_video(site: DemoSite) -> bool:
    """True when the site's prospection video is generated and on disk."""
    return (
        site.video_status == DemoVideoStatus.READY.value
        and video_file_path(site.slug).is_file()
    )


def delete_files_for_slug(slug: str) -> None:
    """Remove the generated video + thumbnail files (best effort)."""
    for path in (video_file_path(slug), thumbnail_file_path(slug)):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


class DemoVideoGenerationError(Exception):
    """Raised when a step of the video pipeline fails (message shown in-app)."""


class DemoVideoService:
    """Orchestrates capture + composition of prospection videos."""

    def request_generation(self, db: Session, site: DemoSite, user_id: int) -> DemoSite:
        """
        Validate and start a background generation for a demo site.

        @param db - Active database session (request-scoped).
        @param site - Demo site owned by the user.
        @param user_id - Owner (used to fetch the presenter clip).
        @returns The site with ``video_status`` set to ``pending``.
        @throws ValueError when the site or presenter clip is not ready.
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
                site: Optional[DemoSite] = db.query(DemoSite).filter(DemoSite.id == demo_site_id).first()
                if site is None:
                    return
                presenter = presenter_video_service.get_for_user(db, user_id)
                if presenter is None or not Path(presenter.file_path).is_file():
                    site.video_status = DemoVideoStatus.FAILED.value
                    site.video_error = "Clip de présentation introuvable sur le disque."
                    db.commit()
                    return

                site.video_status = DemoVideoStatus.GENERATING.value
                db.commit()

                first_name = self._resolve_first_name(db, site)
                try:
                    await self._generate(site, presenter, first_name)
                except DemoVideoGenerationError as exc:
                    site.video_status = DemoVideoStatus.FAILED.value
                    site.video_error = str(exc)[:1000]
                    db.commit()
                    logger.warning("Video generation failed for slug=%s: %s", site.slug, exc)
                    return
                except Exception as exc:  # noqa: BLE001 — surface any pipeline crash on the record
                    site.video_status = DemoVideoStatus.FAILED.value
                    site.video_error = f"Erreur inattendue : {exc}"[:1000]
                    db.commit()
                    logger.exception("Video generation crashed for slug=%s", site.slug)
                    return

                site.video_status = DemoVideoStatus.READY.value
                site.video_error = None
                site.video_generated_at = datetime.now(timezone.utc)
                db.commit()
                logger.info("Prospection video ready for slug=%s", site.slug)
            finally:
                db.close()

    @staticmethod
    def _resolve_first_name(db: Session, site: DemoSite) -> Optional[str]:
        """First name of the resolved decision-maker (None when unknown)."""
        if not site.prospect_id:
            return None
        from services.email_variables import resolved_contact

        first, _last, _gender = resolved_contact(db, site.prospect_id)
        return first or None

    # ------------------------------------------------------------------ #
    # Pipeline steps
    # ------------------------------------------------------------------ #

    async def _generate(self, site: DemoSite, presenter: PresenterVideo, first_name: Optional[str]) -> None:
        """Capture the site, compose the video, build the thumbnail."""
        scroll_seconds = presenter.duration_seconds - presenter.intro_seconds - presenter.outro_seconds
        work_dir = Path(settings.demo_video_dir) / "tmp" / f"{site.slug}-{uuid.uuid4().hex[:8]}"
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            capture_path, scroll_offset, screenshot_path = await self._capture_site(
                site.demo_url or "", scroll_seconds, work_dir
            )
            greeting_path = self._build_greeting_overlay(first_name, work_dir)
            mask_path = self._build_circle_mask(work_dir)

            output_path = video_file_path(site.slug)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            await self._compose(
                presenter=presenter,
                capture_path=capture_path,
                scroll_offset=scroll_offset,
                scroll_seconds=scroll_seconds,
                greeting_path=greeting_path,
                mask_path=mask_path,
                output_path=output_path,
            )
            self._build_thumbnail(screenshot_path, first_name, thumbnail_file_path(site.slug))
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    async def _capture_site(
        self, url: str, scroll_seconds: float, work_dir: Path
    ) -> tuple[Path, float, Path]:
        """
        Record the demo site scrolling smoothly for ``scroll_seconds``.

        A first quick pass scrolls to the bottom and back so entrance
        animations and lazy images are settled before the recorded pass.

        @returns (capture webm path, offset of the scroll start inside the
            recording in seconds, top-of-page screenshot path).
        @throws DemoVideoGenerationError when the page cannot be captured.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover — dependency guard
            raise DemoVideoGenerationError(
                "Playwright n'est pas installé (pip install playwright && playwright install chromium)."
            ) from exc

        screenshot_path = work_dir / "top.png"
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": _WIDTH, "height": _HEIGHT},
                    record_video_dir=str(work_dir),
                    record_video_size={"width": _WIDTH, "height": _HEIGHT},
                )
                page = await context.new_page()
                recording_start = time.monotonic()

                try:
                    await page.goto(url, wait_until="networkidle", timeout=45000)
                except Exception:  # noqa: BLE001 — networkidle peut ne jamais arriver (analytics…)
                    await page.goto(url, wait_until="load", timeout=45000)
                await page.wait_for_timeout(1200)

                # Pré-scroll : déclenche les animations d'entrée + lazy-load,
                # puis retour en haut pour la passe enregistrée.
                await page.evaluate(
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
                await page.wait_for_timeout(800)
                await page.screenshot(path=str(screenshot_path))

                # Passe enregistrée : scroll fluide (ease in/out) calé sur la
                # durée du segment site de la piste audio.
                scroll_start = time.monotonic()
                scroll_offset = scroll_start - recording_start
                await page.evaluate(
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
                await page.wait_for_timeout(400)

                video = page.video
                await context.close()
                await browser.close()
                if video is None:
                    raise DemoVideoGenerationError("Playwright n'a pas produit d'enregistrement vidéo.")
                capture_path = Path(await video.path())
        except DemoVideoGenerationError:
            raise
        except Exception as exc:  # noqa: BLE001 — navigation/record errors become a clean message
            raise DemoVideoGenerationError(f"Échec de la capture du site ({url}) : {exc}") from exc

        if not capture_path.is_file():
            raise DemoVideoGenerationError("Fichier de capture introuvable après l'enregistrement.")
        return capture_path, scroll_offset, screenshot_path

    def _load_font(self, size: int):
        """Load a bold-ish system font, falling back to Pillow's default."""
        from PIL import ImageFont

        for candidate in _FONT_CANDIDATES:
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
        return ImageFont.load_default(size=size)

    def _build_greeting_overlay(self, first_name: Optional[str], work_dir: Path) -> Path:
        """
        Render the transparent intro overlay: « Bonjour {Prénom} » in a pill.

        Text, not cloned voice — the personal touch is visual (same rule as
        the {salutation} email variable: a safe greeting, never a wrong name).
        """
        from PIL import Image, ImageDraw

        text = f"Bonjour {first_name} !" if first_name else "Bonjour !"
        font = self._load_font(54)

        image = Image.new("RGBA", (_WIDTH, _HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        text_box = draw.textbbox((0, 0), text, font=font)
        text_w = text_box[2] - text_box[0]
        text_h = text_box[3] - text_box[1]

        pad_x, pad_y = 44, 24
        pill_w = text_w + pad_x * 2
        pill_h = text_h + pad_y * 2
        x0 = (_WIDTH - pill_w) // 2
        y0 = _HEIGHT - pill_h - 64
        draw.rounded_rectangle(
            (x0, y0, x0 + pill_w, y0 + pill_h),
            radius=pill_h // 2,
            fill=(255, 255, 255, 235),
        )
        draw.text(
            (x0 + pad_x - text_box[0], y0 + pad_y - text_box[1]),
            text,
            font=font,
            fill=(17, 17, 17, 255),
        )

        path = work_dir / "greeting.png"
        image.save(path)
        return path

    def _build_circle_mask(self, work_dir: Path) -> Path:
        """White circle on black, used to round the webcam PiP bubble."""
        from PIL import Image, ImageDraw

        mask = Image.new("L", (_PIP_SIZE, _PIP_SIZE), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, _PIP_SIZE - 1, _PIP_SIZE - 1), fill=255)
        path = work_dir / "pip-mask.png"
        mask.save(path)
        return path

    def _build_thumbnail(self, screenshot_path: Path, first_name: Optional[str], output_path: Path) -> None:
        """
        Build the personalised email thumbnail: site screenshot, slight
        darkening, centered play button, « Bonjour {Prénom} » pill.

        The thumbnail is THE click lever in the inbox — it must read as a
        video (play button) and as personal (his site + his first name).
        """
        from PIL import Image, ImageDraw, ImageEnhance

        thumb_w, thumb_h = 640, 360
        image = Image.open(screenshot_path).convert("RGB").resize((thumb_w, thumb_h))
        image = ImageEnhance.Brightness(image).enhance(0.82)

        overlay = Image.new("RGBA", (thumb_w, thumb_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Bouton play central (cercle blanc, triangle sombre).
        radius = 46
        cx, cy = thumb_w // 2, thumb_h // 2
        draw.ellipse(
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=(255, 255, 255, 235),
        )
        tri = 20
        draw.polygon(
            [(cx - tri // 2 + 3, cy - tri), (cx - tri // 2 + 3, cy + tri), (cx + tri + 3 - tri // 2, cy)],
            fill=(17, 17, 17, 255),
        )

        # Pill de salutation en haut à gauche.
        text = f"Bonjour {first_name} — votre site en vidéo" if first_name else "Votre site en vidéo"
        font = self._load_font(22)
        text_box = draw.textbbox((0, 0), text, font=font)
        text_w = text_box[2] - text_box[0]
        text_h = text_box[3] - text_box[1]
        pad_x, pad_y = 16, 10
        x0, y0 = 16, 16
        draw.rounded_rectangle(
            (x0, y0, x0 + text_w + pad_x * 2, y0 + text_h + pad_y * 2),
            radius=(text_h + pad_y * 2) // 2,
            fill=(255, 255, 255, 235),
        )
        draw.text(
            (x0 + pad_x - text_box[0], y0 + pad_y - text_box[1]),
            text,
            font=font,
            fill=(17, 17, 17, 255),
        )

        composed = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        composed.save(output_path, format="JPEG", quality=85)

    async def _compose(
        self,
        *,
        presenter: PresenterVideo,
        capture_path: Path,
        scroll_offset: float,
        scroll_seconds: float,
        greeting_path: Path,
        mask_path: Path,
        output_path: Path,
    ) -> None:
        """
        Single-pass ffmpeg composition.

        Base = presenter clip (full canvas, carries the audio). The site
        capture covers it between intro and D-outro, with the webcam shrunk
        to a circular PiP bubble; the greeting pill fades in/out during the
        intro.

        @throws DemoVideoGenerationError when ffmpeg fails.
        """
        duration = presenter.duration_seconds
        intro = presenter.intro_seconds
        site_end = duration - presenter.outro_seconds
        fade_out_start = max(intro - 0.5, 0.4)

        # NB filtergraph : à l'intérieur de quotes simples, PAS d'échappement —
        # les virgules de between()/min() y sont littérales et valides.
        filter_complex = (
            f"[0:v]scale={_WIDTH}:{_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={_WIDTH}:{_HEIGHT},setsar=1,fps={_FPS},split=2[pres_full][pip_src];"
            f"[1:v]scale={_WIDTH}:{_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={_WIDTH}:{_HEIGHT},setsar=1,fps={_FPS},setpts=PTS+{intro:.3f}/TB[site];"
            f"[pip_src]crop='min(iw,ih)':'min(iw,ih)',scale={_PIP_SIZE}:{_PIP_SIZE},format=rgba[pip_sq];"
            f"[3:v]format=gray[pip_mask];"
            f"[pip_sq][pip_mask]alphamerge[pip];"
            f"[pres_full][site]overlay=0:0:eof_action=pass:"
            f"enable='between(t,{intro:.3f},{site_end:.3f})'[with_site];"
            f"[with_site][pip]overlay={_PIP_MARGIN}:H-h-{_PIP_MARGIN}:eof_action=pass:"
            f"enable='between(t,{intro:.3f},{site_end:.3f})'[with_pip];"
            f"[2:v]format=rgba,fade=in:st=0.3:d=0.4:alpha=1,"
            f"fade=out:st={fade_out_start:.3f}:d=0.5:alpha=1[greeting];"
            f"[with_pip][greeting]overlay=0:0:eof_action=pass:"
            f"enable='between(t,0,{intro:.3f})'[vout]"
        )

        command = [
            settings.ffmpeg_path,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(presenter.file_path),
            "-ss",
            f"{max(scroll_offset, 0):.3f}",
            "-t",
            f"{scroll_seconds + 0.5:.3f}",
            "-i",
            str(capture_path),
            "-loop",
            "1",
            "-t",
            f"{intro + 1:.3f}",
            "-i",
            str(greeting_path),
            "-loop",
            "1",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(mask_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "0:a?",
            "-t",
            f"{duration:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "22",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(process.communicate(), timeout=600)
        except FileNotFoundError as exc:
            raise DemoVideoGenerationError(
                f"ffmpeg introuvable ({settings.ffmpeg_path}). Installez-le ou configurez FFMPEG_PATH."
            ) from exc
        except asyncio.TimeoutError as exc:
            raise DemoVideoGenerationError("Montage ffmpeg trop long (timeout 10 min).") from exc

        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()[-500:]
            raise DemoVideoGenerationError(f"Échec du montage ffmpeg : {detail}")
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise DemoVideoGenerationError("Le montage ffmpeg n'a produit aucun fichier.")


demo_video_service = DemoVideoService()
