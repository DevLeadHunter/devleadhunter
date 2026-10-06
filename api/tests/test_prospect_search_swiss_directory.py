"""The Swiss directory: the search.ch entry of a candidate, its asterisk refusing advertising, its email and website."""

import asyncio
from typing import Any

import httpx
import pytest

import services.prospect_search.swiss_directory as swiss_directory_module
from enums.prospect_search import CandidateOrigin, CandidateRejectReason, CandidateStatus, EmailProofLevel
from enums.website_status import WebsiteStatus
from models.prospect_search_candidate import ProspectSearchCandidate
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_store import CandidateStore
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.contact_finder import ContactFinder
from services.prospect_search.search_judge import SearchJudge
from services.prospect_search.swiss_directory import (
    SwissDirectory,
    SwissDirectoryEntry,
    SwissDirectoryUnavailableError,
)
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
_RESULT_LIST_PAGE = (
    '<ol class="tel-results tel-entries"><li class="tel-person"><article class="tel-resultentry">'
    '<h1><a href="/tel/saxon/route-de-pro-bovey-12/jean-paul-rochat" data-stats="x">Rochat, Jean-Paul</a></h1>'
    '<ul><li><a class="tel-result-action" href="tel:+41277440001" data-entrytype="Private">027 744 00 01</a></li></ul>'
    "</article></li>"
    '<li class="tel-commercial"><article class="tel-resultentry"><div class="tel-categories">Garage</div>'
    '<h1><a href="/tel/saxon/route-du-leman-62/zodiac" data-stats="x">Zodiac</a></h1>'
    '<div class="tel-context"><span class="sl_context_label">Zusatzzeile: </span>Rochat Jean-Paul</div>'
    '<ul><li><a class="tel-result-action" href="tel:+41790000002" data-entrytype="Business">079 000 00 02 *</a></li></ul>'
    "</article></li></ol>"
    '<ol class="tel-results"><li class="tel-ad"><article>'
    '<h1><a href="/tel/saxon/route-du-village-93/carrieres-de-saxon">Carrières de Saxon</a></h1>'
    "</article></li></ol>"
)
_VCARD = (
    "BEGIN:VCARD\r\n"
    "TEL;TYPE=WORK,pref:+41277444748\r\n"
    "TEL;TYPE=WORK,CELL:+41760000013\r\n"
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
    """A directory answering prepared entries, and remembering the numbers it was asked."""

    def __init__(
        self,
        entry: SwissDirectoryEntry | None,
        entries_by_name: list[SwissDirectoryEntry] | None = None,
        entry_pages: dict[str, SwissDirectoryEntry] | None = None,
    ) -> None:
        self._entry = entry
        self._entries_by_name = entries_by_name or []
        self._entry_pages = entry_pages or {}
        self.asked_phones: list[str | None] = []
        self.asked_names: list[str] = []
        self.is_unavailable = False

    async def entry_for_phone(self, phone: str | None) -> SwissDirectoryEntry | None:
        self.asked_phones.append(phone)
        if self.is_unavailable:
            raise SwissDirectoryUnavailableError("search.ch answered 429")
        return self._entry

    async def entries_for_name(self, name: str, town: str) -> list[SwissDirectoryEntry]:
        self.asked_names.append(name)
        return self._entries_by_name

    async def entry_at(self, entry_url: str) -> SwissDirectoryEntry:
        listed = next((entry for entry in self._entries_by_name if entry.url == entry_url), _entry(url=entry_url))
        return self._entry_pages.get(entry_url, listed)


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


def test_the_asterisk_written_after_a_second_number_refuses_advertising() -> None:
    page = (
        '<a href="tel:+41277761523" data-entrytype="Business">027 776 15 23</a>'
        '<tr><th>Mobile Paul</th><td><span class="sl-nowrap"><a href="tel:+41790000003" title="Appeler" '
        'data-entrytype="Business">079 000 00 03</a> <span title="* Ne souhaite pas de publicité">*</span></span></td>'
    )

    assert SwissDirectory.parse_entry(_ENTRY_URL, page, "").refuses_advertising is True


def test_the_vcard_gives_the_email_the_website_and_the_mobiles() -> None:
    entry = SwissDirectory.parse_entry(_ENTRY_URL, _PAGE_WITHOUT_ASTERISK, _VCARD)

    assert entry.emails == ("garageduvalais@hotmail.com",)
    assert entry.websites == ("http://www.garage-du-valais-saxon-entretien-et-reparation-de-toutes-marques.ch/",)
    assert entry.mobile_phones == ("+41760000013",)


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
    facts = _facts(name="Solis Solutions Tech Sàrl", city="Payerne", phone="079 000 00 14")

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
                name="Atelier E SA - Paul Rochat, Electriciens, installateurs à Martigny",
                is_business=True,
                emails=("paul@atelier-e.swiss",),
            )
        ),
    )

    assert (facts.email, facts.email_proof_level) == ("paul@atelier-e.swiss", EmailProofLevel.DIRECTORY.value)


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


