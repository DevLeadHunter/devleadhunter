"""The Swiss directory: the search.ch entry of a candidate, its asterisk refusing advertising, its email and website."""

import asyncio
from typing import Any

import pytest

from enums.prospect_search import CandidateOrigin, CandidateRejectReason, CandidateStatus, EmailProofLevel
from enums.website_status import WebsiteStatus
from models.prospect_search_candidate import ProspectSearchCandidate
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_store import CandidateStore
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.search_judge import SearchJudge
from services.prospect_search.swiss_directory import SwissDirectory, SwissDirectoryEntry
from services.prospect_search.trade_catalog import TradeCatalog
from services.website_liveness_service import website_liveness_service

_GARAGE = TradeCatalog.resolve("garage")
_EMAIL_SEARCH = SearchCriteria(channel="email", only_without_website=True, minimum_rating=None)  # type: ignore[arg-type]
_ENTRY_URL = "https://search.ch/tel/vevey/avenue-reller-25/sv-automobiles-sarl.fr.html"

_PAGE_WITH_ASTERISK = (
    "<title>SV Automobiles Sàrl, Garage à Vevey - search.ch</title>"
    '<a href="tel:+41219229168" data-entrytype="Business" title="Appeler">021 922 91 68 *</a>'
    '<abbr title="ne souhaite pas de publicité">*</abbr>'
)
_PAGE_WITHOUT_ASTERISK = (
    "<title>Garage du Valais Sàrl, Atelier mécanique à Saxon - search.ch</title>"
    '<a href="tel:+41277444748" data-entrytype="Private" title="Appeler">027 744 47 48</a>'
)
_VCARD = (
    "BEGIN:VCARD\r\n"
    "TEL;TYPE=WORK,pref:+41277444748\r\n"
    "TEL;TYPE=WORK,CELL:+41764354460\r\n"
    "EMAIL:GarageDuValais@Hotmail.com\r\n"
    "URL:http://www.garage-du-valais-saxon-entretien-et-reparation-de-toutes-marq\r\n"
    " ues.ch/\r\n"
    "URL:http://search.ch/tel/saxon/route-du-leman-34/garage-du-valais-sarl.fr.h\r\n"
    " tml\r\n"
    "END:VCARD\r\n"
)


class _OnePageClient:
    """Stands in for Bright Data: always answers the same parsed page."""

    def __init__(self, page: dict[str, Any] | None) -> None:
        self._page = page

    async def google_parsed(self, query: str, *, country: str = "FR", start: int = 0, local: bool = False) -> Any:
        return self._page


class _SilentJudge(SearchJudge):
    """A judge that is never needed by these pages."""

    async def judge(self, **_: object) -> None:
        return None


class _ScriptedDirectory(SwissDirectory):
    """A directory answering one prepared entry, and remembering the numbers it was asked."""

    def __init__(self, entry: SwissDirectoryEntry | None) -> None:
        self._entry = entry
        self.asked_phones: list[str | None] = []

    async def entry_for_phone(self, phone: str | None) -> SwissDirectoryEntry | None:
        self.asked_phones.append(phone)
        return self._entry


@pytest.fixture(autouse=True)
def no_website_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    async def live(website: str | None) -> WebsiteStatus | None:
        return WebsiteStatus.LIVE if website else None

    async def no_front_page(domain: str) -> tuple[str, str] | None:
        return None

    monkeypatch.setattr(website_liveness_service, "check_website_status", live)
    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(no_front_page))


def _facts(**overrides: object) -> CandidateFacts:
    values: dict[str, object] = {
        "name": "SV AUTOMOBILES sàrl",
        "trade_key": "garage",
        "country": "CH",
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "city": "Vevey",
        "phone": "021 922 91 68",
        "google_category": "Garage automobile",
    }
    values.update(overrides)
    return CandidateFacts(**values)  # type: ignore[arg-type]


def _entry(**overrides: object) -> SwissDirectoryEntry:
    values: dict[str, object] = {
        "url": _ENTRY_URL,
        "name": "SV Automobiles Sàrl, Garage à Vevey",
        "is_business": False,
        "refuses_advertising": False,
        "emails": (),
        "websites": (),
        "mobile_phones": (),
    }
    values.update(overrides)
    return SwissDirectoryEntry(**values)  # type: ignore[arg-type]


def _verify(facts: CandidateFacts, directory: _ScriptedDirectory) -> None:
    verifier = CandidateVerifier(_OnePageClient({"organic": []}), _SilentJudge(), directory)  # type: ignore[arg-type]
    asyncio.run(verifier.verify(facts, _GARAGE))


def test_a_number_ending_with_the_asterisk_refuses_advertising() -> None:
    entry = SwissDirectory.parse_entry(_ENTRY_URL, _PAGE_WITH_ASTERISK, "")

    assert entry.refuses_advertising is True
    assert entry.is_business is True
    assert entry.name == "SV Automobiles Sàrl, Garage à Vevey"
    private_entry = SwissDirectory.parse_entry(_ENTRY_URL, _PAGE_WITHOUT_ASTERISK, "")
    assert (private_entry.refuses_advertising, private_entry.is_business) == (False, False)


