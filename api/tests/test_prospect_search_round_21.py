"""
Round 21 of the search training (searches n° 20 and 26): a listing without reviews read from the parsed JSON took its
category for its town, so nothing checked it against the town searched, and a namesake's page and email passed. Each
case is a real one, its names, numbers and places replaced.
"""

import asyncio
from typing import Any

import pytest

from enums.prospect_search import CandidateOrigin, CandidateStatus, EmailProofLevel, ProspectSearchChannel
from enums.website_status import WebsiteStatus
from scrappers.google_local_results import GoogleLocalResultsParser
from services.decision_maker.french_departments import FrenchDepartments
from services.decision_maker.normalize import town_key
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.place_of_contact import PlaceOfContact
from services.prospect_search.search_judge import JudgeVerdict, SearchJudge, SearchResultLine
from services.prospect_search.trade_catalog import TradeCatalog
from services.website_liveness_service import website_liveness_service

_LANDSCAPER = TradeCatalog.resolve("paysagiste")
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=4.0)
_FRENCH_NAMESAKE_PAGE = SearchResultLine(
    link="https://www.facebook.com/",
    host="facebook.com",
    title="Sarl Exemple Paysagiste",
    description=(
        "Modèleville ... · Témoinville, France · Saint-Exemple, France · … Details. exemple-paysagiste.fr. Links. "
        "+33 2 00 00 00 00. sarlexemple@gmail.com. Contact info ..."
    ),
)


class _OnePageClient:
    """Stands in for Bright Data: always answers the same parsed page, and keeps the queries."""

    def __init__(self, page: dict[str, Any]) -> None:
        self._page = page
        self.queries: list[str] = []

    async def google_parsed(self, query: str, *, country: str = "FR", start: int = 0, local: bool = False) -> Any:
        self.queries.append(query)
        return self._page


class _SilentJudge(SearchJudge):
    """A judge that settles nothing."""

    async def judge(self, **_: object) -> JudgeVerdict | None:
        return None


