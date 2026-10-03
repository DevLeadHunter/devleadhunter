"""Phone numbers read in the prospect's country: Québec (NANP) never mistaken for France."""

from __future__ import annotations

from types import SimpleNamespace

from services.prospect_phones import dedupe_phones, first_mobile_e164, sync_prospect_phones
from services.sms.phone_normalizer import (
    format_phone_for_display,
    to_e164,
    to_e164_fr,
    to_e164_mobile,
    to_e164_nanp,
)


class TestNorthAmericanNumbers:
    def test_ten_digits_in_every_local_shape(self) -> None:
        assert to_e164_nanp("514 555-0199") == "+15145550199"
        assert to_e164_nanp("(514) 555-0199") == "+15145550199"
        assert to_e164_nanp("514.555.0199") == "+15145550199"
        assert to_e164_nanp("5145550199") == "+15145550199"

    def test_with_the_country_code(self) -> None:
        assert to_e164_nanp("+1 514 555 0199") == "+15145550199"
        assert to_e164_nanp("1-514-555-0199") == "+15145550199"
        assert to_e164_nanp("001 514 555 0199") == "+15145550199"

    def test_rejects_non_subscriber_shapes(self) -> None:
        assert to_e164_nanp("014 555 0199") is None
        assert to_e164_nanp("514 155 0199") is None
        assert to_e164_nanp("514 555") is None
        assert to_e164_nanp("") is None
        assert to_e164_nanp(None) is None


class TestCountryAwareNormalization:
    def test_a_canadian_ten_digit_number_is_never_read_as_french(self) -> None:
        assert to_e164("514 555-0199", country="CA") == "+15145550199"
        assert to_e164_mobile("514 555-0199", country="CA") == "+15145550199"
        assert to_e164_fr("514 555-0199") is None
        # A French business typing ten digits without a leading 0 has no French shape either.
        assert to_e164("514 555-0199", country="FR") is None
        assert to_e164_mobile("514 555-0199", country="FR") is None

    def test_an_international_form_is_read_whatever_the_country(self) -> None:
        assert to_e164("+1 514 555 0199", country="FR") == "+15145550199"
        assert to_e164("+33 6 12 34 56 78", country="CA") == "+33612345678"
        assert to_e164("0041 79 123 45 67", country="FR") == "+41791234567"

    def test_national_forms_of_other_countries_follow_their_dial_code(self) -> None:
        assert to_e164("079 123 45 67", country="CH") == "+41791234567"
        assert to_e164("0470 12 34 56", country="BE") == "+32470123456"
        assert to_e164("621 123 456", country="LU") == "+352621123456"
        assert to_e164("06 12 34 56 78", country="FR") == "+33612345678"

    def test_canadian_mobile_normalization_leaves_the_french_rules_alone(self) -> None:
        assert to_e164_mobile("06 12 34 56 78", country="FR") == "+33612345678"
        assert to_e164_mobile("01 42 68 53 00", country="FR") is None
        assert to_e164_mobile("079 123 45 67", country="CH") is None


class TestDisplayFormat:
    def test_quebec_writes_the_area_code_apart_and_hyphenates(self) -> None:
        assert format_phone_for_display("5145550199", country="CA") == "514 555-0199"
        assert format_phone_for_display("+1 514 555 0199", country="CA") == "514 555-0199"

    def test_france_groups_by_two(self) -> None:
        assert format_phone_for_display("+33612345678", country="FR") == "06 12 34 56 78"
        assert format_phone_for_display("06 12 34 56 78", country="FR") == "06 12 34 56 78"

    def test_unknown_shapes_and_other_countries_keep_what_was_typed(self) -> None:
        assert format_phone_for_display("079 123 45 67", country="CH") == "079 123 45 67"
        assert format_phone_for_display("standard: 12", country="FR") == "standard: 12"
        assert format_phone_for_display("", country="CA") == ""
        assert format_phone_for_display(None, country="CA") == ""


class TestProspectPhonesByCountry:
    def test_french_numbers_dedupe_across_formats(self) -> None:
        assert dedupe_phones(["06 42 19 38 12", "+33642193812"], "FR") == ["06 42 19 38 12"]

    def test_a_swiss_number_dedupes_with_its_international_form(self) -> None:
        assert dedupe_phones(["079 123 45 67", "+41 79 123 45 67"], "CH") == ["079 123 45 67"]

    def test_quebec_numbers_dedupe_across_formats(self) -> None:
        assert dedupe_phones(["514 555-0199", "+15145550199", "(514) 555-0199"], "CA") == ["514 555-0199"]

    def test_sync_dedupes_in_the_prospect_country(self) -> None:
        prospect = SimpleNamespace(phone="514 555-0199", phones=["514 555-0199"], country="CA")
        sync_prospect_phones(prospect, add=["+1 514 555 0199", "438 555-0100"])
        assert prospect.phones == ["514 555-0199", "438 555-0100"]
        assert prospect.phone == "514 555-0199"

    def test_a_canadian_number_is_not_an_sms_mobile(self) -> None:
        # The plan does not tell a cellular from a landline, and cold SMS is closed in Canada.
        prospect = SimpleNamespace(phone="514 555-0199", phones=["514 555-0199"], country="CA")
        assert first_mobile_e164(prospect) is None
