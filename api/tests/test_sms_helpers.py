"""Unit tests for the pure SMS helpers — phone, segments, legal window per country, pricing, callbacks."""

from datetime import date, datetime

import pytest
from sqlalchemy.orm import Session

from api.v1.routes.sms import _match_stop_message
from core.config import settings
from enums.sms_opt_out_mode import SmsOptOutMode
from models.sms_message import SmsMessage
from services.sms.dlr import (
    classify_dlr,
    dlr_message_id,
    dlr_ref_client,
    dlr_status_detail,
    dlr_status_value,
)
from services.sms.gsm_segments import is_gsm7, segment_count, segment_count_with_reserve, to_gsm7
from services.sms.mo import mo_is_stop, mo_origin_message_id, mo_ref_client, mo_sender_number
from services.sms.opt_out_mention import SmsOptOutMention
from services.sms.phone_normalizer import PhoneNumberPlans, is_mobile_fr, to_e164_fr
from services.sms.pricing import SmsPricing
from services.sms.send_window import PublicHolidays, SmsSendWindow, france_send_window
from services.sms_config_service import SmsConfigService
from services.sms_service import sms_service


class TestPhoneNormalizer:
    def test_national_mobile_to_e164(self) -> None:
        assert to_e164_fr("06 29 34 58 99") == "+33629345899"

    def test_compact_and_dotted(self) -> None:
        assert to_e164_fr("0629345899") == "+33629345899"
        assert to_e164_fr("06.29.34.58.99") == "+33629345899"

    def test_already_international(self) -> None:
        assert to_e164_fr("+33 6 29 34 58 99") == "+33629345899"
        assert to_e164_fr("0033629345899") == "+33629345899"

    def test_landline_normalises_but_is_not_mobile(self) -> None:
        assert to_e164_fr("01 42 68 53 00") == "+33142685300"
        assert is_mobile_fr("01 42 68 53 00") is False

    def test_mobile_detection(self) -> None:
        assert is_mobile_fr("06 29 34 58 99") is True
        assert is_mobile_fr("07 12 34 56 78") is True

    def test_invalid_returns_none(self) -> None:
        assert to_e164_fr("12345") is None
        assert to_e164_fr("") is None
        assert to_e164_fr(None) is None


class TestMobileOfCountry:
    def test_a_french_mobile_reads_as_before(self) -> None:
        assert PhoneNumberPlans.mobile_of_country("06 29 34 58 99", country="FR") == "+33629345899"
        assert PhoneNumberPlans.mobile_of_country("+33 7 12 34 56 78", country=None) == "+33712345678"
        assert PhoneNumberPlans.mobile_of_country("01 42 68 53 00", country="FR") is None

    def test_a_french_number_is_read_exactly_as_the_former_french_helpers_read_it(self) -> None:
        for raw in (
            "06 29 34 58 99",
            "+33 6 29 34 58 99",
            "0033629345899",
            "33629345899",
            "+33 (0)6 29 34 58 99",
            "01 42 68 53 00",
            "079 123 45 67",
            "+41 79 123 45 67",
            "",
        ):
            former_reading = to_e164_fr(raw) if is_mobile_fr(raw) else None
            assert PhoneNumberPlans.mobile_of_country(raw, country="FR") == former_reading, raw

    def test_a_swiss_079_without_country_code_is_a_swiss_mobile_for_a_swiss_prospect(self) -> None:
        assert PhoneNumberPlans.mobile_of_country("079 123 45 67", country="CH") == "+41791234567"
        assert PhoneNumberPlans.mobile_of_country("079 123 45 67", country="FR") == "+33791234567"

    def test_a_swiss_landline_and_a_foreign_mobile_are_refused_for_a_swiss_prospect(self) -> None:
        assert PhoneNumberPlans.mobile_of_country("022 123 45 67", country="CH") is None
        assert PhoneNumberPlans.mobile_of_country("+41 22 123 45 67", country="CH") is None
        assert PhoneNumberPlans.mobile_of_country("+33 6 12 34 56 78", country="CH") is None

    def test_international_forms_of_the_prospect_country_are_kept(self) -> None:
        assert PhoneNumberPlans.mobile_of_country("+41 79 123 45 67", country="CH") == "+41791234567"
        assert PhoneNumberPlans.mobile_of_country("0041 76 123 45 67", country="ch") == "+41761234567"
        assert PhoneNumberPlans.mobile_of_country("0470 12 34 56", country="BE") == "+32470123456"

    def test_a_country_we_do_not_text_has_no_mobile(self) -> None:
        assert PhoneNumberPlans.mobile_of_country("514 555 0199", country="CA") is None
        assert PhoneNumberPlans.mobile_of_country("06 29 34 58 99", country="XX") is None

    def test_country_of_a_number_follows_its_dial_code(self) -> None:
        assert PhoneNumberPlans.country_of_e164("+33612345678") == "FR"
        assert PhoneNumberPlans.country_of_e164("+41791234567") == "CH"
        assert PhoneNumberPlans.country_of_e164("+447700900123") is None
        assert PhoneNumberPlans.country_of_e164(None) is None

    def test_an_international_number_with_or_without_its_plus_becomes_e164(self) -> None:
        assert PhoneNumberPlans.international_to_e164("33612345678") == "+33612345678"
        assert PhoneNumberPlans.international_to_e164("41791234567") == "+41791234567"
        assert PhoneNumberPlans.international_to_e164("+41 79 123 45 67") == "+41791234567"
        assert PhoneNumberPlans.international_to_e164("Dibodev") is None