def _directory_answering(pages: dict[str, tuple[int, str]]) -> httpx.MockTransport:
    """A search.ch stand-in answering each path (with its query) from *pages*."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.url.path + (f"?{request.url.query.decode()}" if request.url.query else "")
        status, body = pages.get(key, pages.get(request.url.path, (404, "")))
        return httpx.Response(status, text=body)

    return httpx.MockTransport(handler)


def _read_directory(monkeypatch: pytest.MonkeyPatch, pages: dict[str, tuple[int, str]], phone: str) -> Any:
    transport = _directory_answering(pages)
    real_client = httpx.AsyncClient

    def client_with_transport(**kwargs: Any) -> httpx.AsyncClient:
        return real_client(transport=transport, **kwargs)

    monkeypatch.setattr(swiss_directory_module.httpx, "AsyncClient", client_with_transport)
    return asyncio.run(SwissDirectory().entry_for_phone(phone))


def test_a_number_listed_once_opens_its_entry_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    entry_page = _PAGE_WITH_ASTERISK + '<a href="/tel/vcard/SV-Automobiles.fr.vcf?key=03cba86fb3ea3899">vCard</a>'
    entry = _read_directory(
        monkeypatch,
        {
            "/tel/": (200, entry_page),
            "/tel/vcard/SV-Automobiles.fr.vcf": (200, "EMAIL:svauto.vevey@gmail.com\r\n"),
        },
        "021 922 91 68",
    )

    assert entry is not None
    assert (entry.refuses_advertising, entry.emails) == (True, ("svauto.vevey@gmail.com",))


def test_a_number_listed_several_times_opens_the_first_entry_of_the_list(monkeypatch: pytest.MonkeyPatch) -> None:
    listing = '<a href="https://search.ch/tel/clarens/rue-du-lac-133/garage-ad">ad</a><a href="/tel/saxon/route-du-leman-34/garage-du-valais-sarl">Garage du Valais</a>'
    entry_page = _PAGE_WITHOUT_ASTERISK + '<a href="/tel/vcard/Garage-du-Valais.fr.vcf?key=ab476683a7d58228">vCard</a>'
    entry = _read_directory(
        monkeypatch,
        {
            "/tel/": (200, listing),
            "/tel/saxon/route-du-leman-34/garage-du-valais-sarl.fr.html": (200, entry_page),
            "/tel/vcard/Garage-du-Valais.fr.vcf": (200, _VCARD),
        },
        "027 744 47 48",
    )

    assert entry is not None
    assert entry.url == "https://search.ch/tel/saxon/route-du-leman-34/garage-du-valais-sarl.fr.html"
    assert entry.emails == ("garageduvalais@hotmail.com",)


def test_an_unlisted_number_has_no_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _read_directory(monkeypatch, {"/tel/": (404, "")}, "021 925 36 66") is None


def test_the_asterisk_of_a_local_ch_extract_refuses_advertising_without_the_directory() -> None:
    facts = _facts(name="Garage des Alpes Rochat Sàrl", city="Saxon", phone="027 744 00 05")
    page = {
        "organic": [
            {
                "link": "https://www.local.ch/fr/d/saxon/1907/garage/garage-des-alpes-rochat-sarl-rsl0p",
                "title": "Garage des Alpes Rochat Sàrl - Saxon",
                "description": "Adresse: Route du Léman 55, 1907 Saxon ; Numéro de téléphone: 027 744 00 05* ; "
                "Email: garagedesalpes.rochat@netplus.ch",
            }
        ]
    }

    asyncio.run(
        CandidateVerifier(_OnePageClient(page), _SilentJudge(), _ScriptedDirectory(None)).verify(facts, _GARAGE)  # type: ignore[arg-type]
    )

    assert facts.refuses_advertising is True
    assert CandidateDecision.decide(facts, _GARAGE, _EMAIL_SEARCH).reject_reason == CandidateRejectReason.NO_ADVERTISING


def test_the_website_a_local_ch_extract_lists_is_the_business_s_website() -> None:
    facts = _facts(name="JANTES ALU", city="Saxon", phone="027 744 31 12")
    page = {
        "organic": [
            {
                "link": "https://www.local.ch/fr/d/saxon/1907/garage/jantes-alu-k2Hq",
                "title": "JANTES ALU - Saxon",
                "description": "Adresse: Route du Léman 12, 1907 Saxon ; Site web: www.jantes-alu.ch ; "
                "Email: pacherix@bluewin.ch",
            }
        ]
    }

    asyncio.run(
        CandidateVerifier(_OnePageClient(page), _SilentJudge(), _ScriptedDirectory(None)).verify(facts, _GARAGE)  # type: ignore[arg-type]
    )

    assert facts.website == "www.jantes-alu.ch"
    assert CandidateDecision.decide(facts, _GARAGE, _EMAIL_SEARCH).reject_reason == CandidateRejectReason.HAS_WEBSITE


def test_a_whatsapp_link_given_as_the_listing_s_website_is_not_its_website() -> None:
    facts = _facts(name="Garage Auto Express", city="Martigny", phone="079 123 45 67")
    page = {"knowledge": {"name": "Garage Auto Express", "site": "https://wa.me/41791234567"}, "organic": []}

    asyncio.run(
        CandidateVerifier(_OnePageClient(page), _SilentJudge(), _ScriptedDirectory(None)).verify(facts, _GARAGE)  # type: ignore[arg-type]
    )

    assert facts.website is None


def test_the_legal_notice_showing_the_number_gives_the_business_s_website() -> None:
    facts = _facts(name="Garage Auto Express", city="Martigny", phone="079 123 45 67")
    page = {
        "organic": [
            {
                "link": "https://www.easy-autos.ch/mentions-legales",
                "title": "Mentions légales - Easy Autos",
                "description": "Mentions légales. Easy Autos Sàrl, Rue du Simplon 12, 1920 Martigny. "
                "Téléphone : 079 123 45 67.",
            }
        ]
    }

    asyncio.run(ContactFinder(_OnePageClient(page), _SilentJudge()).find(facts, _GARAGE))  # type: ignore[arg-type]

    assert facts.website == "https://www.easy-autos.ch/"
    assert facts.website_status == WebsiteStatus.LIVE.value


def test_the_asterisk_found_by_the_phone_search_refuses_advertising() -> None:
    facts = _facts(name="Garage Auto Express", city="Martigny", phone="027 722 11 22")
    page = {
        "organic": [
            {
                "link": "https://www.local.ch/fr/d/martigny/1920/garage/easy-autos-sarl-p3Xz",
                "title": "Easy Autos Sàrl - Martigny",
                "description": "Adresse: Rue du Simplon 12, 1920 Martigny ; Numéro de téléphone: 027 722 11 22*",
            }
        ]
    }

    asyncio.run(ContactFinder(_OnePageClient(page), _SilentJudge()).find(facts, _GARAGE))  # type: ignore[arg-type]

    assert facts.refuses_advertising is True


def test_a_result_list_gives_each_entry_its_extra_line_and_its_asterisk() -> None:
    entries = SwissDirectory.parse_result_list(_RESULT_LIST_PAGE)

    assert [(entry.name, entry.is_business, entry.refuses_advertising, entry.extra_line) for entry in entries] == [
        ("Rochat, Jean-Paul", False, False, ""),
        ("Zodiac", True, True, "Rochat Jean-Paul"),
    ]
    assert entries[1].url == "https://search.ch/tel/saxon/route-du-leman-62/zodiac.fr.html"


def test_a_business_named_after_its_owner_refuses_advertising_on_its_entry_found_by_name() -> None:
    facts = _facts(name="Rochat Jean Paul", city="Saxon", phone="027 744 00 04")
    entries = SwissDirectory.parse_result_list(_RESULT_LIST_PAGE)

    _verify(facts, _ScriptedDirectory(None, entries_by_name=entries))

    assert facts.refuses_advertising is True
    assert CandidateDecision.decide(facts, _GARAGE, _EMAIL_SEARCH).reject_reason == CandidateRejectReason.NO_ADVERTISING


def test_an_entry_of_another_business_found_by_name_brings_nothing() -> None:
    facts = _facts(name="Garage des Bains SA", city="Saillon", phone="027 744 27 28")
    neighbour = _entry(name="Carrosserie du Rhône", is_business=True, refuses_advertising=True)

    _verify(facts, _ScriptedDirectory(None, entries_by_name=[neighbour]))

    assert facts.refuses_advertising is False


def test_the_page_of_an_entry_found_by_name_gives_the_asterisk_the_list_left_out() -> None:
    facts = _facts(name="Rochat Paul & Fils", city="Savièse", phone="079 000 00 15", trade_key="paysagiste")
    listed = _entry(
        url="https://search.ch/tel/saviese/chemin-de-pradzere-54/rochat-paul-fils.fr.html",
        name="Rochat Paul & Fils",
        is_business=True,
    )
    page = _entry(
        url=listed.url,
        name="Rochat Paul & Fils, Paysagistes à Savièse",
        is_business=True,
        refuses_advertising=True,
        emails=("info@rochat-paysagiste.ch",),
    )

    _verify(facts, _ScriptedDirectory(None, entries_by_name=[listed], entry_pages={listed.url: page}))

    assert facts.refuses_advertising is True
    assert facts.email == "info@rochat-paysagiste.ch"


def test_an_entry_page_is_read_with_its_vcard(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _directory_answering(
        {
            "/tel/saxon/route-du-leman-34/garage-du-valais-sarl.fr.html": (
                200,
                _PAGE_WITHOUT_ASTERISK + '<a href="/tel/vcard/Garage-du-Valais.fr.vcf?key=ab476683a7d58228">vCard</a>',
            ),
            "/tel/vcard/Garage-du-Valais.fr.vcf": (200, _VCARD),
        }
    )
    real_client = httpx.AsyncClient

    def client_with_transport(**kwargs: Any) -> httpx.AsyncClient:
        return real_client(transport=transport, **kwargs)

    monkeypatch.setattr(swiss_directory_module.httpx, "AsyncClient", client_with_transport)
    entry = asyncio.run(
        SwissDirectory().entry_at("https://search.ch/tel/saxon/route-du-leman-34/garage-du-valais-sarl.fr.html")
    )

    assert entry is not None
    assert entry.emails == ("garageduvalais@hotmail.com",)


@pytest.mark.parametrize(
    "link",
    [
        "https://www.gardening-company-comparison.ch/en/d/gardening-companies/r-a-paysagiste-d:x1",
        "https://www.horticole-comparatif.ch/d/horticultures/heritier-creation-d:5XhkSzmXq",
        "https://gardening.gartenbauvergleich.ch/d/gardening-companies/ns-design-d:9ghqSXRB7",
        "https://autofit.ch/fr/garage/garage-des-bains/",
        "https://www.411habitation.com/elagueur/lanaudiere/saint-paul-4/arbo-douceur-inc.htm",
    ],
)
def test_a_comparison_site_or_a_network_page_is_never_a_website(link: str) -> None:
    host = link.split("/")[2].removeprefix("www.")

    assert CandidateVerifier.is_known_third_party(link, host) is True


def test_the_directory_is_asked_the_name_without_its_legal_form() -> None:
    directory = _ScriptedDirectory(None)

    _verify(_facts(name="Conthey Centre Automobile Sàrl", city="Conthey", phone="078 000 00 16"), directory)

    assert directory.asked_names == ["Conthey Centre Automobile"]


def test_a_directory_that_does_not_answer_leaves_the_candidate_to_confirm() -> None:
    facts = _facts(email="svauto.vevey@gmail.com", email_proof_level=EmailProofLevel.PUBLISHED.value)
    directory = _ScriptedDirectory(None)
    directory.is_unavailable = True

    _verify(facts, directory)
    verdict = CandidateDecision.decide(facts, _GARAGE, _EMAIL_SEARCH)

    assert verdict.status == CandidateStatus.TO_CONFIRM
    assert verdict.detail == "L'annuaire suisse n'a pas répondu : l'astérisque « pas de publicité » n'a pas été lu."


def test_a_refused_lookup_raises_while_an_unlisted_number_has_no_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SwissDirectoryUnavailableError):
        _read_directory(monkeypatch, {"/tel/": (429, "")}, "021 925 36 66")


def test_an_entry_page_without_vcard_still_gives_its_asterisk(monkeypatch: pytest.MonkeyPatch) -> None:
    entry = _read_directory(
        monkeypatch,
        {
            "/tel/": (200, '<a href="/tel/vevey/avenue-reller-25/sv-automobiles-sarl">SV</a>'),
            "/tel/vevey/avenue-reller-25/sv-automobiles-sarl.fr.html": (200, _PAGE_WITH_ASTERISK),
        },
        "021 922 91 68",
    )

    assert entry is not None and entry.refuses_advertising is True
