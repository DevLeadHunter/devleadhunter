"""Country profiles: the registry every country-dependent service reads."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from enums.country import SUPPORTED_COUNTRIES, normalize_country
from enums.sms_opt_out_mode import SmsOptOutMode
from services.country_profiles import CountryProfiles
from services.pricing_service import PricingService


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
