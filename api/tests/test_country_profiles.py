"""Country profiles: the registry every country-dependent service reads."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from enums.country import SUPPORTED_COUNTRIES, normalize_country
from enums.sms_opt_out_mode import SmsOptOutMode
from services.country_profiles import CountryProfile, CountryProfiles
from services.pricing_service import PricingService


def _quebec() -> CountryProfile:
    """The Québec profile, read whether or not the country is open."""
    profile = CountryProfiles.declared("CA")
    assert profile is not None
    return profile


def test_unknown_or_missing_code_resolves_to_france() -> None:
    assert CountryProfiles.get(None).code == "FR"
    assert CountryProfiles.get("xx").code == "FR"
    assert CountryProfiles.get(" ch ").code == "CH"


def test_supported_countries_are_the_enabled_profiles() -> None:
    assert {profile.code: profile.label for profile in CountryProfiles.enabled()} == SUPPORTED_COUNTRIES
    assert "FR" in SUPPORTED_COUNTRIES


def test_a_declared_but_closed_country_stays_out_of_prospection() -> None:
    canada = CountryProfiles.declared("CA")
    assert canada is not None
    assert canada.enabled is False
    assert "CA" not in SUPPORTED_COUNTRIES
    assert normalize_country("CA") == "FR"


def test_every_profile_names_a_real_timezone() -> None:
    for code in ("FR", "CH", "BE", "LU", "CA"):
        profile = CountryProfiles.declared(code)
        assert profile is not None
        assert ZoneInfo(profile.timezone) is not None


def test_euro_countries_keep_the_exact_price() -> None:
    assert CountryProfiles.get("FR").format_price(50000) == "500 €"
    assert CountryProfiles.get("FR").format_price(49990) == "499,90 €"
    assert CountryProfiles.get("BE").format_price(50000) == "500 €"
    assert PricingService.format_price(50000) == "500 €"


def test_foreign_countries_show_a_rounded_converted_price() -> None:
    assert CountryProfiles.get("CH").format_price(50000) == "≈ 470 CHF"
    canada = CountryProfiles.declared("CA")
    assert canada is not None
    assert canada.format_price(50000) == "≈ 800 $ CA"


def test_sms_rules_follow_leo_decisions() -> None:
    assert CountryProfiles.get("FR").sms_opt_out is SmsOptOutMode.SHORT_CODE
    assert CountryProfiles.get("CH").sms_prospecting_open is True
    assert CountryProfiles.get("CH").sms_opt_out is SmsOptOutMode.LINK
    assert CountryProfiles.get("BE").sms_prospecting_open is False


def test_postal_code_regex_reads_each_country_shape() -> None:
    assert CountryProfiles.get("FR").postal_code_regex.search("12 rue X, 75002 Paris").group(1) == "75002"
    assert CountryProfiles.get("CH").postal_code_regex.search("Rue du Rhône 12, 1204 Genève").group(1) == "1204"
    assert _quebec().postal_code_regex.search("Montréal (Québec) h2x 1y4").group(1) == "h2x 1y4"
    assert CountryProfiles.get("FR").postal_code_regex.search("Montréal (Québec) H2X 1Y4") is None


def test_an_address_tail_drops_the_country_and_the_province() -> None:
    assert _quebec().strip_address_tail("12 Rue X, Laval, QC, Canada") == "12 Rue X, Laval"
    assert _quebec().strip_address_tail("123, rue X, Montréal (Québec)") == "123, rue X, Montréal"
    assert _quebec().strip_address_tail("123 rue X, Laval, Québec") == "123 rue X, Laval"
    assert _quebec().strip_address_tail("MONTRÉAL QC") == "MONTRÉAL"
    assert _quebec().strip_address_tail(", Canada") == ""
    assert CountryProfiles.get("CH").strip_address_tail("Rue du Rhône 12, Genève, Suisse") == "Rue du Rhône 12, Genève"
    assert (
        CountryProfiles.get("FR").strip_address_tail("12 rue de la Paix, Paris, France") == "12 rue de la Paix, Paris"
    )


def test_a_province_that_is_also_a_city_stays_when_nothing_else_names_the_city() -> None:
    """« 123, rue X, Québec » is in Québec City: the bare province name is kept."""
    assert _quebec().strip_address_tail("123, rue X, Québec") == "123, rue X, Québec"
    assert _quebec().strip_address_tail("123, rue X, Québec (Québec)") == "123, rue X, Québec"


def test_luxembourg_keeps_its_capital() -> None:
    """The capital bears the country's name: nothing is dropped from a Luxembourg address."""
    assert CountryProfiles.get("LU").strip_address_tail("12 rue X, Luxembourg") == "12 rue X, Luxembourg"
