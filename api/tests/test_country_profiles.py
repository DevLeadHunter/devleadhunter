"""Country profiles: the registry every country-dependent service reads."""

from __future__ import annotations

import dataclasses
from zoneinfo import ZoneInfo

import pytest

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


def test_canada_is_open_to_prospection_by_email_only() -> None:
    canada = CountryProfiles.get("CA")
    assert canada.enabled is True
    assert SUPPORTED_COUNTRIES["CA"] == "Canada (Québec)"
    assert normalize_country("ca") == "CA"
    assert canada.sms_prospecting_open is False
    assert canada.email_footer_needs_postal_address is True
    assert canada.search_label == "Québec"
    assert canada.in_european_union is False


def test_a_closed_country_reads_as_france(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get`` only resolves open profiles: a declared-but-closed country reads as France."""
    closed = dataclasses.replace(_quebec(), enabled=False)
    monkeypatch.setitem(CountryProfiles._PROFILES, "CA", closed)
    assert CountryProfiles.get("CA").code == "FR"
    assert CountryProfiles.declared("CA") is closed
    assert "CA" not in {profile.code for profile in CountryProfiles.enabled()}


def test_the_open_countries_are_france_switzerland_belgium_luxembourg_and_quebec() -> None:
    assert [profile.code for profile in CountryProfiles.enabled()] == ["FR", "CH", "BE", "LU", "CA"]


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


def test_a_small_converted_price_is_rounded_to_the_unit() -> None:
    assert CountryProfiles.get("CH").format_price(7900) == "≈ 74 CHF"


def test_a_price_shown_alone_drops_the_approximation_sign() -> None:
    assert CountryProfiles.get("CH").format_price_without_approximation(50000) == "470 CHF"
    assert CountryProfiles.get("FR").format_price_without_approximation(49990) == "499,90 €"
    assert CountryProfiles.get("CA").format_price(7900) == "≈ 126 $ CA"
    assert CountryProfiles.get("FR").format_price(7900) == "79 €"


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


def test_an_address_ending_with_another_country_is_abroad() -> None:
    romont_in_france = CountryProfiles.foreign_country_of_address(
        "6 Rue des Vignes, 88700 Romont, France", country="CH"
    )
    laval = CountryProfiles.foreign_country_of_address("12 Rue X, Laval, QC, Canada", country="FR")

    assert romont_in_france is not None and romont_in_france.code == "FR"
    assert laval is not None and laval.code == "CA"
    assert CountryProfiles.foreign_country_of_address("Rue du Rhône 12, 1204 Genève, Suisse", country="CH") is None
    assert CountryProfiles.foreign_country_of_address("Route du Léman 55, 1907 Saxon", country="CH") is None
    assert CountryProfiles.foreign_country_of_address(None, country="CH") is None
