"""Multi-phone helpers: dedupe, iteration, and picking the SMS-reachable mobile.

The SMS relance must reach a mobile that may NOT be the display primary (often a business
landline), so :func:`first_mobile_e164` scans the whole list and returns the first 06/07.
"""

from types import SimpleNamespace

from services.prospect_phones import dedupe_phones, first_mobile_e164, iter_phones, sync_prospect_phones


def _prospect(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {"phone": None, "phones": None}
    base.update(overrides)
    return SimpleNamespace(**base)


class TestDedupePhones:
    def test_dedupes_across_formats_keeping_order(self) -> None:
        assert dedupe_phones(["06 42 19 38 12", "+33642193812", "01 42 68 53 00"]) == [
            "06 42 19 38 12",
            "01 42 68 53 00",
        ]

    def test_drops_blanks_and_non_strings(self) -> None:
        assert dedupe_phones(["", "  ", None, 42, "0612345678"]) == ["0612345678"]


class TestIterPhones:
    def test_returns_the_stored_list(self) -> None:
        assert iter_phones(_prospect(phones=["0612345678", "0142685300"])) == ["0612345678", "0142685300"]

    def test_falls_back_to_the_single_phone(self) -> None:
        assert iter_phones(_prospect(phone="0612345678")) == ["0612345678"]

    def test_tolerates_a_missing_phones_attribute(self) -> None:
        # Legacy rows / lightweight test objects may not carry a `phones` attribute at all.
        assert iter_phones(SimpleNamespace(phone="0612345678")) == ["0612345678"]

    def test_empty_when_no_number_at_all(self) -> None:
        assert iter_phones(_prospect()) == []


class TestFirstMobileE164:
    def test_none_when_only_a_landline(self) -> None:
        assert first_mobile_e164(_prospect(phone="01 42 68 53 00", phones=["01 42 68 53 00"])) is None

    def test_returns_the_mobile_when_it_is_primary(self) -> None:
        assert first_mobile_e164(_prospect(phone="06 12 34 56 78", phones=["06 12 34 56 78"])) == "+33612345678"

    def test_finds_a_mobile_sitting_behind_a_landline_primary(self) -> None:
        # Léo's case: the business landline stays the display primary, the mobile is added after it.
        prospect = _prospect(phone="01 42 68 53 00", phones=["01 42 68 53 00", "+33 6 12 34 56 78"])
        assert first_mobile_e164(prospect) == "+33612345678"

    def test_falls_back_to_the_single_phone_field(self) -> None:
        assert first_mobile_e164(_prospect(phone="0612345678")) == "+33612345678"

    def test_none_without_any_number(self) -> None:
        assert first_mobile_e164(_prospect()) is None


class TestSyncPromotesMobile:
    def test_a_discovered_mobile_becomes_primary_and_demotes_the_landline(self) -> None:
        prospect = _prospect(phone="01 42 68 53 00", phones=["01 42 68 53 00"])
        sync_prospect_phones(prospect, add=["07 49 43 28 84"])
        assert prospect.phones == ["07 49 43 28 84", "01 42 68 53 00"]
        assert prospect.phone == "07 49 43 28 84"

    def test_an_existing_primary_mobile_is_kept(self) -> None:
        prospect = _prospect(phone="06 12 34 56 78", phones=["06 12 34 56 78"])
        sync_prospect_phones(prospect, add=["01 42 68 53 00"])
        assert prospect.phones[0] == "06 12 34 56 78"

    def test_a_forced_primary_wins_over_a_mobile(self) -> None:
        # The human explicitly chose a primary in the drawer — never override it, even for a mobile.
        prospect = _prospect(phone="06 12 34 56 78", phones=["06 12 34 56 78"])
        sync_prospect_phones(prospect, primary="01 42 68 53 00")
        assert prospect.phone == "01 42 68 53 00"

    def test_a_landline_only_prospect_keeps_its_landline_primary(self) -> None:
        prospect = _prospect(phone="01 42 68 53 00", phones=["01 42 68 53 00"])
        sync_prospect_phones(prospect, add=["04 78 00 00 00"])
        assert prospect.phone == "01 42 68 53 00"