class TestGsmSegments:
    def test_plain_ascii_is_gsm7_one_segment(self) -> None:
        assert is_gsm7("Bonjour, voici votre site : demo.dibodev.fr/xyz") is True
        assert segment_count("Bonjour, voici votre site : demo.dibodev.fr/xyz") == 1

    def test_accents_force_ucs2(self) -> None:
        # « é » is in GSM-7, but « ê »/« ô » are NOT → forces UCS-2.
        assert is_gsm7("aperçu prêt") is False

    def test_gsm7_160_boundary(self) -> None:
        assert segment_count("a" * 160) == 1
        assert segment_count("a" * 161) == 2

    def test_ucs2_70_boundary(self) -> None:
        body = "ê" * 70
        assert segment_count(body) == 1
        assert segment_count("ê" * 71) == 2

    def test_empty(self) -> None:
        assert segment_count("") == 0

    def test_the_reserve_counts_in_the_body_encoding(self) -> None:
        assert segment_count_with_reserve("a" * 146, 14) == 1
        assert segment_count_with_reserve("a" * 147, 14) == 2
        assert segment_count_with_reserve("ê" * 56, 14) == 1
        assert segment_count_with_reserve("ê" * 57, 14) == 2
        assert segment_count_with_reserve("", 14) == 0


class TestOptOutMention:
    def test_france_reserves_the_short_code_mention_and_elsewhere_the_link(self) -> None:
        assert SmsOptOutMention.mode_for_country("FR") is SmsOptOutMode.SHORT_CODE
        assert SmsOptOutMention.mode_for_country("CH") is SmsOptOutMode.LINK
        assert SmsOptOutMention.reserved_characters_for_country("FR") == 14
        assert SmsOptOutMention.reserved_characters_for_country("CH") == 25
        assert SmsOptOutMention.reserved_characters_for_country(None) == 25  # unknown destination: the longer mention

    def test_the_reserve_follows_the_destination_number(self) -> None:
        assert SmsOptOutMention.reserved_characters_for_number("+33612345678") == 14
        assert SmsOptOutMention.reserved_characters_for_number("+41791234567") == 25
        # A number of a country without a profile gets the link, the longer of the two mentions.
        assert SmsOptOutMention.reserved_characters_for_number("+491512345678") == 25


class TestToGsm7:
    def test_keeps_gsm7_accents_but_lowers_cedilla(self) -> None:
        # é è à ù stay (GSM-7); ç is NOT GSM-7 in lowercase → simplified to c; ô → o.
        assert to_gsm7("café à côté ça") == "café à coté ca"

    def test_simplifies_circumflex_and_ligatures(self) -> None:
        assert to_gsm7("prêt château cœur hôtel") == "pret chateau coeur hotel"

    def test_simplifies_typographic_punctuation(self) -> None:
        assert to_gsm7("l’été — « oui »… ") == 'l\'été - " oui "... '

    def test_normalized_french_message_is_one_segment(self) -> None:
        # A circumflex-laden message that would be UCS-2 collapses to a single GSM-7 segment.
        raw = "Bonjour, votre aperçu est prêt : demo.dibodev.fr/chateau-burger — Dibodev"
        assert is_gsm7(raw) is False
        assert is_gsm7(to_gsm7(raw)) is True
        assert segment_count(to_gsm7(raw)) == 1


