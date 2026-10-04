"""
Facebook page URLs — telling a business page from the rest of facebook.com.

Search engines return a page under many addresses (its root, a post, a photo, a
« /p/slug-id » permalink, a mobile host, tracking parameters). One page must be one
address, so the same business is recognised wherever it is met; and a result title
must lose Facebook's boilerplate to give the business name.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

# First path segments that are Facebook features, never a business page.
_RESERVED_FIRST_SEGMENTS: frozenset[str] = frozenset(
    {
        "login",
        "recover",
        "reg",
        "help",
        "policies",
        "policy.php",
        "legal",
        "terms",
        "privacy",
        "settings",
        "hashtag",
        "watch",
        "gaming",
        "games",
        "marketplace",
        "events",
        "groups",
        "story.php",
        "photo.php",
        "photo",
        "permalink.php",
        "media",
        "reel",
        "reels",
        "stories",
        "bookmarks",
        "notes",
        "business",
        "ads",
        "adsmanager",
        "careers",
        "home.php",
        "biz",
        "saved",
        "messages",
        "friends",
        "search",
        "public",
        "sharer",
        "sharer.php",
        "tr",
        "plugins",
        "dialog",
        "l.php",
        "flx",
        "ajax",
        "whitehat",
        "about",
        "connect",
        "campaign",
        "fundraisers",
        "live",
        "help.php",
    }
)

# Sub-tabs Facebook appends to a page title (« … - Home | Facebook »).
_TITLE_TAB_WORDS: str = (
    r"Home|Posts|About|Photos|Videos|Reviews|Menu|Community|Shop|Services|Offers|Jobs|"
    r"Accueil|Publications|À propos|A propos|Avis|Vidéos|Boutique|Services|Menu|Offres"
)
_TITLE_TAB_RE: re.Pattern[str] = re.compile(rf"\s*[|\-–·]\s*(?:{_TITLE_TAB_WORDS})\s*$", re.IGNORECASE)
_TITLE_FACEBOOK_RE: re.Pattern[str] = re.compile(r"\s*[|\-–·]\s*Facebook\s*$", re.IGNORECASE)
_TITLE_NOTIFICATION_PREFIX_RE: re.Pattern[str] = re.compile(r"^\s*\(\d+\)\s*")

_PAGE_HANDLE_RE: re.Pattern[str] = re.compile(r"^[A-Za-z0-9.\-_]+$")
_PERMALINK_ID_RE: re.Pattern[str] = re.compile(r"-(\d{6,})$")
_FACEBOOK_ROOT: str = "https://www.facebook.com"


class FacebookPageUrl:
    """Reads Facebook URLs and result titles."""

    @classmethod
    def canonical(cls, raw_url: str) -> str | None:
        """
        Reduce any Facebook URL to the address of its page, or ``None`` when it is not a page.

        A page reference (``/{handle}``, ``/pg/{handle}``, ``/pages/{name}/{id}``,
        ``/people/{name}/{id}``, ``/p/{slug}-{id}``, ``/profile.php?id=…``) collapses to its
        root, dropping sub-tabs, posts, photos and tracking parameters. Feature URLs (login,
        groups, watch, sharer…) are not pages.

        Args:
            raw_url: Any URL that may point at a Facebook page.

        Returns:
            The page's canonical ``https://www.facebook.com/…`` URL, or ``None``.
        """
        parsed = urlparse(raw_url.strip())
        host = parsed.netloc.lower()
        if host != "facebook.com" and not host.endswith(".facebook.com"):
            return None

        segments = [segment for segment in parsed.path.split("/") if segment]
        if not segments:
            return None
        first = segments[0].lower()

        if first == "profile.php":
            page_id = parse_qs(parsed.query).get("id", [""])[0]
            return f"{_FACEBOOK_ROOT}/profile.php?id={page_id}" if page_id.isdigit() else None
        if first == "pg":
            return cls.canonical(f"{_FACEBOOK_ROOT}/{'/'.join(segments[1:])}") if len(segments) > 1 else None
        if first == "pages":
            is_named_page = len(segments) >= 3 and segments[1].lower() != "category"
            if is_named_page and _PAGE_HANDLE_RE.match(segments[2]):
                return f"{_FACEBOOK_ROOT}/pages/{segments[1]}/{segments[2]}"
            return None
        if first == "people":
            if len(segments) >= 3 and segments[2].isdigit():
                return f"{_FACEBOOK_ROOT}/{segments[2]}"
            return None
        if first == "p":
            # « /p/{slug}-{id}/ » permalink of a recent page: the id alone is the page's stable address.
            page_id_match = _PERMALINK_ID_RE.search(segments[1]) if len(segments) > 1 else None
            return f"{_FACEBOOK_ROOT}/{page_id_match.group(1)}" if page_id_match else None
        if first in _RESERVED_FIRST_SEGMENTS:
            return None

        handle = segments[0]
        if not _PAGE_HANDLE_RE.match(handle) or handle.endswith(".php"):
            return None
        return f"{_FACEBOOK_ROOT}/{handle}"

    @staticmethod
    def business_name_of_title(result_title: str) -> str:
        """
        Strip Facebook's boilerplate from a search result title.

        Removes a leading notification count (« (3) »), a trailing sub-tab (« - Avis »)
        and the trailing « | Facebook ».

        Args:
            result_title: Title of a search result on facebook.com.

        Returns:
            The business name, whitespace-collapsed (may be empty).
        """
        cleaned = _TITLE_NOTIFICATION_PREFIX_RE.sub("", result_title or "")
        cleaned = _TITLE_FACEBOOK_RE.sub("", cleaned)
        cleaned = _TITLE_TAB_RE.sub("", cleaned)
        # « … - Home | Facebook » needs the Facebook suffix removed on both sides of the tab.
        cleaned = _TITLE_FACEBOOK_RE.sub("", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip()
