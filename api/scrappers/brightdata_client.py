"""
Bright Data Web Unlocker client — the single place that talks to Bright Data.

Owns the credentials (token / zone) and the one HTTP call to the Web Unlocker API,
plus convenience helpers for search-engine result pages. Every Bright Data access in
the codebase goes through this class so the auth and endpoint live in one spot:
:class:`~scrappers.brightdata_scraper.BrightDataScraper` (Pages Jaunes + Google email
search) and :class:`~scrappers.facebook_search_scraper.FacebookSearchScraper`
(``site:facebook.com`` discovery) both delegate here.

Pure async HTTP (no browser), so it runs on the datacenter VPS as well as the desktop.
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import aiohttp

logger = logging.getLogger(__name__)

# Bright Data Web Unlocker API endpoint.
_BRIGHTDATA_REQUEST_URL: str = "https://api.brightdata.com/request"


class BrightDataClient:
    """Fetch any URL — and Google / Bing SERPs — via the Bright Data Web Unlocker API."""

    def __init__(self) -> None:
        """Load the Bright Data token and zone from settings / environment."""
        self._token: str = self._load_token()
        self._zone: str = self._load_zone()

    @property
    def is_configured(self) -> bool:
        """Whether a Bright Data token is available (else fetches would fail).

        Returns:
            ``True`` when a non-empty token is loaded.
        """
        return bool(self._token)

    def reload_credentials(self) -> None:
        """Re-read the token / zone in case they changed since construction."""
        self._token = self._load_token()
        self._zone = self._load_zone()

    @staticmethod
    def _load_token() -> str:
        """Load the Bright Data API token from settings, falling back to the env.

        Returns:
            The token, or an empty string when not configured.
        """
        try:
            from core.config import settings  # local import — avoids circular deps

            return settings.brightdata_api_token or ""
        except Exception:
            import os

            return os.environ.get("BRIGHTDATA_API_TOKEN", "")

    @staticmethod
    def _load_zone() -> str:
        """Load the Bright Data zone name from settings, falling back to the env.

        Returns:
            The zone name, defaulting to ``"mcp_unlocker"``.
        """
        try:
            from core.config import settings

            return settings.brightdata_zone or "mcp_unlocker"
        except Exception:
            import os

            return os.environ.get("BRIGHTDATA_ZONE", "mcp_unlocker")

    async def fetch(self, url: str, *, zone: str | None = None) -> str:
        """Fetch *url* through the Web Unlocker and return the raw HTML.

        Args:
            url: Target URL to retrieve.
            zone: Bright Data zone override (defaults to the configured zone).

        Returns:
            Raw HTML of the response.

        Raises:
            aiohttp.ClientResponseError: When the API returns a non-2xx status.
            aiohttp.ClientError: On network-level failures.
        """
        payload: dict[str, str] = {"zone": zone or self._zone, "url": url, "format": "raw"}
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                _BRIGHTDATA_REQUEST_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=90),
            ) as resp,
        ):
            resp.raise_for_status()
            return await resp.text()

    async def google(self, query: str, *, num: int = 20, start: int = 0, country: str = "FR") -> str:
        """Fetch a Google results page for *query* (French language, country-ranked).

        Args:
            query: Raw search query (e.g. ``site:facebook.com "food truck" "Nantes"``).
            num: Number of results requested.
            start: Result offset — ``num`` per page, so page N is ``start=N*num``.
            country: Ranking country (``gl=``) — a Swiss search ranked with ``gl=fr``
                     buries the Swiss pages under French ones.

        Returns:
            Raw HTML of the Google SERP.
        """
        url = f"https://www.google.com/search?q={quote_plus(query)}&gl={country.lower()}&hl=fr&num={num}"
        if start > 0:
            url += f"&start={start}"
        return await self.fetch(url)

    async def bing(self, query: str, *, count: int = 20, first: int = 1, country: str = "FR") -> str:
        """Fetch a Bing results page for *query* (French language, country-ranked).

        Args:
            query: Raw search query.
            count: Number of results requested.
            first: 1-based offset of the first result — page N is ``first=N*count+1``.
            country: Ranking country (``cc=``).

        Returns:
            Raw HTML of the Bing SERP.
        """
        url = f"https://www.bing.com/search?q={quote_plus(query)}&cc={country.upper()}&setlang=fr&count={count}"
        if first > 1:
            url += f"&first={first}"
        return await self.fetch(url)