@pytest.fixture(autouse=True)
def offline_web(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every website answers and no domain shows a front page; the searched town is in the Lot-et-Garonne."""

    async def live(website: str | None) -> WebsiteStatus | None:
        return WebsiteStatus.LIVE if website else None

    async def no_front_page(domain: str) -> tuple[str, str] | None:
        return None

    monkeypatch.setattr(website_liveness_service, "check_website_status", live)
    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(no_front_page))
    monkeypatch.setitem(FrenchDepartments._department_by_town, town_key("Exempleville"), "47")


def _listing_without_address(name: str = "Exemple paysage", **overrides: object) -> CandidateFacts:
    """A listing of the parsed JSON without reviews: no address, no town, no phone, no rating."""
    values: dict[str, object] = {
        "name": name,
        "trade_key": "paysagiste",
        "country": "FR",
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "searched_city": "Exempleville",
        "google_category": "Paysagiste",
        "google_cid": "1111",
        "is_verified": True,
    }
    values.update(overrides)
    return CandidateFacts(**values)  # type: ignore[arg-type]


def test_an_unrated_listing_of_the_parsed_json_has_a_category_and_no_town() -> None:
    """Bright Data writes the rating line of a listing without reviews where the address goes."""
    listings = GoogleLocalResultsParser.parse_snack_pack(
        [
            {"cid": "1", "name": "Exemple paysage", "work_status": "Fermé", "address": "Aucun avis ⋅ Paysagiste"},
            {"cid": "2", "name": "Jardins Témoin", "address": "Plus de 3 ans en activité"},
            {"cid": "3", "name": "Modèle Paysages", "rating": 4.4, "type": "Paysagiste", "address": "Exempleville"},
        ]
    )

    assert [(listing.category, listing.locality) for listing in listings] == [
        ("Paysagiste", None),
        (None, None),
        ("Paysagiste", "Exempleville"),
    ]


def test_an_unrated_listing_is_placed_and_verified_by_the_searched_town() -> None:
    listing = GoogleLocalResultsParser.parse_snack_pack(
        [{"cid": "1111", "name": "Exemple paysage", "address": "Aucun avis ⋅ Paysagiste"}]
    )[0]
    facts = _listing_without_address(city=listing.locality, is_verified=False)
    client = _OnePageClient({"organic": [{"link": "https://www.exemple.fr/", "title": "Autre", "description": "-"}]})

    asyncio.run(CandidateVerifier(client, _SilentJudge()).verify(facts, _LANDSCAPER))  # type: ignore[arg-type]

    assert facts.is_placed_by_the_search_only is True
    assert client.queries == ['"Exemple paysage" Exempleville']


def test_an_email_read_on_a_page_placing_the_business_in_another_country_is_dropped() -> None:
    """A Swiss listing without address: the page giving the email is a French landscaper's."""
    facts = _listing_without_address("Jules Exemple Paysagiste", country="CH")

    CandidateVerifier.offer_email_read_in(
        facts,
        "sarlexemple@gmail.com",
        EmailProofLevel.DIRECTORY,
        _FRENCH_NAMESAKE_PAGE,
        _LANDSCAPER,
        department=None,
        is_own_text=False,
    )

    assert facts.email is None
    assert [(line["fact"], line["source"]) for line in facts.evidence] == [
        ("email_dropped", "La page qui le donne le place ailleurs (France)")
    ]


@pytest.mark.parametrize(
    "description",
    [
        "Modèleville, Suisse · Témoinville, France. sarlexemple@gmail.com",
        "Jardinier à Exempleville et environs. sarlexemple@gmail.com",
    ],
)
def test_a_page_naming_the_search_s_country_or_town_keeps_its_email(description: str) -> None:
    facts = _listing_without_address("Jules Exemple Paysagiste", country="CH")
    line = SearchResultLine(link="https://www.exemple.ch/", host="exemple.ch", title="Exemple", description=description)

    CandidateVerifier.offer_email_read_in(
        facts,
        "sarlexemple@gmail.com",
        EmailProofLevel.DIRECTORY,
        line,
        _LANDSCAPER,
        department=None,
        is_own_text=False,
    )

    assert facts.email == "sarlexemple@gmail.com"


@pytest.mark.parametrize(
    ("description", "place_elsewhere"),
    [
        ("Exemple Paysage, 12 rue Exemple, 41000 Modèleville. Tél. 02 00 00 00 00", "41000"),
        ("Exemple Paysage, 12 rue Exemple, 47000 Exempleville. Tél. 05 00 00 00 00", None),
        ("Exemple Paysage, SIRET 000 000 000 00012 Modèle, 41000 personnes servies", None),
    ],
)
def test_a_page_of_another_departement_places_a_listing_without_address_elsewhere(
    description: str, place_elsewhere: str | None
) -> None:
    facts = _listing_without_address()

    assert PlaceOfContact.place_elsewhere_in(description, facts, "47") == place_elsewhere


def test_a_namesake_s_facebook_page_elsewhere_is_not_the_listing_s_own_page() -> None:
    """Found by the name alone, the page does not name the searched town: its email is a third party's, dropped."""
    facts = _listing_without_address("Jules Exemple Paysagiste", country="CH", is_verified=False)
    client = _OnePageClient(
        {
            "organic": [
                {
                    "link": "https://www.facebook.com/sarlexemplepaysagiste/",
                    "title": "Sarl Exemple Paysagiste",
                    "description": _FRENCH_NAMESAKE_PAGE.description,
                }
            ]
        }
    )

    asyncio.run(CandidateVerifier(client, _SilentJudge()).verify(facts, _LANDSCAPER))  # type: ignore[arg-type]

    assert (facts.facebook_url, facts.email) == (None, None)


def test_an_email_naming_another_departement_read_on_a_page_that_does_not_place_the_listing_is_dropped() -> None:
    facts = _listing_without_address()
    line = SearchResultLine(
        link="https://www.annuaire-exemple.fr/exemple-paysage",
        host="annuaire-exemple.fr",
        title="Exemple paysage - Paysagiste",
        description="Entretien de jardins, tonte, taille de haies. exemplepaysage41@gmail.com",
    )
    CandidateVerifier.offer_email_read_in(
        facts,
        "exemplepaysage41@gmail.com",
        EmailProofLevel.DIRECTORY,
        line,
        _LANDSCAPER,
        department="47",
        is_own_text=False,
    )

    asyncio.run(PlaceOfContact.note_contact_elsewhere(facts))

    assert facts.email is None
    verdict = CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY)
    assert (verdict.status, verdict.detail) == (CandidateStatus.REJECTED, "Ni email ni numéro de portable trouvés.")


def test_an_email_naming_another_departement_on_the_listing_s_own_page_is_left_to_confirm() -> None:
    """Its Facebook page named the searched town: the email is its own, its département number a doubt."""
    facts = _listing_without_address(facebook_url="https://www.facebook.com/exemplepaysage", is_facebook_page_read=True)
    facts.offer_email(
        "exemplepaysage41@gmail.com", EmailProofLevel.PUBLISHED, source="Page Facebook", url=facts.facebook_url
    )

    asyncio.run(PlaceOfContact.note_contact_elsewhere(facts))

    verdict = CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY)
    assert verdict.status == CandidateStatus.TO_CONFIRM
    assert verdict.detail == (
        "Son email (exemplepaysage41@gmail.com) désigne un autre endroit (41) que Exempleville : à vérifier, ce peut "
        "être un homonyme."
    )


@pytest.mark.parametrize(("panel_feature_id", "takes_panel"), [("0x0:0x2b67", False), ("0x0:0x457", True)])
def test_a_listing_takes_the_panel_of_its_own_google_listing_only(panel_feature_id: str, takes_panel: bool) -> None:
    """0x457 is the listing's own identifier (1111); a namesake's listing elsewhere has another."""
    facts = _listing_without_address(is_verified=False)
    client = _OnePageClient(
        {
            "knowledge": {
                "name": "Exemple Paysage",
                "address": "12 Rue Exemple, 41000 Modèleville",
                "phone": "02 00 00 00 00",
                "fid": panel_feature_id,
            },
            "organic": [],
        }
    )

    asyncio.run(CandidateVerifier(client, _SilentJudge()).verify(facts, _LANDSCAPER))  # type: ignore[arg-type]

    assert (facts.address is not None, facts.phone is not None) == (takes_panel, takes_panel)
    assert facts.is_placed_by_the_search_only is not takes_panel
