"""
Website liveness classification for scraped prospect URLs.

A URL on a Google Maps / PagesJaunes listing does not mean the business has a
working website: Google closed every ``business.site`` in March 2024, Solocal
mini-sites die with the subscription, domains expire. Those prospects used to be
excluded by the "no website" filter while being the best possible targets — they
already paid for a website once. This service tells the scrapers which URLs
actually respond.
"""

from __future__ import annotations

import logging
from typing import ClassVar
from urllib.parse import urlparse

import httpx

from enums.website_status import WebsiteStatus

logger = logging.getLogger(__name__)


class WebsiteLivenessService:
    """
    Classifies a scraped website URL as live, dead, or a directory placeholder.

    Results are cached per URL for the lifetime of the process: the same
    business often appears in several scraper sources during one job, and the
    verdict for a URL does not change mid-scrape.
    """

    REQUEST_TIMEOUT_SECONDS = 8.0
    MAX_CACHED_URLS = 2048
    BODY_SNIFF_CHARS = 20_000

    # Directory mini-site hosts — "not a real website" even when they respond.
    PLACEHOLDER_HOSTS: frozenset[str] = frozenset(
        {
            "business.site",
            "site-solocal.com",
            "solocal.com",
            "wixsite.com",
            "pagesjaunes.fr",
        }
    )

    # Lowercase markers of hosting error pages that answer 200 for a dead site.
    DEAD_PAGE_MARKERS: tuple[str, ...] = (
        "site not found",
        "account suspended",
        "site suspendu",
        "this domain is for sale",
        "buy this domain",
        "domain has expired",
        "ce domaine est à vendre",
        "ce nom de domaine a expiré",
    )

    # Statuses that prove the page is gone. Other 4xx (401/403/429…) usually
    # mean bot protection on a perfectly working site — never call those dead.
    DEAD_HTTP_STATUSES: frozenset[int] = frozenset({404, 410})

    # A browser-like UA: default python UAs get blocked by common WAFs, which
    # would look like a dead site.
    REQUEST_HEADERS: ClassVar[dict[str, str]] = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
    }

    def __init__(self) -> None:
        self._status_by_url: dict[str, WebsiteStatus] = {}

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize a scraped URL so it can be fetched and cached consistently.

        Args:
            url: Raw URL from a scraper (may lack a scheme, e.g. OSM tags).

        Returns:
            The URL with a scheme, stripped of surrounding whitespace.
        """
        cleaned = url.strip()
        if "://" not in cleaned:
            cleaned = f"https://{cleaned}"
        return cleaned

    @classmethod
    def is_placeholder_host(cls, url: str) -> bool:
        """
        Check whether a URL lives on a directory mini-site host.

        Args:
            url: Normalized website URL.

        Returns:
            True when the host is (or is a subdomain of) a placeholder host.
        """
        host = (urlparse(cls.normalize_url(url)).hostname or "").lower()
        return any(host == candidate or host.endswith(f".{candidate}") for candidate in cls.PLACEHOLDER_HOSTS)

    async def check_website_status(self, website: str | None) -> WebsiteStatus | None:
        """
        Classify a scraped website URL.

        The verdict errs on the side of LIVE: only definitive signals (DNS
        failure, connection refused, 404/410/5xx, hosting error page) mark a
        site dead. An inconclusive probe (timeout, odd 4xx) is treated as live
        so a prospect is never pitched "your site is down" by mistake.

        Args:
            website: Raw URL found by a scraper, or None when nothing was found.

        Returns:
            The classification, or None when no URL was given.
        """
        if not website or not website.strip():
            return None

        normalized = self.normalize_url(website)
        cached = self._status_by_url.get(normalized)
        if cached is not None:
            return cached

        status = await self._probe(normalized)
        if status is not WebsiteStatus.DEAD and self.is_placeholder_host(normalized):
            status = WebsiteStatus.PLACEHOLDER

        if status is not WebsiteStatus.LIVE:
            logger.info("Website %s classified as %s", normalized, status.value)

        if len(self._status_by_url) >= self.MAX_CACHED_URLS:
            self._status_by_url.clear()
        self._status_by_url[normalized] = status
        return status

    async def _probe(self, url: str) -> WebsiteStatus:
        """
        Fetch the URL and classify the response.

        Args:
            url: Normalized website URL.

        Returns:
            DEAD on definitive failure signals, LIVE otherwise.
        """
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
                headers=self.REQUEST_HEADERS,
            ) as client:
                response = await client.get(url)
        except (httpx.ConnectError, httpx.TooManyRedirects) as exc:
            # DNS failure, connection refused, TLS breakage, redirect loop —
            # a visitor cannot reach the site either.
            logger.info("Website %s unreachable: %s", url, exc)
            return WebsiteStatus.DEAD
        except httpx.HTTPError as exc:
            # Timeouts and protocol quirks are not proof of death.
            logger.debug("Website %s probe inconclusive: %s", url, exc)
            return WebsiteStatus.LIVE

        if response.status_code in self.DEAD_HTTP_STATUSES or response.status_code >= 500:
            return WebsiteStatus.DEAD

        body_start = response.text[: self.BODY_SNIFF_CHARS].lower()
        if any(marker in body_start for marker in self.DEAD_PAGE_MARKERS):
            return WebsiteStatus.DEAD

        return WebsiteStatus.LIVE


# Global service instance
website_liveness_service = WebsiteLivenessService()
