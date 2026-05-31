"""
Shared nodriver browser session management for scrapers.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import nodriver as uc

    NODRIVER_AVAILABLE = True
except ImportError:
    uc = None  # type: ignore[assignment,misc]
    NODRIVER_AVAILABLE = False

HEADLESS_BROWSER_ARGS: list[str] = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-software-rasterizer",
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-breakpad",
    "--disable-component-extensions-with-background-pages",
    "--disable-features=TranslateUI",
    "--disable-ipc-flooding-protection",
    "--disable-renderer-backgrounding",
    "--force-color-profile=srgb",
    "--metrics-recording-only",
    "--mute-audio",
    "--no-first-run",
    "--password-store=basic",
    "--use-mock-keychain",
    "--window-size=1920,1080",
    "--js-flags=--max-old-space-size=512",
]

HEADED_BROWSER_ARGS: list[str] = [
    "--no-sandbox",
    "--disable-blink-features=AutomationControlled",
    "--disable-features=IsolateOrigins,site-per-process",
    "--start-maximized",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-session-crashed-bubble",
    "--disable-dev-shm-usage",
]

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => false,
});
"""


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def resolve_scraper_headless() -> bool:
    """Whether Chrome runs headless (default: visible window)."""
    try:
        from core.config import settings

        return settings.scraper_browser_headless
    except Exception:  # noqa: BLE001
        return _env_bool("SCRAPER_BROWSER_HEADLESS", default=False)


def should_keep_browser_open() -> bool:
    """When True, ``close()`` does not stop Chrome (debug / manual inspection)."""
    try:
        from core.config import settings

        return settings.scraper_browser_keep_open
    except Exception:  # noqa: BLE001
        return _env_bool("SCRAPER_BROWSER_KEEP_OPEN", default=False)


def resolve_scraper_user_data_dir(*, ephemeral: bool = False) -> Optional[str]:
    """
    Persistent Chrome profile directory.

    Only used when ``SCRAPER_USER_DATA_DIR`` is set explicitly — avoids profile
    locks when multiple Chrome sessions run during a scrape.
    """
    if ephemeral:
        return None

    try:
        from core.config import settings

        if settings.scraper_user_data_dir:
            return settings.scraper_user_data_dir.strip()
    except Exception:  # noqa: BLE001
        pass

    explicit = (os.environ.get("SCRAPER_USER_DATA_DIR") or "").strip()
    return explicit or None


def build_browser_args(*, headless: bool) -> list[str]:
    """Chromium flags tuned for headless vs visible scraping."""
    return list(HEADLESS_BROWSER_ARGS if headless else HEADED_BROWSER_ARGS)


async def activate_tab(tab: Any) -> None:
    """Bring the scraping tab to the foreground (visible Chrome)."""
    try:
        await tab.activate()
    except Exception as exc:  # noqa: BLE001
        logger.debug("tab.activate failed: %s", exc)


