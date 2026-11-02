"""
Round 22 of the search training (searches n° 25 to 27, electricians of the Calvados): a directory copying a Wix
site's error-reporting address as the business's email, and the RGE list's capitals reaching the prospects and their
sites. Each case is a real one, its names, numbers and places replaced.
"""

import asyncio
from typing import Any

import httpx
import pytest

from enums.prospect_search import CandidateOrigin, CandidateStatus, ProspectSearchChannel
from enums.website_status import WebsiteStatus
from scrappers.email_candidate_scoring import email_candidate_scorer
from services.decision_maker.french_departments import FrenchDepartments
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.register_spelling import RegisterSpelling
from services.prospect_search.registry_sources import rge_registry
from services.prospect_search.search_judge import JudgeVerdict, SearchJudge, SearchResultLine
from services.prospect_search.trade_catalog import TradeCatalog
from services.website_liveness_service import website_liveness_service

_ELECTRICIAN = TradeCatalog.resolve("electricien")
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=4.0)
_REAL_ASYNC_CLIENT = httpx.AsyncClient
_DIRECTORY_PAGE = {
    "link": "https://www.infobel.com/fr/france/exemple_elec/exempleville/fr000000000-0000000000/businessdetails.aspx",
    "title": "Exemple Elec, Exempleville, FR | Informations sur l'entreprise",
    "description": (
        "Exemple Elec. 18 Rue Exemple 14999 Exempleville. Afficher le téléphone ... Aperçu rapide. email "
        "aa@sentry.wixpress.com · Exemple Elec. 0 Commentaires."
    ),
}


class _OnePageClient:
    """Stands in for Bright Data: always answers the same parsed page."""

    def __init__(self, page: dict[str, Any]) -> None:
        self._page = page

    async def google_parsed(self, query: str, *, country: str = "FR", start: int = 0, local: bool = False) -> Any:
        return self._page


class _SilentJudge(SearchJudge):
    """A judge that settles nothing."""

    async def judge(self, **_: object) -> JudgeVerdict | None:
        return None


@pytest.fixture(autouse=True)
def offline_web(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every website answers and no domain shows a front page."""

    async def live(website: str | None) -> WebsiteStatus | None:
        return WebsiteStatus.LIVE if website else None

    async def no_front_page(domain: str) -> tuple[str, str] | None:
        return None

    monkeypatch.setattr(website_liveness_service, "check_website_status", live)
    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(no_front_page))


def _listing(phone: str) -> CandidateFacts:
    """An electrician's Google listing, rated, placed in its town."""
    return CandidateFacts(
        name="Exemple Elec",
        trade_key="electricien",
        country="FR",
        origin=CandidateOrigin.GOOGLE_LOCAL.value,
        city="Exempleville",
        searched_city="Exempleville",
        phone=phone,
        google_rating=5.0,
        google_reviews_count=9,
        google_category="Électricien",
    )


@pytest.mark.parametrize(
    "email",
    [
        "aa@sentry.wixpress.com",
        "0f1e2d3c4b5a69788796a5b4c3d2e1f0@sentry-next.wixpress.com",
        "1a2b3c@o123456.ingest.sentry.io",
        "support@wix.com",
        "example@gmail.com",
        "exemple@orange.fr",
        "info@mysite.com",
    ],
)
def test_a_site_service_or_placeholder_address_is_never_a_business_email(email: str) -> None:
    page = f"Exemple Elec, Exempleville. {email} · contact@exemple-elec.fr"

    ranked = [address for address, _ in email_candidate_scorer.rank_candidates(page, name="Exemple Elec", city="Caen")]

    assert ranked == ["contact@exemple-elec.fr"]


@pytest.mark.parametrize(
    ("phone", "status", "detail"),
    [
        (
            "06 00 00 00 01",
            CandidateStatus.TO_CONFIRM,
            "infobel.com lui donne aa@sentry.wixpress.com, l'adresse technique d'un site : il a sans doute un "
            "site, qui n'a pas été retrouvé : à vérifier.",
        ),
        ("02 00 00 00 01", CandidateStatus.REJECTED, "Ni email ni numéro de portable trouvés."),
    ],
)
def test_a_directory_copying_a_wix_site_s_address_shows_a_site_not_an_email(
    phone: str, status: CandidateStatus, detail: str
) -> None:
    """A mobile still reaches the business: its site is to check. A landline alone leaves no contact."""
    facts = _listing(phone)

    client = _OnePageClient({"organic": [_DIRECTORY_PAGE]})
    verifier = CandidateVerifier(client, _SilentJudge())  # type: ignore[arg-type]

    asyncio.run(verifier.verify(facts, _ELECTRICIAN))

    assert facts.email is None
    verdict = CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY)
    assert (verdict.status, verdict.detail) == (status, detail)


def test_the_contact_search_notes_the_site_a_site_service_address_reveals() -> None:
    facts = _listing("06 00 00 00 01")
    line = SearchResultLine(
        link=_DIRECTORY_PAGE["link"],
        host="infobel.com",
        title=_DIRECTORY_PAGE["title"],
        description=_DIRECTORY_PAGE["description"],
    )

    CandidateVerifier.read_site_revealing_addresses(facts, line)

    assert facts.website_technical_address is not None
    assert facts.website_technical_address["value"] == "aa@sentry.wixpress.com"


