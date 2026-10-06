"""
Facebook page results — telling a business page of the searched town from the noise.

A search engine query « site:facebook.com "trade" "town" » returns posts, videos,
groups, personal profiles and pages of other towns that merely contain the words.
Only a result that is the root of a business page, whose title or snippet places it
in the town (not merely a name that sounds like the town), becomes a candidate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from scrappers.facebook_page_urls import FacebookPageUrl
from services.decision_maker.normalize import fold
from services.prospect_search.search_judge import SearchResultLine

_PAGE_SUB_TABS: frozenset[str] = frozenset({"about", "reviews"})
_NAME_MAX_CHARS: int = 80
_PERSONAL_PROFILE_MARKERS: tuple[str, ...] = (
    "personnes que vous pouvez connaitre",
    "others you may know",
    "anderen, die du kennst",
)


@dataclass(frozen=True)
class FacebookBusinessPage:
    """A business page found by a search engine."""

    page_url: str
    name: str
    result_link: str


class FacebookPageResults:
    """Keeps, among search results on facebook.com, the business pages of a town."""

    @classmethod
    def business_pages(cls, results: list[SearchResultLine], *, town: str) -> list[FacebookBusinessPage]:
        """
        Filter search results down to business pages of the searched town.

        Args:
            results: Result lines of a « site:facebook.com » search.
            town: The searched town.

        Returns:
            One entry per page, in result order.
        """
        pages: dict[str, FacebookBusinessPage] = {}
        for line in results:
            page_url = FacebookPageUrl.canonical(line.link)
            if not page_url or page_url in pages or not cls.is_page_root(line.link):
                continue
            name, title_town = cls._split_title(line.title)
            if not name or len(name) > _NAME_MAX_CHARS or "#" in name or name.endswith(("...", "…")):
                continue
            if any(marker in fold(line.description) for marker in _PERSONAL_PROFILE_MARKERS):
                continue
            if not cls._is_in_town(title_town, line.description, town, name=name):
                continue
            pages[page_url] = FacebookBusinessPage(page_url=page_url, name=name, result_link=line.link)
        return list(pages.values())

    @staticmethod
    def is_page_root(link: str) -> bool:
        """Whether a link points at a page itself, not at one of its posts, videos or photos."""
        segments = [segment for segment in urlparse(link).path.split("/") if segment]
        if not segments:
            return False
        if segments[0] in {"p", "pages", "people"}:
            return len(segments) <= 3
        if segments[0] == "profile.php":
            return True
        return len(segments) == 1 or (len(segments) == 2 and segments[1] in _PAGE_SUB_TABS)

    @staticmethod
    def _split_title(title: str) -> tuple[str, str | None]:
        """Split « Name | Town » (the shape Facebook gives a page title) into its two parts."""
        cleaned = FacebookPageUrl.business_name_of_title(title)
        parts = [part.strip() for part in re.split(r"\s[|·]\s", cleaned) if part.strip()]
        if not parts:
            return "", None
        return parts[0], parts[1] if len(parts) > 1 else None

    @staticmethod
    def _is_in_town(title_town: str | None, description: str, town: str, *, name: str) -> bool:
        """
        Whether the page is placed in the searched town, by its title or else by its snippet.

        The page's own name does not count: « Paul Rolle » is no page of the town of Rolle.
        """
        searched = fold(town)
        if title_town is not None:
            return searched in fold(title_town)
        description_without_name = fold(description).replace(fold(name), " ")
        return re.search(rf"\b{re.escape(searched)}\b", description_without_name) is not None