class TestSendWindow:
    def test_weekday_inside(self) -> None:
        # Monday 2026-08-31 at 10:00 → open.
        assert france_send_window.is_open(datetime(2026, 8, 31, 10, 0)) is True

    def test_weekday_before_open(self) -> None:
        assert france_send_window.is_open(datetime(2026, 8, 31, 7, 30)) is False

    def test_saturday_hours(self) -> None:
        # Saturday 2026-08-29 — open 10:00–19:00.
        assert france_send_window.is_open(datetime(2026, 8, 29, 9, 30)) is False
        assert france_send_window.is_open(datetime(2026, 8, 29, 11, 0)) is True

    def test_sunday_closed(self) -> None:
        assert france_send_window.is_open(datetime(2026, 8, 30, 12, 0)) is False

    def test_public_holiday_closed(self) -> None:
        # 2026-05-01 (Fête du Travail) is a Friday but a holiday.
        assert france_send_window.is_open(datetime(2026, 5, 1, 11, 0)) is False

    def test_next_slot_defers_sunday_to_monday(self) -> None:
        slot = france_send_window.next_open_slot(datetime(2026, 8, 30, 12, 0))  # Sunday noon
        assert slot.weekday() == 0 and slot.hour == 8  # Monday 08:00

    def test_next_slot_before_open_returns_open(self) -> None:
        slot = france_send_window.next_open_slot(datetime(2026, 8, 31, 6, 0))  # Monday 06:00
        assert slot.hour == 8 and slot.date() == datetime(2026, 8, 31).date()

    def test_next_slot_inside_returns_same(self) -> None:
        moment = datetime(2026, 8, 31, 10, 0)
        assert france_send_window.next_open_slot(moment) == moment

    def test_utc_round_trip_follows_the_country_clock(self) -> None:
        paris_summer = datetime(2026, 8, 31, 10, 0)
        assert france_send_window.to_utc_naive(paris_summer) == datetime(2026, 8, 31, 8, 0)
        assert france_send_window.to_local_naive(datetime(2026, 8, 31, 8, 0)) == paris_summer


class TestSwissSendWindow:
    def test_the_window_is_evaluated_on_zurich_time(self) -> None:
        window = SmsSendWindow("CH")
        assert window.country == "CH"
        assert window.timezone.key == "Europe/Zurich"
        assert window.is_open(datetime(2026, 8, 31, 10, 0)) is True
        assert window.is_open(datetime(2026, 8, 30, 12, 0)) is False  # Sunday

    def test_swiss_national_holidays_close_the_window_and_french_ones_do_not(self) -> None:
        window = SmsSendWindow("CH")
        assert window.is_open(datetime(2026, 8, 1, 11, 0)) is False  # Fête nationale (a Saturday in 2026)
        assert window.is_open(datetime(2026, 4, 3, 11, 0)) is False  # Vendredi saint 2026
        assert window.is_open(datetime(2026, 7, 14, 11, 0)) is True  # 14 juillet is a working Tuesday in Switzerland
        assert window.is_open(datetime(2026, 5, 1, 11, 0)) is True  # 1er mai is cantonal only
        assert france_send_window.is_open(datetime(2026, 8, 3, 11, 0)) is True  # a plain Monday in France

    def test_the_next_slot_skips_a_swiss_holiday(self) -> None:
        window = SmsSendWindow("CH")
        # In 2026 the 1st of August is a Saturday: Friday evening jumps over the holiday and Sunday to Monday.
        slot = window.next_open_slot(datetime(2026, 7, 31, 21, 0))
        assert slot == datetime(2026, 8, 3, 8, 0)

    def test_an_undeclared_country_reads_the_french_window_and_a_closed_one_its_own_clock(self) -> None:
        assert SmsSendWindow("XX").country == "FR"
        assert SmsSendWindow(None).country == "FR"
        assert SmsSendWindow("CA").timezone.key == "America/Toronto"


