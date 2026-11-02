"""A French overseas number keeps its department's dial code, is told mobile or landline, and is never texted.

A Martinique mobile « 0696 12 34 56 » is ``+596 696 12 34 56``: dialled as ``+33 6 96 …`` it reaches nobody.
It is a mobile (the « Portable » mark of a lead, a WhatsApp link), but the prospection never texts the
overseas departments, nor a prospect living there whatever his number.
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from schemas.site_contact import SiteContactRequest
from scrappers.facebook_enrichment_scraper import _parse_phone
from services.prospect_phones import first_mobile_e164
from services.prospect_search.candidate_facts import CandidateFacts
from services.site_contact_email import SiteContactEmail
from services.sms.phone_normalizer import (
    PhoneNumberPlans,
    format_phone_for_display,
    format_phone_for_reader,
    format_phone_in_national_form,
    is_mobile_fr,
    to_e164,
    to_e164_fr,
    to_e164_mobile,
    to_served_mobile,
)
from services.sms_prospecting_rules import SmsProspectingRules


@pytest.mark.parametrize(
    "written",
    ["0696 12 34 56", "06 96 12 34 56", "0696123456", "+596 696 12 34 56", "00596 696 12 34 56", "+33 6 96 12 34 56"],
)
def test_a_martinique_mobile_takes_the_martinique_dial_code_however_it_is_written(written: str) -> None:
    assert to_e164_fr(written) == "+596696123456"
    assert to_e164(written, country="FR") == "+596696123456"


def test_each_overseas_department_gets_its_own_dial_code() -> None:
    assert to_e164_fr("0596 51 62 52") == "+596596516252"
    assert to_e164_fr("0690 12 34 56") == "+590690123456"
    assert to_e164_fr("0694 12 34 56") == "+594694123456"
    assert to_e164_fr("0262 12 34 56") == "+262262123456"
    assert to_e164_fr("0692 12 34 56") == "+262692123456"
    assert to_e164_fr("0639 12 34 56") == "+262639123456"
    assert to_e164_fr("+262 269 61 23 45") == "+262269612345"


def test_a_mainland_number_keeps_plus_thirty_three() -> None:
    assert to_e164_fr("06 12 34 56 78") == "+33612345678"
    assert to_e164_fr("01 23 45 67 89") == "+33123456789"
    assert to_e164_fr("+33 9 72 12 34 56") == "+33972123456"


def test_a_martinique_mobile_is_a_mobile_but_never_one_the_prospection_texts() -> None:
    assert PhoneNumberPlans.is_mobile_line("0696 12 34 56", country="FR") is True
    assert PhoneNumberPlans.mobile_of_country("0696 12 34 56", country="FR") is None
    assert is_mobile_fr("0696 12 34 56") is False
    assert to_served_mobile("0696 12 34 56") is None


def test_a_martinique_landline_is_no_mobile() -> None:
    assert PhoneNumberPlans.is_mobile_line("0596 51 62 52", country="FR") is False
    assert to_e164_mobile("0596 51 62 52") is None
    assert to_e164_mobile("+596 596 50 58 09") is None


def test_an_overseas_number_reads_in_its_local_national_form() -> None:
    assert format_phone_for_display("+596 696 12 34 56") == "0696 12 34 56"
    assert format_phone_in_national_form("+596 596 50 58 09", country="FR") == "0596 50 58 09"
    assert format_phone_in_national_form("+596 696 12 34 56", country="CH") is None
    assert format_phone_for_reader("+596 696 12 34 56", number_country="FR", reader_country="FR") == "0696 12 34 56"


def test_a_lead_with_a_martinique_mobile_is_marked_mobile() -> None:
    facts = CandidateFacts(name="Garage Eden Meca", trade_key="garage", country="FR", origin="google_local")
    facts.phone = "+596 696 80 10 23"

    assert facts.has_mobile_phone is True


def test_a_lead_with_a_martinique_number_and_no_address_is_not_abroad() -> None:
    facts = CandidateFacts(name="Garage Universel", trade_key="garage", country="FR", origin="google_local")
    facts.phone = "+596 596 50 03 43"

    assert facts.is_abroad is False


def test_a_martinique_number_on_a_swiss_lead_is_abroad() -> None:
    facts = CandidateFacts(name="Garage du Lac", trade_key="garage", country="CH", origin="google_local")
    facts.phone = "+596 596 50 03 43"

    assert facts.is_abroad is True


def test_a_facebook_page_s_martinique_number_is_read_in_its_national_form() -> None:
    assert _parse_phone("Garage · +596 696 04 04 25 · Le Lamentin", country="FR") == "0696 04 04 25"
    assert _parse_phone("Appelez le 0696 04 04 25", country="FR") == "0696 04 04 25"


def test_the_whatsapp_link_of_a_visitor_s_martinique_mobile_dials_plus_five_nine_six() -> None:
    request = SiteContactRequest(
        name="Marie", email="marie@example.com", phone="0696 12 34 56", message="Bonjour, un devis ?"
    )

    rendered = SiteContactEmail.render(request, datetime(2026, 11, 2, 9, 0))

    assert "https://wa.me/596696123456" in rendered.html
    assert "tel:+596696123456" in rendered.html


def _french_prospect(*, address: str | None, phones: list[str]) -> SimpleNamespace:
    return SimpleNamespace(id=7, country="FR", address=address, phones=phones, phone=phones[0] if phones else None)


def test_no_prospecting_sms_reaches_a_martinique_prospect_even_with_a_mainland_mobile() -> None:
    prospect = _french_prospect(address="Le Lamentin 97232, Martinique", phones=["06 12 34 56 78"])

    assert first_mobile_e164(prospect) is None
    assert SmsProspectingRules.country_refusal(prospect) == "Pas de SMS de prospection en outre-mer (Martinique)"
    assert SmsProspectingRules.automatic_country_refusal(prospect) is not None


def test_a_prospect_placed_in_martinique_by_his_number_alone_is_not_texted_either() -> None:
    prospect = _french_prospect(address=None, phones=["0596 51 62 52", "06 12 34 56 78"])

    assert first_mobile_e164(prospect) is None


def test_a_mainland_prospect_is_still_texted_on_his_mobile() -> None:
    prospect = _french_prospect(address="12 Rue Nationale, 41000 Blois", phones=["02 54 00 00 00", "06 12 34 56 78"])

    assert SmsProspectingRules.country_refusal(prospect) is None
    assert first_mobile_e164(prospect) == "+33612345678"