class NodriverBrowser:
    """
    Manages a single Chrome instance via nodriver.

    Use ``ephemeral=True`` for short-lived secondary sessions (email lookup)
    so the main scraper profile is not locked by two Chrome processes.
    """

    def __init__(self, *, headless: Optional[bool] = None, ephemeral: bool = False) -> None:
        self.headless = resolve_scraper_headless() if headless is None else headless
        self.ephemeral = ephemeral
        self._browser: Any = None

    def _chrome_executable(self) -> Optional[str]:
        chrome_executable = (os.environ.get("SCRAPER_CHROME_EXECUTABLE") or "").strip() or None
        try:
            from core.config import settings

            if settings.scraper_chrome_executable:
                chrome_executable = settings.scraper_chrome_executable.strip()
        except Exception:  # noqa: BLE001
            pass
        return chrome_executable

    def _start_kwargs(self, user_data_dir: Optional[str]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "headless": self.headless,
            "browser_args": build_browser_args(headless=self.headless),
            "sandbox": False,
        }
        exe = self._chrome_executable()
        if exe:
            kwargs["browser_executable_path"] = exe
        if user_data_dir:
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)
            kwargs["user_data_dir"] = user_data_dir
        return kwargs

    async def ensure_browser(self) -> Any:
        """Start Chrome if not already running."""
        if not NODRIVER_AVAILABLE:
            raise RuntimeError(
                "nodriver is not installed. Install it with: pip install nodriver"
            )

        browser = self._browser
        if browser is not None and not getattr(browser, "stopped", False):
            return browser

        primary_profile = resolve_scraper_user_data_dir(ephemeral=self.ephemeral)
        attempts: list[Optional[str]] = [primary_profile]
        if primary_profile and not self.ephemeral:
            attempts.append(None)

        last_exc: Exception | None = None
        mode = "headless" if self.headless else "visible"

        for idx, profile_dir in enumerate(attempts):
            profile_label = profile_dir or "ephemeral"
            logger.info(
                "Starting Chrome via nodriver (%s, %s profile, attempt %s/%s)",
                mode,
                profile_label,
                idx + 1,
                len(attempts),
            )
            try:
                self._browser = await uc.start(**self._start_kwargs(profile_dir))
                return self._browser
            except Exception as exc:
                last_exc = exc
                logger.warning("Chrome start failed (%s): %s", profile_label, exc)
                self._browser = None

        raise RuntimeError(
            "Failed to start Chrome via nodriver. "
            "Close any leftover Chrome window, or set SCRAPER_CHROME_EXECUTABLE."
        ) from last_exc

    async def get_tab(self, url: Optional[str] = None) -> Any:
        """Open a tab, optionally navigating to ``url``."""
        browser = await self.ensure_browser()
        if url:
            tab = await browser.get(url)
            await tab
            await asyncio.sleep(0.5)
            await self._apply_stealth(tab)
            if not self.headless:
                await activate_tab(tab)
            return tab
        tab = await browser.get("about:blank")
        await tab
        await self._apply_stealth(tab)
        return tab

    @staticmethod
    async def _apply_stealth(tab: Any) -> None:
        try:
            await tab.evaluate(STEALTH_INIT_SCRIPT, return_by_value=False)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Stealth init script failed: %s", exc)

    async def close(self) -> None:
        """Stop Chrome and reset session state."""
        browser = self._browser
        if browser is None:
            return

        if should_keep_browser_open() and not self.ephemeral:
            logger.info(
                "SCRAPER_BROWSER_KEEP_OPEN=1 — Chrome left open for manual inspection"
            )
            self._browser = None
            return

        if not self.headless and not self.ephemeral:
            pause_s = 2.5
            try:
                from core.config import settings

                pause_s = float(settings.scraper_browser_close_delay_sec)
            except Exception:  # noqa: BLE001
                pause_s = float(os.environ.get("SCRAPER_BROWSER_CLOSE_DELAY_SEC", "2.5"))
            if pause_s > 0:
                await asyncio.sleep(pause_s)

        pid: Optional[int] = None
        try:
            proc = getattr(browser, "_process", None)
            if proc is not None:
                pid = getattr(proc, "pid", None)
        except Exception:  # noqa: BLE001
            pid = None

        try:
            if not getattr(browser, "stopped", True):
                await asyncio.sleep(0.3)
                browser.stop()
        except Exception as exc:  # noqa: BLE001
            logger.warning("nodriver browser.stop() failed: %s", exc)
        finally:
            self._browser = None

        if sys.platform == "win32" and pid and not getattr(browser, "stopped", True):
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    timeout=12,
                    check=False,
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("taskkill after nodriver stop: %s", exc)


class NodriverScraperMixin:
    """Mixin that adds nodriver browser lifecycle to scrapers."""

    _nodriver: NodriverBrowser

    def _init_nodriver(self) -> None:
        self._nodriver = NodriverBrowser()

    async def ensure_browser(self) -> Any:
        return await self._nodriver.ensure_browser()

    async def close(self) -> None:
        await self._nodriver.close()
