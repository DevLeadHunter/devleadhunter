"""The prospect's country reaches every email search and every desktop enrichment, France by default."""

from __future__ import annotations

import asyncio

import pytest

import enrich_cli
import scraper_sidecar as sidecar
from enums.source import Source
from models.prospect import ProspectCreate
from scrappers.auto_scraper import AutoScraper
from scrappers.email_scraper import email_scraper
from scrappers.enrichment_scraper import EnrichmentData, enrichment_scraper
from scrappers.google_scraper import GoogleScraper
from scrappers.osm_scraper import OSMScraper


@pytest.fixture
def email_search_countries(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The country of every email search the scrapers launch, without opening a browser."""
    countries: list[str] = []

    async def record_find_email(name: str, city: str, website: str | None = None, *, country: str = "FR") -> None:
        countries.append(country)

    async def record_find_email_smart(
        name: str,
        city: str,
        phone: str | None = None,
        social_url: str | None = None,
        website: str | None = None,
        *,
        country: str = "FR",
    ) -> None:
        countries.append(country)

    monkeypatch.setattr(email_scraper, "find_email", record_find_email)
    monkeypatch.setattr(email_scraper, "find_email_smart", record_find_email_smart)
    return countries


@pytest.fixture
def enrichment_countries(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The country every desktop enrichment hands to the scraper, without opening a browser."""
    countries: list[str] = []

    async def record_enrich(
        business_name: str,
        city: str | None = None,
        google_maps_url: str | None = None,
        facebook_url: str | None = None,
        country: str = "FR",
    ) -> EnrichmentData:
        countries.append(country)
        return EnrichmentData(source="facebook")

    monkeypatch.setattr(enrichment_scraper, "enrich", record_enrich)
    return countries


class TestEmailSearchCountry:
    def test_the_auto_scraper_searches_in_the_search_country(self, email_search_countries: list[str]) -> None:
        prospect = ProspectCreate(
            name="Sanitaire Rochat",
            city="Lausanne",
            phone="+41 21 123 45 67",
            category="Plombier",
            source=Source.OSM,
            confidence=2,
        )
        asyncio.run(AutoScraper()._enrich_email(prospect, "CH"))
        assert email_search_countries == ["CH"]

    def test_a_single_maps_place_searches_its_email_in_the_search_country(
        self, email_search_countries: list[str]
    ) -> None:
        details: dict[str, str | None] = {
            "name": "Plomberie Tremblay",
            "address": "123, rue Principale, Laval (Québec) H7N 1A1",
            "city": "Laval",
            "phone": "450 555-0199",
            "website": None,
            "category": "Plombier",
        }
        asyncio.run(GoogleScraper()._build_prospect_from_details(details, country="CA"))
        asyncio.run(GoogleScraper()._build_prospect_from_details(details))
        assert email_search_countries == ["CA", "FR"]

    def test_an_osm_business_searches_its_email_in_the_search_country(self, email_search_countries: list[str]) -> None:
        business = {"tags": {"name": "Sanitaire Rochat", "craft": "plumber", "addr:city": "Lausanne"}}
        asyncio.run(OSMScraper().extract_prospect_from_osm_data(business, "Lausanne", country="CH"))
        assert email_search_countries == ["CH"]


class TestDesktopEnrichmentCountry:
    def test_the_sidecar_reads_the_page_in_the_prospect_country(
        self, monkeypatch: pytest.MonkeyPatch, enrichment_countries: list[str]
    ) -> None:
        async def nothing_to_close() -> None:
            return None

        monkeypatch.setattr(sidecar, "close_transient_browsers", nothing_to_close)
        monkeypatch.setattr(sidecar, "close_autocomplete_session", nothing_to_close)
        request = sidecar.SidecarEnrichmentRequest(
            business_name="Sanitaire Rochat",
            facebook_url="https://www.facebook.com/sanitairerochat",
            country="CH",
        )
        asyncio.run(sidecar.enrichment(request))
        assert enrichment_countries == ["CH"]

    def test_a_front_sending_no_country_still_reads_in_france(self) -> None:
        assert sidecar.SidecarEnrichmentRequest(business_name="Tacos Maru").country == "FR"

    def test_the_enrichment_cli_reads_each_prospect_in_its_country(self, enrichment_countries: list[str]) -> None:
        asyncio.run(enrich_cli._scrape({"id": 7, "name": "Plomberie Tremblay", "city": "Laval", "country": "CA"}))
        asyncio.run(enrich_cli._scrape({"id": 8, "name": "Tacos Maru", "city": "Châtellerault"}))
        assert enrichment_countries == ["CA", "FR"]
