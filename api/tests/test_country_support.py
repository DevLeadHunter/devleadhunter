"""Europe support: country normalization, search routing and query disambiguation."""

from __future__ import annotations

from urllib.parse import unquote

from enums.country import country_label, normalize_country, search_label
from enums.source import Source
from scrappers.google_scraper import GoogleScraper
from scrappers.osm_scraper import OSMScraper
from services.scraper_service import ScraperService


class _StubScraper:
    """Bare stand-in carrying only the ``source`` the ordering logic reads."""

    def __init__(self, source: Source) -> None:
        self.source = source


def _service_with_all_sources() -> ScraperService:
    service = ScraperService()
    for source in (Source.GOOGLE, Source.PAGESJAUNES, Source.BRIGHTDATA, Source.OSM, Source.FACEBOOK):
        service._scrapers.append(_StubScraper(source))
    return service


def test_normalize_country_defaults_unknown_codes_to_france() -> None:
    """Only supported alpha-2 codes survive; anything else falls back to FR."""
    assert normalize_country("ch") == "CH"
    assert normalize_country(" be ") == "BE"
    assert normalize_country("lu") == "LU"
    assert normalize_country("XX") == "FR"
    assert normalize_country(None) == "FR"


def test_country_label_names_the_country_in_french() -> None:
    """Labels feed search queries ("plombier à Mons Belgique")."""
    assert country_label("CH") == "Suisse"
    assert country_label("BE") == "Belgique"
    assert country_label("LU") == "Luxembourg"


def test_failover_chain_drops_french_directories_outside_france() -> None:
    """A Swiss search never cascades into Pages Jaunes or its Bright Data unlocker."""
    service = _service_with_all_sources()
    candidates, _ = service._ordered_candidates(None, "CH")
    names = [scraper.source.value for scraper in candidates]
    assert "pagesjaunes" not in names
    assert "brightdata" not in names
    assert names[0] == "google"


def test_failover_chain_keeps_french_directories_in_france() -> None:
    """The French chain is unchanged by the country parameter."""
    service = _service_with_all_sources()
    candidates, _ = service._ordered_candidates(None, "FR")
    names = [scraper.source.value for scraper in candidates]
    assert names == ["google", "pagesjaunes", "brightdata", "osm"]


def test_google_query_appends_the_country_outside_france() -> None:
    """Homonym cities (Mons, Fribourg…) need the country pinned in the Maps query."""
    assert GoogleScraper.build_query("plombier", "Mons", "BE").endswith("Belgique")
    assert "Suisse" not in GoogleScraper.build_query("plombier", "Lyon", "FR")


def test_switzerland_is_searched_with_its_name() -> None:
    """The search suffix is the region the prospects read in their listings, nothing in France."""
    assert search_label("CH") == "Suisse"
    assert search_label("FR") == ""
    assert unquote(GoogleScraper.build_query("paysagiste", "Genève", "CH")) == "paysagiste à Genève Suisse"


def test_extract_city_reads_the_country_postal_shape() -> None:
    """A Swiss code has four digits; the country written after the city is never taken for it."""
    assert GoogleScraper.extract_city("12 rue de la Paix, 75002 Paris", "FR") == "Paris"
    assert GoogleScraper.extract_city("Rue du Rhône 12, 1204 Genève, Suisse", "CH") == "Genève"
    assert OSMScraper.extract_city("Rue du Rhône 12, 1204 Genève, Suisse", "CH") == "Genève"


def test_extract_city_never_returns_the_country_or_the_province() -> None:
    """Without a postal code the last segment used to be « Suisse » or « Belgique »."""
    assert GoogleScraper.extract_city("Rue du Rhône 12, Genève, Suisse", "CH") == "Genève"
    assert GoogleScraper.extract_city("Rue de la Loi 16, 1000 Bruxelles, Belgique", "BE") == "Bruxelles"