@pytest.mark.parametrize(
    ("registered_name", "shown_name"),
    [
        ("TEMOIN JULIEN", "Julien Temoin"),
        ("SAINT-EXEMPLE ELECTRICITE", "Saint-Exemple Électricité"),
        ("TEMOIN & ASSOCIES", "Temoin & Associés"),
        ("TEMOIN ET ASSOCIES", "Temoin et Associés"),
        ("ABE", "ABE"),
        ("VX ELECTRICITE", "VX Électricité"),
        ("J.M. ENTREPRISE", "J.M. Entreprise"),
        ("EXE'MP", "Exe'mp"),
        ("LE TEMOIN BATIMENT", "Le Temoin Bâtiment"),
        ("PLOMBERIE CHAUFFAGE LA MODELIERE", "Plomberie Chauffage La Modeliere"),
        ("GARAGE JULIEN", "Garage Julien"),
        ("XTR PIERRE", "XTR Pierre"),
        ("SAS TEMOIN CHRISTOPHE", "SAS Temoin Christophe"),
    ],
)
def test_a_registered_name_is_written_the_way_a_site_shows_it(registered_name: str, shown_name: str) -> None:
    """A sole trader « NOM PRÉNOM » is « Prénom Nom »; a business word or a legal form keeps the order."""
    assert RegisterSpelling.business_name(registered_name) == shown_name


@pytest.mark.parametrize(
    ("registered_street", "shown_address"),
    [
        ("RUE DE L'EXEMPLE - ZI", "Rue de l'Exemple, ZI, 14999 Exempleville-sur-Mer"),
        ("RUE DE LA MODELERIE ZA D'EXEMPLEVILLE", "Rue de la Modelerie, ZA d'Exempleville, 14999 Exempleville-sur-Mer"),
        (
            "70 RUE DU MONT EXEMPLE ZAC LES TEMOINS",
            "70 rue du Mont Exemple, ZAC Les Temoins, 14999 Exempleville-sur-Mer",
        ),
        ("2 IMPASSE DE L'ETABLE", "2 impasse de l'Étable, 14999 Exempleville-sur-Mer"),
        ("14 BIS RUE JULES EXEMPLE BP 23", "14 bis rue Jules Exemple, BP 23, 14999 Exempleville-sur-Mer"),
        ("875 RUE DE LA PLANCHE Z.I EST", "875 rue de la Planche, ZI Est, 14999 Exempleville-sur-Mer"),
        ("HAMEAU D EXEMPLEVILLE", "Hameau d'Exempleville, 14999 Exempleville-sur-Mer"),
        ("4 RUE DU PARC", "4 rue du Parc, 14999 Exempleville-sur-Mer"),
        ("", "14999 Exempleville-sur-Mer"),
    ],
)
def test_a_registered_street_carries_its_postal_code_and_commune(registered_street: str, shown_address: str) -> None:
    assert RegisterSpelling.address(registered_street, "14999", "Exempleville-sur-Mer") == shown_address


def _communes(monkeypatch: pytest.MonkeyPatch, by_postal_code: dict[str, list[str]]) -> None:
    async def communes_of_postal_code(postal_code: str) -> list[dict[str, str]]:
        return [{"nom": name} for name in by_postal_code.get(postal_code, [])]

    monkeypatch.setattr(FrenchDepartments, "_communes_of_postal_code", staticmethod(communes_of_postal_code))


@pytest.mark.parametrize(
    ("registered_commune", "spelled"),
    [
        ("EXEMPLEVILLE SUR MER", "Exempleville-sur-Mer"),
        ("SAINT-TEMOIN", "Saint-Témoin"),
        ("MODELEVILLE", "Modeleville"),
    ],
)
def test_a_registered_commune_takes_the_official_spelling_of_its_postal_code(
    monkeypatch: pytest.MonkeyPatch, registered_commune: str, spelled: str
) -> None:
    """14999 serves two communes; a commune the official list does not know there is only made readable."""
    _communes(monkeypatch, {"14999": ["Saint-Témoin", "Exempleville-sur-Mer"]})

    assert asyncio.run(FrenchDepartments.commune_name(registered_commune, postal_code="14999")) == spelled


def test_the_rge_list_s_companies_reach_the_search_written_properly(monkeypatch: pytest.MonkeyPatch) -> None:
    _communes(monkeypatch, {"14999": ["Saint-Témoin", "Exempleville-sur-Mer"]})
    rows = [
        {
            "nom_entreprise": "TEMOIN JULIEN",
            "adresse": "RUE DE L'EXEMPLE - ZI",
            "code_postal": "14999",
            "commune": "EXEMPLEVILLE SUR MER",
            "telephone": "0600000001",
            "email": "temoin.julien@gmail.com",
            "siret": "00000000000001",
        }
    ]

    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": rows})

    def build(**kwargs: Any) -> httpx.AsyncClient:
        return _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(answer), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", build)

    [company] = asyncio.run(rge_registry.companies_near(trade=_ELECTRICIAN, city="Exempleville-sur-Mer", limit=10))

    assert (company.name, company.city, company.address) == (
        "Julien Temoin",
        "Exempleville-sur-Mer",
        "Rue de l'Exemple, ZI, 14999 Exempleville-sur-Mer",
    )
