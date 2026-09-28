"""How every browser capture of a prospection video opens its page, on the VPS and in the desktop sidecar."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

_NAVIGATION_TIMEOUT_MS = 45000


class CapturePage:
    """The page a video capture films: its address and its loading."""

    @staticmethod
    def internal_url(url: str) -> str:
        """
        Tag a page address as the owner's own visit (``internal=1``): a capture never notifies nor counts as a prospect.

        Args:
            url: The page to capture.

        Returns:
            The same address with ``internal=1`` in its query.
        """
        parts = urlparse(url)
        query = dict(parse_qsl(parts.query))
        query["internal"] = "1"
        return urlunparse(parts._replace(query=urlencode(query)))

    @staticmethod
    def open(page: Any, url: str, timeout_ms: int = _NAVIGATION_TIMEOUT_MS) -> None:
        """
        Load a page and wait until its network is idle, or only until it has loaded when it keeps polling.

        Args:
            page: A Playwright (sync) page.
            url: The address to load.
            timeout_ms: How long each attempt may take.
        """
        try:
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
        except Exception:
            page.goto(url, wait_until="load", timeout=timeout_ms)
