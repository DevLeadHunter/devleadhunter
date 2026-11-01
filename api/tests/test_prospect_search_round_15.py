"""
Round 15 of the search training (searches n° 18 and 20, Perpignan's landscapers and Swiss garages): a Facebook page
taken on generic words, another business's email or page, a network and a brand's dealer, an email published beside
the business's own mobile, a listing filed under another trade, a website Google did not show, a domain holding no
site. Each case is a real one, its names, numbers and people replaced.
"""

import asyncio
from typing import Any

import pytest

from enums.prospect_search import (
    CandidateOrigin,
    CandidateRejectReason,
    CandidateStatus,
    EmailProofLevel,
    ProspectSearchChannel,
)
from enums.website_status import WebsiteStatus
from services.decision_maker.french_departments import FrenchDepartments
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.french_registry import FrenchRegistry
from services.prospect_search.network_outlets import NetworkOutlets
from services.prospect_search.search_judge import JudgedEmail, JudgeVerdict, SearchJudge, SearchResultLine
from services.prospect_search.trade_catalog import TradeCatalog
from services.website_liveness_service import website_liveness_service

_LANDSCAPER = TradeCatalog.resolve("paysagiste")
_GARAGE = TradeCatalog.resolve("garage")
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=4.0)


class _OnePageClient:
    """Stands in for Bright Data: always answers the same parsed page."""

    def __init__(self, page: dict[str, Any] | None) -> None:
        self._page = page

    async def google_parsed(self, query: str, *, country: str = "FR", start: int = 0, local: bool = False) -> Any:
        return self._page


class _ScriptedJudge(SearchJudge):
    """A judge answering a prepared verdict."""

    def __init__(self, verdict: JudgeVerdict | None = None) -> None:
        self._verdict = verdict

    async def judge(self, **_: object) -> JudgeVerdict | None:
        return self._verdict


@pytest.fixture(autouse=True)
def offline_web(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every website answers, no domain shows a front page and no town is a commune of the cases."""

    async def live(website: str | None) -> WebsiteStatus | None:
        return WebsiteStatus.LIVE if website else None

    async def no_front_page(domain: str) -> tuple[str, str] | None:
        return None

    async def no_commune(town: str) -> list[dict[str, Any]]:
        return []

    monkeypatch.setattr(website_liveness_service, "check_website_status", live)
    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(no_front_page))
    monkeypatch.setattr(FrenchDepartments, "_communes_named", staticmethod(no_commune))


def _facts(name: str, town: str, *, trade: str = "garage", country: str = "CH", **overrides: object) -> CandidateFacts:
    """A listing of the search, in *town*."""
    values: dict[str, object] = {
        "name": name,
        "trade_key": trade,
        "country": country,
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "city": town,
        "searched_city": town,
        "google_category": "Paysagiste" if trade == "paysagiste" else "Garage automobile",
        "google_rating": 5.0,
        "google_reviews_count": 12,
        "is_verified": True,
    }
    values.update(overrides)
    return CandidateFacts(**values)  # type: ignore[arg-type]


def _line(link: str, title: str, description: str) -> SearchResultLine:
    return SearchResultLine(
        link=link, host=link.split("/")[2].removeprefix("www."), title=title, description=description
    )


def _verify(facts: CandidateFacts, results: list[dict[str, str]], verdict: JudgeVerdict | None, trade: Any) -> None:
    verifier = CandidateVerifier(_OnePageClient({"organic": results}), _ScriptedJudge(verdict))  # type: ignore[arg-type]
    asyncio.run(verifier.verify(facts, trade))


def test_a_facebook_page_sharing_only_the_trade_and_the_departement_number_is_another_s() -> None:
    """« Taille Exemple Jardinier Perpignan 66 » is not « Jules Le Jardinier - 66 », a gardener with a site of its own."""
    facts = _facts("Taille Exemple Jardinier Perpignan 66", "Perpignan", trade="paysagiste", country="FR", city=None)
    pages = [
        _line(
            "https://www.facebook.com/p/Jules-Le-Jardinier-66-100000000000066/",
            "Jules Le Jardinier - 66 | Perpignan",
            "L'entreprise Jules Le Jardinier-66 est là pour vous : élagage, abattage, évacuation des déchets.",
        ),
        _line(
            "https://www.facebook.com/p/Taille-Exemple-100000000000067/",
            "Taille Exemple | Perpignan",
            "Taille Exemple, jardinier à Perpignan : taille de haies, tonte.",
        ),
    ]

    assert [CandidateVerifier.is_facebook_page_of(page, facts, _LANDSCAPER) for page in pages] == [False, True]


def test_an_email_on_the_page_of_another_business_at_another_street_is_not_its_own() -> None:
    """Garage Exemple, Rte de la Bourgeoisie 5: the page of « Auto Modele », Route des Ateliers 8, gives its email."""
    facts = _facts("Garage Exemple", "Vétroz", address="Rte de la Bourgeoisie 5, 1963 Vétroz", phone="079 000 00 10")
    result = {
        "link": "https://autopro.ch/fr/garage/auto-modele/",
        "title": "Auto Modele - autopro",
        "description": "Auto Modele Jules Modele Route des Ateliers 8 1963 Vetroz. automodele@hotmail.com · "
        "http://auto-modele.ch.",
    }
    verdict = JudgeVerdict(
        owner_name="Jules Modele",
        owner_name_index=0,
        emails=[JudgedEmail(email="automodele@hotmail.com", result_index=0, belongs_to_business=True)],
    )

    _verify(facts, [result], verdict, _GARAGE)

    assert (facts.email, facts.owner_name) == (None, None)


def test_an_email_on_the_live_site_of_another_business_is_forgotten(monkeypatch: pytest.MonkeyPatch) -> None:
    """ABC Automobiles writes from « temoin-auto.ch », the live site of Temoin Auto: its email is that garage's."""
    facts = _facts(
        "ABC Automobiles",
        "Exempleville",
        email="info@temoin-auto.ch",
        email_proof_level=EmailProofLevel.GUESSED.value,
    )

    async def another_garage_s_site(domain: str) -> tuple[str, str] | None:
        return f"https://{domain}/", "<title>Temoin Auto, votre garage à Exempleville</title>"

    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(another_garage_s_site))

    asyncio.run(CandidateVerifier.consider_email_domain(facts, _GARAGE))
    verdict = CandidateDecision.decide(facts, _GARAGE, _EMAIL_ONLY)

    assert facts.email is None
    assert facts.evidence[-1]["source"] == "temoin-auto.ch est le site en ligne d'une autre entreprise"
    assert (verdict.status, verdict.reject_reason) == (CandidateStatus.REJECTED, CandidateRejectReason.NO_CONTACT)


