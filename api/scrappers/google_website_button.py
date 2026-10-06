"""
Google website button — where the « Site Web » button of a Google card leads.

Google hides the address behind its own redirect (« /goto?url=… »). Following that one
redirect gives the business's website, a directory page or a social page, without any
paid request: a search learns whether a card's button really shows a website before
it pays for a verification.
"""

from __future__ import annotations

import logging
from urllib.parse import urljoin, urlparse

import httpx

from services.website_liveness_service import website_liveness_service

logger = logging.getLogger(__name__)

_GOOGLE_ORIGIN: str = "https://www.google.com"
_TIMEOUT_SECONDS: float = 8.0


class GoogleWebsiteButton:
    """Follows the redirect behind the « Site Web » button of a Google card."""

    async def destination(self, link: str | None) -> str | None:
        """
        The address the button of a card leads to.

        Args:
            link: The button's link as the card gives it, a Google redirect or a plain address.

        Returns:
            The address, ``None`` when Google answers without redirecting, sends back to itself
            (a consent or rate-limit page) or does not answer.
        """
        if not link:
            return None
        url = urljoin(_GOOGLE_ORIGIN, link)
        if not self._is_google(url):
            return url
        try:
            async with httpx.AsyncClient(
                timeout=_TIMEOUT_SECONDS, follow_redirects=False, headers=website_liveness_service.REQUEST_HEADERS
            ) as http:
                response = await http.get(url)
        except httpx.HTTPError as exc:
            logger.info("Google website button %s did not answer: %s", link, exc)
            return None
        location = response.headers.get("location", "")
        if not response.is_redirect or not location.startswith(("http://", "https://")) or self._is_google(location):
            return None
        return location

    @staticmethod
    def _is_google(url: str) -> bool:
        """Whether an address belongs to Google itself (« www.google.ch », « consent.google.com »)."""
        return ".google." in f".{(urlparse(url).hostname or '').lower()}."


google_website_button = GoogleWebsiteButton()
