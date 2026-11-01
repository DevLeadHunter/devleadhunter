"""
Round 16 of the search training (garages of search n° 17 set aside once their sites were generated): the networks
seen on their photos, a brand's agent named in a directory's title or approved in its presentation, a site whose
domain glues the business's own short word to a trade word and whose contact page alone says where it is. Each case
is a real one, its names, numbers and people replaced.
"""

import asyncio
from collections.abc import Callable
from typing import Any

import httpx
import pytest

import services.prospect_search.candidate_verifier as candidate_verifier_module
from enums.prospect_search import CandidateOrigin, CandidateStatus, ProspectSearchChannel
from enums.website_status import WebsiteStatus
from services.decision_maker.french_departments import FrenchDepartments
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.network_outlets import NetworkOutlets
from services.prospect_search.search_judge import JudgeVerdict, SearchJudge, SearchResultLine
from services.prospect_search.trade_catalog import TradeCatalog
from services.website_liveness_service import website_liveness_service

_GARAGE = TradeCatalog.resolve("garage")
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=4.0)
_REAL_ASYNC_CLIENT = httpx.AsyncClient
_EXEM_AUTO_FRONT_PAGE = (
    "<title>Garage Exem&#039;auto</title>"
    '<a href="https://exemauto.fr/">Accueil</a> <a href="https://exemauto.fr/index.php/contact/">Contact:</a> '
    '<a href="https://www.facebook.com/exemauto">Facebook</a> Bienvenue chez Exem&#039;auto, votre garage '
    "multimarque de proximité."
)


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


def _facts(name: str, town: str, **overrides: object) -> CandidateFacts:
    """A garage's listing of the search, in *town*."""
    values: dict[str, object] = {
        "name": name,
        "trade_key": "garage",
        "country": "FR",
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "city": town,
        "searched_city": town,
        "google_category": "Atelier de réparation automobile",
        "google_rating": 4.4,
        "google_reviews_count": 67,
        "is_verified": True,
    }
    values.update(overrides)
    return CandidateFacts(**values)  # type: ignore[arg-type]


def _line(link: str, title: str, description: str) -> SearchResultLine:
    return SearchResultLine(
        link=link, host=link.split("/")[2].removeprefix("www."), title=title, description=description
    )


def _verify(facts: CandidateFacts, results: list[dict[str, str]], panel: dict[str, Any] | None = None) -> None:
    page: dict[str, Any] = {"organic": results, "knowledge": panel}
    verifier = CandidateVerifier(_OnePageClient(page), _ScriptedJudge())  # type: ignore[arg-type]
    asyncio.run(verifier.verify(facts, _GARAGE))


def _front_page_of_exem_auto(domain: str) -> Callable[[str], Any]:
    """The front page of *domain* names Garage Exem'Auto and links its contact page, nothing else answers."""

    async def front_page(asked: str) -> tuple[str, str] | None:
        return ("https://exemauto.fr", _EXEM_AUTO_FRONT_PAGE) if asked == domain else None

    return front_page


def _contact_page_answering(text: str, asked: list[str]) -> Callable[..., httpx.AsyncClient]:
    """Build the HTTP clients the verifier opens: the contact page answers *text*, the rest a 404."""

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append(str(request.url))
        if request.url.path == "/index.php/contact/":
            return httpx.Response(200, text=text)
        return httpx.Response(404, text="Not found")

    def build(**kwargs: Any) -> httpx.AsyncClient:
        return _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    return build


@pytest.mark.parametrize(
    "sign",
    [
        "Façade d'un garage avec enseigne 'Eurorepar Car Service' et panneaux indiquant les services.",
        "Bannière promotionnelle Euro Repar Car Service avec logo et fond bleu ciel.",
        "Façade d'un garage avec enseigne 'Top Garage' et vitrine montrant des véhicules en exposition.",
        "Façade aux enseignes « Selection Auto » et « Groupauto »",
        "Atelier automobile moderne avec façade en bois clair, enseigne PRECISIUM et vitrines.",
    ],
)
def test_eurorepar_top_garage_groupauto_and_precisium_are_networks(sign: str) -> None:
    assert NetworkOutlets.names_network(sign)