def test_a_stop_and_go_partner_is_a_network_outlet() -> None:
    """« Garage Exemple Sàrl | stop+go | … », whose listing leads to « exemple.stopgo.ch »."""
    facts = _facts("Garage Exemple Sàrl", "Exempleville")

    assert NetworkOutlets.names_network("Garage Exemple Sàrl | stop+go | Garage automobiles à Exempleville")
    assert NetworkOutlets.is_network_page("http://www.exemple.stopgo.ch/")
    CandidateVerifier(_OnePageClient(None), _ScriptedJudge())._read_knowledge_panel(  # type: ignore[arg-type]
        facts, {"name": "Garage Exemple Sàrl | stop+go | Garage automobiles à Exempleville", "phone": "032 000 00 13"}
    )
    assert facts.is_chain


def test_a_page_of_a_brand_s_site_naming_the_garage_in_its_town_makes_it_the_brand_s_dealer() -> None:
    """« garage.toyota.ch/exemple-develier » lists Garage St-Exemple SA, Route de Delémont 12, Develier: a Toyota dealer."""
    facts = _facts("Garage St Exemple S.A.", "Develier", address="Rte de Delémont 12, 2802 Develier")
    results = [
        {
            "link": "https://garage.toyota.ch/exemple-develier/fr",
            "title": "Garage St-Exemple SA",
            "description": "Garage St-Exemple SA. Route de Delémont 12. 2802 Develier. +41 32 000 00 00",
        }
    ]

    _verify(facts, results, None, _GARAGE)
    verdict = CandidateDecision.decide(facts, _GARAGE, _EMAIL_ONLY)

    assert _GARAGE.brand_of_site("https://garage.toyota.ch/exemple-develier/fr") == "Toyota"
    assert _GARAGE.brand_of_site("https://www.toyota-exemple.ch/") is None
    assert (verdict.status, verdict.detail) == (
        CandidateStatus.REJECTED,
        "Agent ou concessionnaire Toyota : le patron ne décide pas seul.",
    )


def test_an_email_beside_the_business_s_own_mobile_on_a_page_naming_it_is_published_by_it() -> None:
    """A local bulletin writes « Jules Exemple • … Tél. 078 … • E-mail: jex.exemple@… »: same name, same mobile."""
    facts = _facts(
        "Jules Exemple", "Le Landeron", trade="paysagiste", address="2525 Le Landeron", phone="078 000 00 63"
    )
    line = _line(
        "https://www.bulletin-exemple.ch/",
        "ENCORE UN FÉRIÉ QUI TOMBE SUR UN WEEK-END",
        "Jules Exemple • Rue du Vignoble 1 • 2087 Cornaux. Tél. 078 000 00 63 • E-mail: jex.exemple@gmail.com.",
    )

    CandidateVerifier.offer_email_read_in(
        facts, "jex.exemple@gmail.com", EmailProofLevel.GUESSED, line, _LANDSCAPER, department=None, is_own_text=False
    )

    assert (facts.email, facts.email_proof_level) == ("jex.exemple@gmail.com", EmailProofLevel.PUBLISHED.value)