class TestPublicHolidays:
    def test_easter_based_days_2026(self) -> None:
        assert PublicHolidays.easter_sunday(2026) == date(2026, 4, 5)
        assert date(2026, 4, 6) in PublicHolidays.france(2026)  # Lundi de Pâques
        assert date(2026, 5, 14) in PublicHolidays.france(2026)  # Ascension
        assert date(2026, 4, 3) in PublicHolidays.switzerland(2026)  # Vendredi saint
        assert date(2026, 5, 25) in PublicHolidays.switzerland(2026)  # Lundi de Pentecôte

    def test_the_country_dispatch_defaults_to_france(self) -> None:
        assert PublicHolidays.for_country("CH", 2026) == PublicHolidays.switzerland(2026)
        assert PublicHolidays.for_country("BE", 2026) == PublicHolidays.france(2026)
        assert PublicHolidays.for_country(None, 2026) == PublicHolidays.france(2026)


class TestSenderValidation:
    def test_valid_sender(self) -> None:
        assert SmsConfigService.is_valid_sender("Dibodev") is True

    def test_too_short(self) -> None:
        assert SmsConfigService.is_valid_sender("ab") is False

    def test_too_long(self) -> None:
        assert SmsConfigService.is_valid_sender("DibodevProSMS") is False

    def test_numeric_only_rejected(self) -> None:
        assert SmsConfigService.is_valid_sender("12345") is False

    def test_symbols_rejected(self) -> None:
        assert SmsConfigService.is_valid_sender("Dibo-dev") is False


class TestGsm7Body:
    def test_no_stop_mention_is_ever_written_by_us(self) -> None:
        body = sms_service.to_gsm7_body("Bonjour, votre site est prêt")
        assert "STOP" not in body and "36180" not in body
        assert body == "Bonjour, votre site est pret"

    def test_trims_surrounding_whitespace(self) -> None:
        assert sms_service.to_gsm7_body("   Coucou   ") == "Coucou"

    def test_marketing_segments_reserve_the_mention_of_the_destination_country(self) -> None:
        body = "a" * 146
        assert sms_service.marketing_segment_count(body, country="FR") == 1
        assert sms_service.marketing_segment_count(body, country="CH") == 2


class TestPriceEstimate:
    def test_france_reads_the_account_rate_and_other_countries_the_public_list(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "smsmode_price_per_segment_eur", 0.061)
        assert SmsPricing.estimate_cents(1, country="FR") == 6
        assert SmsPricing.estimate_cents(2, country="FR") == 12
        assert SmsPricing.estimate_cents(1, country="CH") == 7
        assert SmsPricing.estimate_cents(2, country="CH") == 13
        assert SmsPricing.estimate_cents(1, country="BE") == 6
        assert SmsPricing.estimate_cents(1, country="CA") == 2

    def test_the_number_names_the_destination(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "smsmode_price_per_segment_eur", 0.061)
        assert SmsPricing.estimate_cents_for_number(2, to_e164="+41791234567") == 13
        assert SmsPricing.estimate_cents_for_number(1, to_e164="+33612345678") == 6
        # An unserved destination is estimated at the dearest listed price rather than at zero.
        assert SmsPricing.estimate_cents_for_number(1, to_e164="+447700900123") == 7

    def test_zero_segments_bills_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "smsmode_price_per_segment_eur", 0.061)
        assert SmsPricing.estimate_cents(0, country="FR") == 6

    def test_cents_format_for_the_activity_feed(self) -> None:
        assert SmsPricing.french_amount_label(13) == "13 c"
        assert SmsPricing.french_amount_label(120) == "1,20 €"


