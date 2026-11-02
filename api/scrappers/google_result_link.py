"""
Google result link — the address a result of a Google page leads to.

Google may hide a result's address behind its own redirect (« https://www.google.com/goto?url=… », an opaque
token): read as is, the result seems to sit on google.com and a business's own site goes unseen. The address
Google writes under the title (« https://exemple.fr › contact ») still names the site: the result is then read
as that site's front page, without any request.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

# Google's own redirects: « /goto?url=… » (an opaque token) and the older « /url?q=… ».
_REDIRECT_PATHS: frozenset[str] = frozenset({"/goto", "/url"})
_SHOWN_ADDRESS_SEPARATOR: str = "›"
_HOST_RE: re.Pattern[str] = re.compile(r"^[\w-]+(\.[\w-]+)+$")


class GoogleResultLink:
    """Reads where a Google result leads, Google's redirect set aside."""

    @classmethod
    def address_of(cls, result: dict[str, Any]) -> str:
        """
        The address a result of Bright Data's parsed page leads to.

        Args:
            result: One ``organic`` result: its ``link`` and the address shown under its title (``display_link``).

        Returns:
            Its link; the front page of the site shown under the title when the link is Google's redirect, the
            redirect itself when Google shows no site.
        """
        link = str(result.get("link") or "")
        if not cls._is_google_redirect(link):
            return link
        return cls._shown_front_page(str(result.get("display_link") or "")) or link

    @staticmethod
    def _is_google_redirect(link: str) -> bool:
        """Whether a link is Google's redirect (« https://www.google.fr/goto?url=… »), not a page of the result."""
        parsed = urlparse(link)
        return ".google." in f".{(parsed.hostname or '').lower()}." and parsed.path in _REDIRECT_PATHS

    @staticmethod
    def _shown_front_page(shown_address: str) -> str | None:
        """
        The front page of the site an address shown under a title names.

        Returns:
            « https://exemple.fr/ » for « https://exemple.fr › contact »; ``None`` when the address is empty, cut
            or Google's own.
        """
        origin = shown_address.split(_SHOWN_ADDRESS_SEPARATOR, 1)[0].strip()
        if origin and "://" not in origin:
            origin = f"https://{origin}"
        parsed = urlparse(origin)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in ("http", "https") or not _HOST_RE.match(host) or ".google." in f".{host}.":
            return None
        return f"{parsed.scheme}://{host}/"