def test_a_listing_whose_company_is_filed_under_another_trade_waits_for_a_check() -> None:
    """« Au Jardin de l'Exemple », a landscaper on Google, is filed as a greengrocer (52.2A) since 1991."""
    facts = _facts(
        "Au Jardin De L'Exemple",
        "Perpignan",
        trade="paysagiste",
        country="FR",
        email="ecojardin@exemple.fr",
        email_proof_level=EmailProofLevel.PUBLISHED.value,
    )
    greengrocer = {
        "nom_complet": "AU JARDIN DE L'EXEMPLE",
        "etat_administratif": "A",
        "activite_principale": "52.2A",
        "siege": {"activite_principale": "52.2A", "code_postal": "66000"},
    }
    old_landscaper = {**greengrocer, "siege": {"activite_principale": "01.4A", "code_postal": "66000"}}

    FrenchRegistry.note_registered_activity(facts, [old_landscaper])
    assert facts.activity_of_another_trade is None

    FrenchRegistry.note_registered_activity(facts, [greengrocer])
    verdict = CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY)

    assert verdict.status == CandidateStatus.TO_CONFIRM
    assert verdict.detail == (
        "Le registre inscrit « AU JARDIN DE L'EXEMPLE » sous une autre activité (52.2A) : à vérifier, ce n'est "
        "peut-être pas un paysagiste."
    )


def test_the_domain_spelling_the_business_name_is_read_when_google_shows_no_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """« espaces-verts-exemple.fr » names Espaces Verts Exemple and its town: its site, which Google's results hid."""
    facts = _facts("Espaces Verts Exemple", "Canet-en-Roussillon", trade="paysagiste", country="FR")
    read: list[str] = []

    async def front_page(domain: str) -> tuple[str, str] | None:
        read.append(domain)
        if domain != "espaces-verts-exemple.fr":
            return None
        return f"https://www.{domain}/", "<title>Espaces Verts Exemple : paysagiste Canet-en-Roussillon</title>"

    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(front_page))
    results = [{"link": "https://fr.mappy.com/activite/paysagistes", "title": "Paysagistes", "description": "…"}]

    _verify(facts, results, None, _LANDSCAPER)
    verdict = CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY)

    assert read[0] == "espaces-verts-exemple.fr"
    assert (verdict.status, verdict.reject_reason) == (CandidateStatus.REJECTED, CandidateRejectReason.HAS_WEBSITE)
    assert CandidateVerifier.domains_named_after(facts, _LANDSCAPER) == [
        "espaces-verts-exemple.fr",
        "espacesvertsexemple.fr",
        "espaces-verts-exemple.com",
        "espacesvertsexemple.com",
    ]
    assert CandidateVerifier.domains_named_after(_facts("Garage du Centre", "Dijon", country="FR"), _GARAGE) == []


def test_a_namesake_s_site_elsewhere_is_never_taken_for_the_business_s(monkeypatch: pytest.MonkeyPatch) -> None:
    """« espaces-verts-exemple.fr » of a namesake near Lyon names neither Canet nor the business's number."""
    facts = _facts(
        "Espaces Verts Exemple", "Canet-en-Roussillon", trade="paysagiste", country="FR", phone="04 00 00 00 96"
    )

    async def namesake_page(domain: str) -> tuple[str, str] | None:
        return f"https://{domain}/", "<title>Espaces Verts Exemple, paysagiste à Villeurbanne</title> 04 11 11 11 11"

    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(namesake_page))

    asyncio.run(CandidateVerifier.consider_domains_named_after_business(facts, _LANDSCAPER))

    assert facts.website is None


def test_a_listing_at_the_town_hall_without_a_company_of_its_name_waits_for_a_check() -> None:
    """« exemple paysagiste », 2 Pass. de l'Hôtel de ville: no company of its name in the département, the town hall
    of a travelling tree trimmer's commune. A garage of the Rue de l'Hôtel de Ville has its company."""
    facts = _facts(
        "exemple paysagiste",
        "Mulhouse",
        trade="paysagiste",
        country="FR",
        address="2 Pass. de l'Hôtel de ville, 68100 Mulhouse",
        email="exemple.paysage@exemple.fr",
        email_proof_level=EmailProofLevel.PUBLISHED.value,
    )
    shop = _facts("Garage Exemple", "Mulhouse", country="FR", address="12 Rue de l'Hôtel de Ville, 68100 Mulhouse")

    FrenchRegistry.note_town_hall_address(facts, [])
    FrenchRegistry.note_town_hall_address(shop, [{"nom_complet": "GARAGE EXEMPLE"}])
    verdict = CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY)

    assert verdict.status == CandidateStatus.TO_CONFIRM
    assert (verdict.detail or "").startswith("Sa fiche Google donne l'adresse de la mairie")
    assert not shop.is_addressed_at_town_hall