class TestLegalWindowGuard:
    def test_refuses_on_sunday(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(SmsSendWindow, "now", lambda self: datetime(2026, 8, 30, 12, 0))  # Sunday noon
        refusal = sms_service.legal_window_refusal()
        assert refusal is not None and "fenêtre légale" in refusal

    def test_refuses_before_opening(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(SmsSendWindow, "now", lambda self: datetime(2026, 8, 31, 7, 0))  # Monday 07:00
        assert sms_service.legal_window_refusal() is not None

    def test_allows_inside_window(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(SmsSendWindow, "now", lambda self: datetime(2026, 8, 31, 10, 0))  # Monday 10:00
        assert sms_service.legal_window_refusal() is None

    def test_a_swiss_prospect_is_spared_on_august_first_and_texted_on_july_fourteenth(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(SmsSendWindow, "now", lambda self: datetime(2026, 7, 14, 10, 0))  # Tuesday
        assert sms_service.legal_window_refusal("FR") is not None
        assert sms_service.legal_window_refusal("CH") is None
        monkeypatch.setattr(SmsSendWindow, "now", lambda self: datetime(2025, 8, 1, 10, 0))  # a Friday
        assert sms_service.legal_window_refusal("FR") is None
        refusal = sms_service.legal_window_refusal("CH")
        assert refusal is not None and "Europe/Zurich" in refusal


class TestMoStopParsing:
    def test_stop_flagged_by_body_stop(self) -> None:
        # smsmode flags a STOP opt-out with body.stop = true.
        assert mo_is_stop({"direction": "MO", "body": {"text": "STOP", "stop": True}}) is True

    def test_stop_detected_from_keyword_text(self) -> None:
        assert mo_is_stop({"body": {"text": "stop"}}) is True
        assert mo_is_stop({"body": {"text": "Désabonnement"}}) is True

    def test_non_stop_reply_is_not_stop(self) -> None:
        assert mo_is_stop({"body": {"text": "Oui ça m'intéresse", "stop": False}}) is False

    def test_sender_number_from_nested_recipient(self) -> None:
        assert mo_sender_number({"recipient": {"to": "33612345678"}}) == "33612345678"

    def test_sender_number_skips_the_short_code_of_a_documented_mo(self) -> None:
        payload = {"direction": "MO", "recipient": {"to": "36034"}, "from": "41791234567", "body": {"text": "STOP"}}
        assert mo_sender_number(payload) == "41791234567"

    def test_sender_number_skips_the_lettered_sender(self) -> None:
        assert mo_sender_number({"recipient": {"to": "Dibodev"}, "msisdn": "33612345678"}) == "33612345678"
        assert mo_sender_number({"recipient": {"to": "36034"}}) == ""

    def test_origin_message_id_and_ref_client(self) -> None:
        assert mo_origin_message_id({"originMessageId": "abc-123"}) == "abc-123"
        assert mo_ref_client({"refClient": "dlh-42"}) == "dlh-42"


class TestDlrParsing:
    def test_delivered_maps_to_delivered(self) -> None:
        assert classify_dlr("DELIVERED") == "delivered"
        assert classify_dlr("14") == "delivered"

    def test_undeliverable_maps_to_failed(self) -> None:
        # The « NON LIVRABLE / spam » case — the regression that left rows on « Envoyé ».
        assert classify_dlr("UNDELIVERABLE") == "failed"
        assert classify_dlr("UNDELIVERED") == "failed"
        assert classify_dlr("3524") == "failed"

    def test_in_transit_leaves_unchanged(self) -> None:
        assert classify_dlr("ENROUTE") is None
        assert classify_dlr("UNKNOWN") is None
        assert classify_dlr("") is None

    def test_message_id_tolerates_field_names(self) -> None:
        assert dlr_message_id({"messageId": "abc"}) == "abc"
        assert dlr_message_id({"message_id": "xyz"}) == "xyz"
        assert dlr_message_id({}) == ""

    def test_status_value_from_dict_or_string(self) -> None:
        assert dlr_status_value({"status": {"value": "UNDELIVERABLE"}}) == "UNDELIVERABLE"
        assert dlr_status_value({"status": "DELIVERED"}) == "DELIVERED"
        assert dlr_status_value({"statusCode": "3524"}) == "3524"

    def test_status_detail_from_code_or_field(self) -> None:
        assert dlr_status_detail({"status": "3524"}) == "Spam (filtre anti-spam opérateur)"
        assert dlr_status_detail({"statusDetail": "Spam"}) == "Spam"
        assert dlr_status_detail({"status": "DELIVERED"}) is None

    def test_ref_client_fallback(self) -> None:
        assert dlr_ref_client({"refClient": "dlh-3"}) == "dlh-3"
        assert dlr_ref_client({}) == ""


def test_a_swiss_stop_reply_matches_its_sms_by_the_sender_number(db: Session) -> None:
    """Without originMessageId nor refClient, the number in ``from`` still finds the Swiss SMS it answers."""
    swiss_sms = SmsMessage(
        user_id=7, prospect_id=3, to_e164="+41791234567", sender="Dibodev", body="Bonjour", status="sent", segments=1
    )
    db.add(swiss_sms)
    db.commit()

    matched = _match_stop_message(db, {"direction": "MO", "recipient": {"to": "36034"}, "from": "41791234567"})

    assert matched is not None and matched.id == swiss_sms.id
