"""
Render the prospection-video *background*: a linear site scroll followed by a
real Storyblok Visual Editor click-to-edit sequence, on the prospect's own site.

This is the desktop-only half of the video pipeline: it needs the owner's
Storyblok session (see ``storyblok_session_service``), which lives on the user's
machine, so it runs in the sidecar — never on the VPS. The VPS montage later
overlays the webcam PiP bubble and the « Bonjour {Prénom} » pill on top.

Reproducing exactly the render Léo validated (v9):
  - the site scroll is rendered frame-by-frame at a constant pixel step and
    assembled at a fixed fps → rigorously constant velocity (Playwright's own
    video recorder is variable-rate and made the end « rush »);
  - the editor sequence uses click-to-edit with a visible cursor, edits the hero
    text and replaces the hero photo, then **reverts** both (we never publish, so
    the live site is untouched, and the revert keeps the client's draft clean).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from services.storyblok_session_service import StoryblokSessionSeed

logger = logging.getLogger(__name__)

# Editor capture runs at 1600x900 (where the panel/library coordinates are
# calibrated), then the whole background is scaled to the pipeline size.
_EDIT_W, _EDIT_H = 1600, 900

# Neutral fallback only: the real, trade-aware phrase is passed in per site (the API
# sends the template's default subtitle), so a landscaper never gets a barber line.
_DEMO_ACCROCHE = "Votre activité, présentée comme il se doit."

# A visible fake cursor injected into the editor page (Playwright records no OS
# cursor). We drive its position ourselves, so it glides where we click.
_CURSOR_INIT = """() => {
  if (window.__curInstalled) return; window.__curInstalled = true;
  const c = document.createElement('div'); c.id='__cur';
  c.style.cssText='position:fixed;z-index:2147483647;left:-80px;top:-80px;width:26px;height:26px;pointer-events:none;transition:left .09s linear, top .09s linear;filter:drop-shadow(0 1px 2px rgba(0,0,0,.5));';
  c.innerHTML='<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2 L4 21 L9.2 15.8 L12.4 22.5 L15.4 21.2 L12.2 14.6 L19.5 14.6 Z" fill="#111" stroke="#fff" stroke-width="1.4"/></svg>';
  const add=()=>{ if(document.body && !document.getElementById('__cur')) document.body.appendChild(c); };
  if(document.body) add(); else document.addEventListener('DOMContentLoaded', add);
  window.__moveCur=(x,y)=>{ if(!c.isConnected && document.body) document.body.appendChild(c); c.style.left=(x-2)+'px'; c.style.top=(y-2)+'px'; };
}"""


class StoryblokEditorClipError(Exception):
    """Raised when the background clip cannot be produced."""


class _FrameCapturer:
    """Screenshot the editor into a numbered sequence — our own recorder.

    Playwright's ``record_video`` needs Playwright's bundled ffmpeg, which the
    packaged sidecar has no copy of; grabbing frames + assembling them with the
    system ffmpeg keeps the editor sequence working in the frozen binary.
    """

    def __init__(self, page, frames_dir: Path, fps: int) -> None:
        self._page = page
        self._dir = frames_dir
        self._fps = fps
        self._index = 0

    def shot(self) -> None:
        """Capture one frame of the current editor state."""
        self._page.screenshot(path=str(self._dir / f"f{self._index:05d}.png"))
        self._index += 1

    def hold(self, milliseconds: int) -> None:
        """Capture frames for ``milliseconds`` at the target fps (replaces a wait)."""
        frames = max(1, round(milliseconds / 1000 * self._fps))
        interval = max(1, round(milliseconds / frames))
        for _ in range(frames):
            self.shot()
            self._page.wait_for_timeout(interval)


class _Cursor:
    """A self-positioned on-screen cursor that also moves the real Playwright mouse."""

    def __init__(self, page, capturer: _FrameCapturer) -> None:
        self._page = page
        self._cap = capturer
        self.x, self.y = 800, 460

    def move(self, x: float, y: float, steps: int = 6, delay: int = 15) -> None:
        """Glide the cursor (and the mouse) to (x, y), capturing frames as it goes."""
        for i in range(1, steps + 1):
            ix, iy = self.x + (x - self.x) * i / steps, self.y + (y - self.y) * i / steps
            self._page.evaluate("([x,y]) => window.__moveCur && window.__moveCur(x,y)", [ix, iy])
            self._page.mouse.move(ix, iy)
            self._cap.hold(delay)
        self.x, self.y = x, y

    def click(self, x: float, y: float, settle: int = 150) -> None:
        """Glide to (x, y), pause so the move reads on screen, then click."""
        self.move(x, y)
        self._cap.hold(settle)
        self._page.mouse.click(x, y)
        self._cap.shot()


class StoryblokEditorClipService:
    """Produce the video background (site scroll + Storyblok editor) for a prospect."""

    def __init__(self, ffmpeg_path: str | None = None) -> None:
        self._ffmpeg = ffmpeg_path or os.environ.get("FFMPEG_PATH") or "ffmpeg"

    def build_background(
        self,
        *,
        demo_url: str,
        space_id: str,
        story_id: str,
        output_path: Path,
        seed: StoryblokSessionSeed | None = None,
        user_data_dir: str | None = None,
        accroche: str = "",
        executable_path: str | None = None,
        site_seconds: float = 14.0,
        hold_seconds: float = 1.0,
        total_seconds: float | None = None,
        out_width: int = 1280,
        out_height: int = 720,
        fps: int = 30,
        on_progress: Callable[[str], None] | None = None,
    ) -> Path:
        """Render the background clip to ``output_path`` and return it.

        Either ``seed`` (a machine session to inject) or ``user_data_dir`` (a
        dedicated persistent profile) must let us reach the authenticated editor.
        ``on_progress`` (when given) is called with the phase starting:
        ``site_capture`` / ``editor_capture`` / ``background_assemble``.

        Raises:
            StoryblokEditorClipError: when Playwright is missing or the editor
                cannot be reached / captured.
        """
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError as exc:  # pragma: no cover — dependency guard
            raise StoryblokEditorClipError("Playwright n'est pas installé.") from exc

        work_dir = Path(tempfile.mkdtemp(prefix="sb-editor-clip-"))
        try:
            if on_progress:
                on_progress("site_capture")
            site_clip = self._render_site_segment(demo_url, site_seconds, hold_seconds, fps, work_dir, executable_path)
            if on_progress:
                on_progress("editor_capture")
            editor_clip = self._record_editor_segment(
                space_id, story_id, seed, user_data_dir, fps, work_dir, executable_path, accroche
            )
            if on_progress:
                on_progress("background_assemble")
            return self._concat(site_clip, editor_clip, output_path, out_width, out_height, fps, total_seconds)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    # ── Site scroll: frame sequence → constant velocity ──────────────────────

    def _render_site_segment(
        self,
        demo_url: str,
        site_seconds: float,
        hold_seconds: float,
        fps: int,
        work_dir: Path,
        executable_path: str | None = None,
    ) -> Path:
        """Capture the site as an equal-step frame sequence and assemble it."""
        from playwright.sync_api import sync_playwright

        frames_dir = work_dir / "site_frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, executable_path=executable_path)
                context = browser.new_context(viewport={"width": _EDIT_W, "height": _EDIT_H})
                page = context.new_page()
                # ?internal=1 flags this as the owner's own visit → no prospect
                # notifications / tracking events fire during the capture.
                page.goto(self._as_internal_url(demo_url), wait_until="load", timeout=45000)
                page.evaluate(
                    "() => document.querySelectorAll('img').forEach(i => { i.loading='eager'; i.decoding='sync'; })"
                )
                page.wait_for_timeout(600)
                # Pre-pass: force every lazy asset (incl. the bottom map) so heights are final.
                pre = page.evaluate("Math.max(0, document.documentElement.scrollHeight - window.innerHeight)")
                for k in range(10):
                    page.evaluate("y => window.scrollTo(0, y)", pre * (k + 1) / 10)
                    page.wait_for_timeout(200)
                page.wait_for_timeout(1500)
                page.evaluate("() => window.scrollTo(0, 0)")
                page.wait_for_timeout(600)

                max_y = page.evaluate("Math.max(0, document.documentElement.scrollHeight - window.innerHeight)")
                n = max(1, int(fps * site_seconds))
                index = 0
                for i in range(0, n + 1):
                    page.evaluate("y => window.scrollTo(0, y)", max_y * i / n)
                    page.wait_for_timeout(12)
                    page.screenshot(path=str(frames_dir / f"f{index:05d}.png"))
                    index += 1
                for _ in range(int(fps * hold_seconds)):
                    page.screenshot(path=str(frames_dir / f"f{index:05d}.png"))
                    index += 1
                context.close()
                browser.close()
        except Exception as exc:
            raise StoryblokEditorClipError(f"Capture du site échouée ({demo_url}) : {exc}") from exc

        out = work_dir / "site.mp4"
        self._run_ffmpeg(
            [
                "-framerate",
                str(fps),
                "-i",
                str(frames_dir / "f%05d.png"),
                *self._enc(fps),
                "-vf",
                f"scale={_EDIT_W}:{_EDIT_H}",
                str(out),
            ]
        )
        return out

    # ── Editor sequence: click-to-edit + revert ──────────────────────────────

    def _record_editor_segment(
        self,
        space_id: str,
        story_id: str,
        seed: StoryblokSessionSeed | None,
        user_data_dir: str | None,
        fps: int,
        work_dir: Path,
        executable_path: str | None = None,
        accroche: str = "",
    ) -> Path:
        """Capture the authenticated editor edit as a frame sequence (no Playwright video)."""
        from playwright.sync_api import sync_playwright

        frames_dir = work_dir / "editor_frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        editor_url = f"https://app.storyblok.com/#/me/spaces/{space_id}/stories/0/0/{story_id}"
        context_kwargs = {"viewport": {"width": _EDIT_W, "height": _EDIT_H}}
        try:
            with sync_playwright() as playwright:
                if seed is None and user_data_dir:
                    # Dedicated persistent profile (GoupixDex fallback): localStorage
                    # already holds the session, nothing to inject.
                    context = playwright.chromium.launch_persistent_context(
                        user_data_dir, headless=False, executable_path=executable_path, **context_kwargs
                    )
                    browser = None
                    page = context.pages[0] if context.pages else context.new_page()
                else:
                    browser = playwright.chromium.launch(headless=False, executable_path=executable_path)
                    context = browser.new_context(**context_kwargs)
                    if seed is not None:
                        if seed.cookies:
                            context.add_cookies(seed.cookies)
                        context.add_init_script(script=self._seed_script(seed.local_storage))
                    page = context.new_page()
                context.add_init_script(script=_CURSOR_INIT)

                if not self._open_editor(page, editor_url):
                    raise StoryblokEditorClipError("Éditeur Storyblok inaccessible (session invalide ?).")
                page.evaluate(_CURSOR_INIT)
                # Capture starts only now → the loading screen is never in the clip.
                capturer = _FrameCapturer(page, frames_dir, fps)
                self._drive_edit_and_revert(page, capturer, accroche)

                context.close()
                if browser is not None:
                    browser.close()
        except StoryblokEditorClipError:
            raise
        except Exception as exc:
            raise StoryblokEditorClipError(f"Capture de l'éditeur échouée : {exc}") from exc

        if not any(frames_dir.iterdir()):
            raise StoryblokEditorClipError("Aucune image d'éditeur capturée.")
        out = work_dir / "editor.mp4"
        self._run_ffmpeg(
            [
                "-framerate",
                str(fps),
                "-i",
                str(frames_dir / "f%05d.png"),
                *self._enc(fps),
                "-vf",
                f"scale={_EDIT_W}:{_EDIT_H}",
                str(out),
            ]
        )
        return out

    def _drive_edit_and_revert(self, page, capturer: _FrameCapturer, accroche: str = "") -> None:
        """Click-to-edit the hero text + photo (with a visible cursor), capturing frames, then revert."""
        new_accroche = accroche.strip() or _DEMO_ACCROCHE
        cursor = _Cursor(page, capturer)
        capturer.hold(700)
        frame = self._preview_frame(page)
        if frame is None:
            raise StoryblokEditorClipError("Preview du site introuvable dans l'éditeur.")

        # 1) hero title -> En-tête opens -> edit the hero line
        heading = frame.locator("h1, h2").first.bounding_box()
        cursor.click(heading["x"] + heading["width"] / 2, heading["y"] + heading["height"] / 2)
        capturer.hold(1300)
        accroche = page.get_by_text("Phrase d'accroche").locator("xpath=following::textarea[1]")
        original_accroche = accroche.input_value()
        box = accroche.bounding_box()
        cursor.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        capturer.hold(250)
        accroche.press("Control+a")
        accroche.press("Delete")
        capturer.shot()
        for index, char in enumerate(new_accroche):
            accroche.type(char, delay=3)
            if index % 3 == 0:
                capturer.shot()
        accroche.press("Tab")
        capturer.hold(800)

        # 2) hero photo -> replace via the asset library
        thumb = self._panel_top_asset(page)
        if thumb:
            cursor.move(thumb["cx"], thumb["cy"])
            capturer.hold(300)
            cursor.click(thumb["cx"] + 146, thumb["cy"] - 25)  # Replace asset icon
            capturer.hold(1900)
            cursor.click(456, 324)  # a different photo from the library grid
            capturer.hold(1700)
        capturer.hold(1300)

        # Revert (never published, so the LIVE site is untouched; this keeps the
        # client's editor draft clean): undo the photo, restore the text verbatim.
        try:
            page.keyboard.press("Control+z")
            page.wait_for_timeout(500)
            accroche.fill(original_accroche)
        except Exception as exc:
            logger.debug("editor revert best-effort failed: %s", exc)

    # ── Small helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _as_internal_url(url: str) -> str:
        """Add ``internal=1`` so a capture visit is excluded from tracking/notifications."""
        parts = urlparse(url)
        query = dict(parse_qsl(parts.query))
        query["internal"] = "1"
        return urlunparse(parts._replace(query=urlencode(query)))

    @staticmethod
    def _seed_script(local_storage: dict[str, str]) -> str:
        """Init script that seeds the auth localStorage before Storyblok's SPA boots."""
        return (
            "(() => { try { const items = "
            + json.dumps(local_storage)
            + "; if (location.host === 'app.storyblok.com') { for (const k in items) localStorage.setItem(k, items[k]); } } catch (e) {} })();"
        )

    @staticmethod
    def _open_editor(page, editor_url: str) -> bool:
        """Load the Visual Editor and wait until the field panel + preview are up.

        Raises:
            StoryblokEditorClipError: prefixed ``needs_login:`` when Storyblok bounces
                us to its sign-in page (the session is expired/absent) — surfaced fast
                and distinctly so the caller prompts a reconnect instead of retrying.
        """
        page.goto(editor_url, wait_until="domcontentloaded")
        for _ in range(10):
            page.wait_for_timeout(2500)
            url = (page.url or "").lower()
            if "sign-in" in url or "/login" in url or page.locator("input[type=password]").count() > 0:
                raise StoryblokEditorClipError("needs_login: session Storyblok expirée ou absente — reconnecte-toi.")
            if page.locator("iframe").count() and page.locator("input").count():
                page.wait_for_timeout(2200)
                return True
        return False

    @staticmethod
    def _preview_frame(page):
        """The demo-site preview iframe inside the editor (matched by host)."""
        for candidate in page.frames:
            if "dibodev" in (candidate.url or ""):
                return candidate
        return None

    @staticmethod
    def _panel_top_asset(page):
        """Center of the top-most Storyblok asset thumbnail in the right-hand panel."""
        return page.evaluate(
            """() => { const imgs=[...document.querySelectorAll('img')].filter(i=>{const r=i.getBoundingClientRect(); return r.x>1150 && r.width>60 && r.height>40 && (i.src||'').includes('a.storyblok');}); if(!imgs.length) return null; imgs.sort((a,b)=>a.getBoundingClientRect().y-b.getBoundingClientRect().y); const r=imgs[0].getBoundingClientRect(); return {cx:Math.round(r.x+r.width/2), cy:Math.round(r.y+r.height/2)}; }"""
        )

    def _concat(
        self,
        site_clip: Path,
        editor_clip: Path,
        output_path: Path,
        out_width: int,
        out_height: int,
        fps: int,
        total_seconds: float | None,
    ) -> Path:
        """Concatenate the segments, fit to ``total_seconds`` if given, scale to output.

        When a total is requested the background is trimmed (if longer) or its last
        frame is frozen (if shorter) so it matches the webcam clip's timeline exactly.
        """
        work_dir = site_clip.parent
        listing = work_dir / "concat.txt"
        listing.write_text(f"file '{site_clip}'\nfile '{editor_clip}'\n", encoding="utf-8")
        merged = work_dir / "merged.mp4"
        self._run_ffmpeg(["-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(merged)])

        video_filter = f"scale={out_width}:{out_height}"
        fit_args: list[str] = []
        if total_seconds and total_seconds > 0:
            duration = self._probe_duration(merged)
            if duration > total_seconds + 0.05:
                fit_args = ["-t", f"{total_seconds:.2f}"]
            elif duration + 0.05 < total_seconds:
                video_filter = f"tpad=stop_mode=clone:stop_duration={total_seconds - duration:.2f},{video_filter}"
        self._run_ffmpeg(["-i", str(merged), *fit_args, *self._enc(fps), "-vf", video_filter, str(output_path)])
        return output_path

    def _probe_duration(self, path: Path) -> float:
        """Return the media duration in seconds (0.0 when it cannot be read).

        Raises:
            StoryblokEditorClipError: when no ffprobe executable exists — a silent
                0.0 there would pad the background to the wrong length.
        """
        ffmpeg = Path(self._ffmpeg)
        probe = str(ffmpeg.with_name(ffmpeg.name.replace("ffmpeg", "ffprobe"))) if ffmpeg.name else "ffprobe"
        # The frozen sidecar bundles ffprobe next to ffmpeg; when the derived path
        # does not exist (dev machine, partial bundle), fall back to the PATH one.
        if probe != "ffprobe" and not Path(probe).is_file():
            probe = "ffprobe"
        try:
            result = subprocess.run(
                [probe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise StoryblokEditorClipError(
                "ffprobe introuvable à côté de ffmpeg — impossible de caler la durée du fond."
            ) from exc
        try:
            return float(result.stdout.strip())
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _enc(fps: int) -> list[str]:
        """Shared x264 encode flags."""
        return ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-r", str(fps)]

    def _run_ffmpeg(self, args: list[str]) -> None:
        """Run ffmpeg with ``-y``, raising a clear error on failure."""
        result = subprocess.run([self._ffmpeg, "-y", *args], capture_output=True, text=True)
        if result.returncode != 0:
            raise StoryblokEditorClipError(f"ffmpeg a échoué : {result.stderr[-400:]}")


storyblok_editor_clip_service = StoryblokEditorClipService()