@pytest.mark.parametrize(
    ("text", "brand"),
    [
        ("Le Garage Exemple est un atelier de réparation et d'entretien automobile, agrée Renault.", "Renault"),
        ("Garage Exemple Agent Renault - Exempleville", "Renault"),
        ("Agence Renault avec façade blanche et enseigne noire affichant le nom 'Agence Exemple SARL'.", "Renault"),
        ("Concessionnaire Peugeot à Exempleville", "Peugeot"),
        ("Réparation toutes marques : Peugeot, Renault, Citroën.", None),
        ("Renault Clio blanche stationnée devant un garage avec d'autres véhicules en arrière-plan.", None),
        ("Flyer promotionnel pour la revente de véhicules Renault Clio avec garantie 3 mois.", None),
    ],
)
def test_a_brand_counts_only_after_agent_agence_concessionnaire_or_agree(text: str, brand: str | None) -> None:
    assert _GARAGE.brand_dealt_in_text(text) == brand


def test_a_directory_title_calling_the_garage_a_brand_s_agent_makes_it_the_brand_s_outlet() -> None:
    """The directories list « Garage Exemple Agent Renault », a garage Google names « GARAGE EXEMPLE »."""
    facts = _facts("GARAGE EXEMPLE", "Exempleville")
    results = [
        {
            "link": "https://www.pagesjaunes.fr/pros/00000001",
            "title": "Garage Exemple Agent Renault - Exempleville",
            "description": "Garage Exemple, 1 rue de l'Exemple 00000 Exempleville. Entretien, réparation.",
        },
        {
            "link": "https://www.pagesjaunes.fr/pros/00000002",
            "title": "Garage Témoin Agent Peugeot - Exempleville",
            "description": "Garage Témoin, 2 rue de l'Exemple 00000 Exempleville.",
        },
    ]

    _verify(facts, results)
    verdict = CandidateDecision.decide(facts, _GARAGE, _EMAIL_ONLY)

    assert (verdict.status, verdict.detail) == (
        CandidateStatus.REJECTED,
        "Agent ou concessionnaire Renault : le patron ne décide pas seul.",
    )


def test_a_google_presentation_saying_approved_by_a_brand_makes_the_garage_its_outlet() -> None:
    """« Le Garage Exemple est un atelier de réparation et d'entretien automobile, agrée Renault. »"""
    facts = _facts("Garage Exemple", "Exempleville", phone="05 00 00 00 01")
    panel = {
        "name": "Garage Exemple",
        "phone": "05 00 00 00 01",
        "merchant_description": (
            "Le Garage Exemple est un atelier de réparation et d'entretien automobile, agrée Renault."
        ),
    }

    _verify(facts, [], panel)
    verdict = CandidateDecision.decide(facts, _GARAGE, _EMAIL_ONLY)

    assert facts.evidence[-1]["source"] == "Présentation de sa fiche Google"
    assert verdict.detail == "Agent ou concessionnaire Renault : le patron ne décide pas seul."


def test_a_presentation_listing_the_makes_it_repairs_names_no_brand_s_outlet() -> None:
    facts = _facts("Garage Exemple", "Exempleville", phone="05 00 00 00 01")
    panel = {
        "name": "Garage Exemple",
        "phone": "05 00 00 00 01",
        "merchant_description": "Mécanique toutes marques : Peugeot, Renault, Citroën, Dacia.",
    }

    _verify(facts, [], panel)

    assert not facts.is_chain