def test_the_vcard_gives_the_email_the_website_and_the_mobiles() -> None:
    entry = SwissDirectory.parse_entry(_ENTRY_URL, _PAGE_WITHOUT_ASTERISK, _VCARD)

    assert entry.emails == ("garageduvalais@hotmail.com",)
    assert entry.websites == ("http://www.garage-du-valais-saxon-entretien-et-reparation-de-toutes-marques.ch/",)
    assert entry.mobile_phones == ("+41764354460",)


def test_only_a_swiss_number_is_looked_up() -> None:
    assert SwissDirectory.national_number("+41 21 922 91 68") == "0219229168"
    assert SwissDirectory.national_number("079 123 45 67") == "0791234567"
    assert SwissDirectory.national_number("+33 6 12 34 56 78") is None
    assert SwissDirectory.national_number(None) is None


def test_a_candidate_refusing_advertising_is_discarded_with_its_proof() -> None:
    facts = _facts()

    _verify(facts, _ScriptedDirectory(_entry(refuses_advertising=True, emails=("svauto.vevey@gmail.com",))))
    verdict = CandidateDecision.decide(facts, _GARAGE, _EMAIL_SEARCH)

    assert verdict.status == CandidateStatus.REJECTED
    assert verdict.reject_reason == CandidateRejectReason.NO_ADVERTISING
    assert {"fact": "no_advertising", "value": "*", "source": "Annuaire search.ch", "url": _ENTRY_URL} in facts.evidence


def test_the_directory_email_of_the_business_keeps_it_for_an_email_search() -> None:
    facts = _facts(name="Garage du Valais Sàrl", city="Saxon", phone="027 744 47 48")

    _verify(
        facts,
        _ScriptedDirectory(
            _entry(name="Garage du Valais Sàrl, Atelier mécanique à Saxon", emails=("garageduvalais@hotmail.com",))
        ),
    )

    assert facts.email == "garageduvalais@hotmail.com"
    assert facts.email_proof_level == EmailProofLevel.DIRECTORY.value
    assert CandidateDecision.decide(facts, _GARAGE, _EMAIL_SEARCH).status == CandidateStatus.KEPT


def test_the_website_the_directory_knows_discards_the_business() -> None:
    facts = _facts(name="Solis Solutions Tech Sàrl", city="Payerne", phone="079 579 84 97")

    _verify(
        facts,
        _ScriptedDirectory(
            _entry(
                name="Solis Solutions Tech Sàrl, Electricité à Payerne", websites=("http://www.solis-solutions.ch/",)
            )
        ),
    )

    assert facts.website == "http://www.solis-solutions.ch/"
    assert CandidateDecision.decide(facts, _GARAGE, _EMAIL_SEARCH).reject_reason == CandidateRejectReason.HAS_WEBSITE


def test_an_entry_naming_someone_else_only_brings_the_asterisk_of_the_number() -> None:
    facts = _facts()

    _verify(
        facts,
        _ScriptedDirectory(
            _entry(
                name="Dupont, Marcel",
                refuses_advertising=True,
                emails=("marcel.dupont@bluewin.ch",),
                websites=("http://dupont.ch",),
            )
        ),
    )

    assert facts.refuses_advertising is True
    assert facts.email is None
    assert facts.website is None


def test_a_business_outside_switzerland_is_never_looked_up() -> None:
    directory = _ScriptedDirectory(_entry(refuses_advertising=True))

    _verify(_facts(country="FR", city="Annecy", phone="04 50 12 34 56"), directory)

    assert directory.asked_phones == []


def test_the_refusal_survives_a_new_reading_of_the_stored_candidate() -> None:
    facts = _facts()
    facts.refuses_advertising = True
    facts.add_evidence("no_advertising", "*", source="Annuaire search.ch", url=_ENTRY_URL)
    row = ProspectSearchCandidate(
        search_id=1, user_id=1, trade="garage", origin=facts.origin, name=facts.name, country="CH"
    )
    CandidateStore.write_back(row, facts, CandidateDecision.decide(facts, _GARAGE, _EMAIL_SEARCH))

    assert CandidateStore.facts_of(row).refuses_advertising is True


def test_a_business_entry_found_by_the_number_gives_its_email_whatever_its_wording() -> None:
    facts = _facts(name="Atelier E SA", city="Martigny", phone="027 565 22 12", trade_key="electricien")

    _verify(
        facts,
        _ScriptedDirectory(
            _entry(
                name="Atelier E SA - Stéphane Juilliand, Electriciens, installateurs à Martigny",
                is_business=True,
                emails=("stephane@atelier-e.swiss",),
            )
        ),
    )

    assert (facts.email, facts.email_proof_level) == ("stephane@atelier-e.swiss", EmailProofLevel.DIRECTORY.value)


def test_a_marketplace_page_given_as_the_listing_s_website_is_not_its_website() -> None:
    facts = _facts(name="Garage Touring AC Sàrl", city="Romont", phone="026 652 40 10")
    page = {
        "knowledge": {
            "name": "Garage Touring AC Sàrl",
            "phone": "026 652 40 10",
            "site": "https://www.autoscout24.ch/fr/ip/garage-touring-romont-sarl-1680-romont?accountid=1357862",
        },
        "organic": [],
    }

    asyncio.run(
        CandidateVerifier(_OnePageClient(page), _SilentJudge(), _ScriptedDirectory(None)).verify(facts, _GARAGE)  # type: ignore[arg-type]
    )

    assert facts.website is None
