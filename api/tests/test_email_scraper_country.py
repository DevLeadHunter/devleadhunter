"""The email search abroad: Google ranked for the prospect's country, the phone quoted as that country writes it.

No browser and no network: navigation is recorded, results pages are canned text.
"""

from __future__ import annotations

import asyncio
import importlib

import pytest

from scrappers.email_scraper import EmailScraper
from scrappers.nodriver_dom import NodriverDom

email_scraper_module = importlib.import_module("scrappers.email_scraper")


class _FakeTab:
    """A results page the scraper reads, standing in for a nodriver tab."""

    def __init__(self, page_text: str = "") -> None:
        self.page_text = page_text

    async def get_content(self) -> str:
        """The canned page text."""
        return self.page_text


@pytest.fixture
def visited_urls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record every URL the scraper opens; a social results page lists no profile."""
    urls: list[str] = []

    async def record_navigation(tab: object, url: str, *, sleep_s: float = 0.8) -> None:
        urls.append(url)

    async def no_profile_links(tab: object, js: str) -> list[str]:
        return []

    monkeypatch.setattr(NodriverDom, "navigate", record_navigation)
    monkeypatch.setattr(NodriverDom, "evaluate_list", no_profile_links)
    return urls


class TestGoogleSearchUrl:
    def test_a_swiss_prospect_is_searched_with_gl_ch(self) -> None:
        url = EmailScraper.build_google_search_url('"Sanitaire Rochat" "Lausanne" email', country="CH")
        assert url == "https://www.google.com/search?q=%22Sanitaire+Rochat%22+%22Lausanne%22+email&gl=ch&hl=fr"

    def test_each_country_sends_its_own_region_in_french(self) -> None:
        assert EmailScraper.build_google_search_url("plombier", country="BE").endswith("&gl=be&hl=fr")
        assert EmailScraper.build_google_search_url("plombier", country="LU").endswith("&gl=lu&hl=fr")
        assert EmailScraper.build_google_search_url("plombier", country="CA").endswith("&gl=ca&hl=fr")
        assert EmailScraper.build_google_search_url("plombier").endswith("&gl=fr&hl=fr")

    def test_a_later_results_page_keeps_the_region(self) -> None:
        assert EmailScraper.build_google_search_url("plombier", country="CA", page_number=2).endswith(
            "&gl=ca&hl=fr&start=20"
        )


class TestResultsPageSearch:
    def test_a_swiss_results_page_is_ranked_for_switzerland_and_skips_local_ch(self, visited_urls: list[str]) -> None:
        tab = _FakeTab("Sanitaire Rochat, Lausanne — info@local.ch — Contact : contact@sanitaire-rochat.ch")
        email = asyncio.run(
            EmailScraper().search_google_page(
                tab, '"Sanitaire Rochat" "Lausanne" email', 1, name="Sanitaire Rochat", city="Lausanne", country="CH"
            )
        )
        assert email == "contact@sanitaire-rochat.ch"
        assert visited_urls == [
            "https://www.google.com/search?q=%22Sanitaire+Rochat%22+%22Lausanne%22+email&gl=ch&hl=fr&start=10"
        ]


class TestSocialSearch:
    def test_a_swiss_phone_is_searched_in_its_national_form_with_gl_ch(self, visited_urls: list[str]) -> None:
        asyncio.run(
            EmailScraper()._find_email_social_nodriver(
                _FakeTab(), "Sanitaire Rochat", "Lausanne", "+41 79 123 45 67", country="CH"
            )
        )
        assert visited_urls == [
            EmailScraper.build_google_search_url(
                '"Sanitaire Rochat" "079 123 45 67" facebook OR instagram', country="CH"
            )
        ]

    def test_a_number_of_another_country_falls_back_on_the_city(self, visited_urls: list[str]) -> None:
        asyncio.run(
            EmailScraper()._find_email_social_nodriver(
                _FakeTab(), "Sanitaire Rochat", "Lausanne", "+33 6 12 34 56 78", country="CH"
            )
        )
        assert visited_urls == [
            EmailScraper.build_google_search_url('"Sanitaire Rochat" "Lausanne" facebook OR instagram', country="CH")
        ]

    def test_a_french_social_search_opens_the_same_url_as_before(self, visited_urls: list[str]) -> None:
        asyncio.run(
            EmailScraper()._find_email_social_nodriver(_FakeTab(), "Tacos Maru", "Châtellerault", "+33 6 29 34 58 99")
        )
        assert visited_urls == [
            "https://www.google.com/search?q=%22Tacos+Maru%22+%2206+29+34+58+99%22+facebook+OR+instagram&gl=fr&hl=fr"
        ]


class TestSmartSearchPhoneQuery:
    @pytest.mark.parametrize(
        ("phone", "country", "quoted_phone"),
        [
            ("+41 79 123 45 67", "CH", "079 123 45 67"),
            ("0470 12 34 56", "BE", "0470 12 34 56"),
            ("+352 621 123 456", "LU", "621 123 456"),
            ("+1 514 555 0199", "CA", "514 555-0199"),
            ("06 29 34 58 99", "FR", "06 29 34 58 99"),
            ("0629345899", "FR", "06 29 34 58 99"),
        ],
    )
    def test_the_phone_query_quotes_the_number_as_its_country_writes_it(
        self, monkeypatch: pytest.MonkeyPatch, phone: str, country: str, quoted_phone: str
    ) -> None:
        scraper = EmailScraper()
        searches: list[tuple[str, str]] = []

        async def record_search(
            tab: object,
            query: str,
            max_pages: int = 3,
            *,
            name: str,
            city: str,
            website: str | None = None,
            country: str = "FR",
        ) -> str:
            searches.append((query, country))
            return "contact@artisan.example"

        async def no_browser() -> None:
            return None

        async def canned_tab() -> _FakeTab:
            return _FakeTab()

        monkeypatch.setattr(email_scraper_module, "NODRIVER_AVAILABLE", True)
        monkeypatch.setattr(scraper, "ensure_browser", no_browser)
        monkeypatch.setattr(scraper._browser, "get_tab", canned_tab)
        monkeypatch.setattr(scraper, "search_google_multiple_pages", record_search)

        email = asyncio.run(scraper._find_email_smart_nodriver("Atelier Test", "Ville", phone=phone, country=country))

        assert email == "contact@artisan.example"
        assert searches == [(f'"Atelier Test" "{quoted_phone}"', country)]