def test_the_domain_gluing_the_garage_s_short_word_to_its_trade_is_read_with_its_contact_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    exemauto.fr names Garage Exem'Auto on its front page; only its contact page, linked « Contact: » from the menu,
    gives the address, its town written without hyphens.
    """
    facts = _facts("GARAGE EXEM'AUTO", "Saint-Exemple-lès-Dax", phone="05 00 00 00 49")
    asked: list[str] = []
    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(_front_page_of_exem_auto("exemauto.fr")))
    monkeypatch.setattr(
        candidate_verifier_module.httpx,
        "AsyncClient",
        _contact_page_answering("Contact: 56 Allée des Exemples 40990 Saint Exemple les Dax", asked),
    )

    asyncio.run(CandidateVerifier.consider_domains_named_after_business(facts, _GARAGE))

    assert "exemauto.fr" in CandidateVerifier.domains_named_after(facts, _GARAGE)
    assert asked == ["https://exemauto.fr/index.php/contact/"]
    assert (facts.website, facts.website_status) == ("https://exemauto.fr", WebsiteStatus.LIVE.value)
    assert facts.evidence[-1]["source"] == "Le domaine à son nom répond"


def test_a_namesake_s_site_whose_contact_page_is_elsewhere_is_never_taken(monkeypatch: pytest.MonkeyPatch) -> None:
    facts = _facts("GARAGE EXEM'AUTO", "Saint-Exemple-lès-Dax", phone="05 00 00 00 49")
    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(_front_page_of_exem_auto("exemauto.fr")))
    monkeypatch.setattr(
        candidate_verifier_module.httpx,
        "AsyncClient",
        _contact_page_answering("Contact: 3 rue du Témoin 69100 Villeurbanne. Téléphone: 04 11 11 11 11", []),
    )

    asyncio.run(CandidateVerifier.consider_domains_named_after_business(facts, _GARAGE))

    assert facts.website is None


def test_a_result_on_the_domain_spelling_the_garage_s_name_and_showing_its_number_gives_its_site() -> None:
    facts = _facts("GARAGE EXEM'AUTO", "Saint-Exemple-lès-Dax", phone="05 00 00 00 49")
    line = _line(
        "https://exemauto.fr/index.php/privacy-policy/",
        "Politique de confidentialité – Garage Exem'auto",
        "Responsable du traitement : SOCIETE NOUVELLE EXEM'AUTO SARL. Téléphone : 05.00.00.00.49",
    )

    CandidateVerifier.take_site_showing_contact(facts, line, _GARAGE, source="Recherche par son numéro")

    assert facts.website == "https://exemauto.fr/"


def test_a_result_on_a_domain_spelling_the_garage_s_name_is_its_site_only_in_its_town() -> None:
    """A result naming « Garage Exem'Auto » elsewhere may be a namesake's: only the one in its town is its site."""
    namesake = {
        "link": "https://exemauto.com/",
        "title": "Garage Exem'Auto",
        "description": "Garage Exem'Auto, votre garage multimarque à Villeurbanne.",
    }
    own_site = {
        "link": "https://exemauto.fr/",
        "title": "Garage Exem'auto",
        "description": "Bienvenue chez Exem'auto, votre garage de proximité à Saint Exemple les Dax.",
    }
    facts_beside_a_namesake = _facts("GARAGE EXEM'AUTO", "Saint-Exemple-lès-Dax")
    facts_beside_its_site = _facts("GARAGE EXEM'AUTO", "Saint-Exemple-lès-Dax")

    _verify(facts_beside_a_namesake, [namesake])
    _verify(facts_beside_its_site, [namesake, own_site])

    assert facts_beside_a_namesake.website is None
    assert facts_beside_its_site.website == "https://exemauto.fr/"


def test_a_town_is_read_however_its_words_are_joined() -> None:
    facts = _facts("Garage Exemple", "Saint-Exemple-lès-Dax")

    assert facts.is_town_named_in("56 Allée des Exemples, 40990 SAINT EXEMPLE LES DAX")
    assert facts.is_town_named_in("à Saint-Exemple-lès-Dax (40)")
    assert not facts.is_town_named_in("Saint-Exemple-lès-Daxois")
    assert not _facts("Garage Exemple", "Dax").is_town_named_in("Daxois")
