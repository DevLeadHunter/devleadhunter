"""Country support: country normalization, search wording and address reading."""

from __future__ import annotations

from enums.country import country_label, normalize_country, search_label
from scrappers.google_scraper import GoogleScraper
from services.prospect_search.search_zones import SearchZones


def test_normalize_country_defaults_unknown_codes_to_france() -> None:
    """Only supported alpha-2 codes survive; anything else falls back to FR."""
    assert normalize_country("ch") == "CH"
    assert normalize_country(" be ") == "BE"
    assert normalize_country("lu") == "LU"
    assert normalize_country("XX") == "FR"
    assert normalize_country(None) == "FR"


def test_country_label_names_the_country_in_french() -> None:
    assert country_label("CH") == "Suisse"
    assert country_label("BE") == "Belgique"
    assert country_label("LU") == "Luxembourg"


def test_switzerland_is_searched_with_its_name() -> None:
    """The search suffix is the region the prospects read in their listings, nothing in France."""
    assert search_label("CH") == "Suisse"
    assert search_label("FR") == ""


def test_canada_is_searched_as_quebec() -> None:
    """Québec prospects read « Québec » in their listings, never « Canada (Québec) » (Laval exists in France too)."""
    assert normalize_country("ca") == "CA"
    assert country_label("CA") == "Canada (Québec)"
    assert search_label("CA") == "Québec"


def test_every_open_country_has_towns_to_search() -> None:
    for country in ("FR", "CH", "BE", "LU", "CA"):
        assert len(SearchZones.towns_of(country)) >= 5


def test_extract_city_reads_the_country_postal_shape() -> None:
    """A Swiss code has four digits; the country written after the city is never taken for it."""
    assert GoogleScraper.extract_city("12 rue de la Paix, 75002 Paris", "FR") == "Paris"
    assert GoogleScraper.extract_city("Rue du Rhône 12, 1204 Genève, Suisse", "CH") == "Genève"


def test_extract_city_never_returns_the_country_or_the_province() -> None:
    """Without a postal code the last segment used to be « Suisse » or « Belgique »."""
    assert GoogleScraper.extract_city("Rue du Rhône 12, Genève, Suisse", "CH") == "Genève"
    assert GoogleScraper.extract_city("Rue de la Loi 16, 1000 Bruxelles, Belgique", "BE") == "Bruxelles"


def test_extract_city_reads_a_quebec_address() -> None:
    """Maps writes « Montréal, QC H2X 1Y4, Canada »: the city is the segment before the province."""
    assert GoogleScraper.extract_city("123 Rue Sainte-Catherine O, Montréal, QC H2X 1Y4, Canada", "CA") == "Montréal"
    assert GoogleScraper.extract_city("123 Rue X, Laval, QC H7N 1A1, Canada", "CA") == "Laval"
    assert GoogleScraper.extract_city("123 Rue X, Laval, QC, Canada", "CA") == "Laval"
    assert GoogleScraper.extract_city("123, rue X, Montréal (Québec) H2X 1Y4", "CA") == "Montréal"
