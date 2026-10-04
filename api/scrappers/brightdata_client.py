"""
Bright Data Web Unlocker client — the single place that talks to Bright Data.

Owns the credentials (token / zone) and the one HTTP call to the Web Unlocker API,
plus helpers for Google result pages. Every Bright Data access in the codebase goes
through this class so the auth and endpoint live in one spot: the prospect search
(:mod:`services.prospect_search`) reads Google's local and web results through it.

Pure async HTTP (no browser), so it runs on the datacenter VPS as well as the desktop.
Each instance counts the requests it spends (``request_count``), which is what a
search's cost is computed from.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import quote_plus

import aiohttp

logger = logging.getLogger(__name__)

# Bright Data Web Unlocker API endpoint.
_BRIGHTDATA_REQUEST_URL: str = "https://api.brightdata.com/request"

# A search page fails now and then for no lasting reason: one more try settles most of them.
_PARSED_SEARCH_ATTEMPTS: int = 3
_PARSED_SEARCH_RETRY_PAUSE_SECONDS: float = 1.5


class BrightDataClient:
    """Fetch any URL — and Google / Bing SERPs — via the Bright Data Web Unlocker API."""

    def __init__(self) -> None:
        """Load the Bright Data token and zone from settings / environment."""
        self._token: str = self._load_token()
        self._zone: str = self._load_zone()
        self.request_count: int = 0

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
        self.request_count += 1
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

    @staticmethod
    def google_search_url(query: str, *, country: str = "FR", start: int = 0, local: bool = False) -> str:
        """Build a Google results URL ranked for *country*, in French.

        Args:
            query: Raw search query.
            country: Ranking country (``gl=``).
            start: Result offset (10 per web page, 20 per local page).
            local: Ask for the local results (« Lieux ») instead of the web results.

        Returns:
            The search URL.
        """
        url = f"https://www.google.com/search?q={quote_plus(query)}&gl={country.lower()}&hl=fr"
        if local:
            url += "&udm=local"
        else:
            url += "&num=10"
        if start > 0:
            url += f"&start={start}"
        return url

    async def google_parsed(
        self, query: str, *, country: str = "FR", start: int = 0, local: bool = False
    ) -> dict[str, Any] | None:
        """Fetch a Google results page already parsed into JSON by Bright Data.

        The web page carries ``organic`` (link, title, description) and, when Google
        recognises a business, ``knowledge`` (phone, address, ``site``, rating…); the
        local page carries ``snack_pack``.

        Args:
            query: Raw search query.
            country: Ranking country.
            start: Result offset.
            local: Ask for the local results instead of the web results.

        Returns:
            The parsed page, or ``None`` when every attempt failed.
        """
        url = self.google_search_url(query, country=country, start=start, local=local) + "&brd_json=1"
        for attempt in range(_PARSED_SEARCH_ATTEMPTS):
            try:
                parsed = json.loads(await self.fetch(url))
            except (TimeoutError, aiohttp.ClientError, json.JSONDecodeError) as exc:
                # An empty body (read as invalid JSON) is the usual failure: the next try answers.
                logger.info("[BrightData] parsed search failed (attempt %d) for '%s': %s", attempt + 1, query, exc)
                await asyncio.sleep(_PARSED_SEARCH_RETRY_PAUSE_SECONDS * (attempt + 1))
                continue
            if isinstance(parsed, dict):
                return parsed
        return None

    async def google_local_html(self, query: str, *, country: str = "FR", start: int = 0) -> str | None:
        """Fetch the raw HTML of a Google local results page (20 businesses per page).

        Args:
            query: Raw search query (« paysagiste Sion »).
            country: Ranking country.
            start: Result offset — page N starts at ``N * 20``.

        Returns:
            The page HTML, or ``None`` when the fetch failed.
        """
        try:
            return await self.fetch(self.google_search_url(query, country=country, start=start, local=True))
        except (TimeoutError, aiohttp.ClientError) as exc:
            logger.warning("[BrightData] local results failed for '%s' (start %d): %s", query, start, exc)
            return None
