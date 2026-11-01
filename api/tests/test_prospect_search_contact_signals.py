"""
Round 14 of the search training (search n° 19, Martinique): what a business's own contact says. Its phone or its email on
a domain carrying its name makes that domain its website; a car brand opening its email makes it the brand's dealer;
a Facebook page placed in another commune of the island is another garage's. The real cases' people are replaced.
"""

import asyncio
from typing import Any

import pytest

from enums.prospect_search import CandidateOrigin, CandidateRejectReason, CandidateStatus, ProspectSearchChannel
from enums.website_status import WebsiteStatus
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.contact_finder import ContactFinder
from services.prospect_search.search_judge import SearchJudge, SearchResultLine
from services.prospect_search.trade_catalog import TradeCatalog
from services.website_liveness_service import website_liveness_service

_GARAGE = TradeCatalog.resolve("garage")
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=4.0)
_FACEBOOK_PAGE = "https://www.facebook.com/Garage-Marc-EXEMPLE-100000000000005"


class _OnePageClient:
    """Stands in for Bright Data: always answers the same parsed page."""

    def __init__(self, page: dict[str, Any]) -> None:
        self._page = page

    async def google_parsed(self, query: str, *, country: str = "FR", start: int = 0, local: bool = False) -> Any:
        return self._page


class _SilentJudge(SearchJudge):
    async def judge(self, **_: object) -> None:
        return None


@pytest.fixture(autouse=True)
def offline_web(monkeypatch: pytest.MonkeyPatch) -> None:
    async def live(website: str | None) -> WebsiteStatus | None:
        return WebsiteStatus.LIVE if website else None

    async def no_front_page(domain: str) -> tuple[str, str] | None:
        return None

    monkeypatch.setattr(website_liveness_service, "check_website_status", live)
    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(no_front_page))


def _martinique_garage(**overrides: object) -> CandidateFacts:
    """A garage of Saint-Esprit whose Google listing gives its Facebook page as its website (candidate n° 5484)."""
    values: dict[str, object] = {
        "name": "Garage Marc Exemple",
        "trade_key": "garage",
        "country": "FR",
        "region": "MQ",
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "city": "Saint-Esprit",
        "searched_city": "Le François",
        "address": "Quartier Exemple, Saint-Esprit 97270, Martinique",
        "phone": "+596 696 00 00 08",
        "google_category": "Garage automobile",
        "google_rating": 4.8,
        "google_reviews_count": 20,
        "facebook_url": _FACEBOOK_PAGE,
    }
    values.update(overrides)
    facts = CandidateFacts(**values)  # type: ignore[arg-type]
    facts.add_evidence("facebook", _FACEBOOK_PAGE, source="Bouton « Site Web » de la fiche Google", url=_FACEBOOK_PAGE)
    return facts


def _result(link: str, title: str, description: str) -> dict[str, str]:
    return {"link": link, "title": title, "description": description}


def test_the_contact_page_of_a_domain_carrying_its_name_is_the_business_s_website() -> None:
    """The verification shows the garage's own contact page, its number on it: the domain is its website."""
    facts = _martinique_garage()
    page = {
        "organic": [
            _result(
                "https://www.garagemexemple.fr/contact",
                "Contact",
                "Appelez-nous au 0696 00 00 08 ou écrivez-nous à 0696000008@orange.fr.",
            )
        ]
    }

    asyncio.run(CandidateVerifier(_OnePageClient(page), _SilentJudge()).verify(facts, _GARAGE))  # type: ignore[arg-type]
    verdict = CandidateDecision.decide(facts, _GARAGE, _EMAIL_ONLY)

    assert facts.website == "https://www.garagemexemple.fr/contact"
    assert (verdict.status, verdict.reject_reason) == (CandidateStatus.REJECTED, CandidateRejectReason.HAS_WEBSITE)


def test_the_number_search_finds_the_legal_notice_of_its_own_website() -> None:
    facts = _martinique_garage(is_verified=True, is_facebook_page_read=True)
    finder = ContactFinder(
        _OnePageClient(
            {
                "organic": [
                    _result(
                        "https://www.garagemexemple.fr/mentions",
                        "Informations",
                        "Garage automobile, Saint-Esprit. Tél : 06 96 00 00 08.",
                    )
                ]
            }
        ),
        _SilentJudge(),
    )  # type: ignore[arg-type]

    asyncio.run(finder.find(facts, _GARAGE))

    assert (facts.website, facts.website_status) == ("https://www.garagemexemple.fr/", WebsiteStatus.LIVE.value)


def test_a_domain_carrying_the_name_without_its_contact_is_not_taken_from_the_number_search() -> None:
    """A namesake's site found by the number search shows another number: it is not the garage's."""
    facts = _martinique_garage(is_verified=True, is_facebook_page_read=True)
    namesake = SearchResultLine(
        link="https://www.exemple-immobilier.fr/agence",
        host="exemple-immobilier.fr",
        title="Agence Exemple Immobilier",
        description="Agence immobilière. Tél : 05 96 00 00 01.",
    )

    CandidateVerifier.take_site_showing_contact(facts, namesake, _GARAGE, source="Recherche par son numéro")

    assert facts.website is None


@pytest.mark.parametrize(
    ("email", "is_dealer"),
    [("aixamautomobille@outlook.fr", True), ("mercedes.exemple@gmail.com", False), ("garage.exemple@gmail.com", False)],
)
def test_a_car_brand_opening_the_email_makes_its_dealer(email: str, is_dealer: bool) -> None:
    """Garage Automobile VSP (candidate n° 5268) writes from « aixamautomobille@… »: an Aixam dealer."""
    facts = _martinique_garage(name="Garage Automobile VSP", email=email, is_verified=True)

    CandidateVerifier.mark_brand_named_in_email(facts, _GARAGE)
    verdict = CandidateDecision.decide(facts, _GARAGE, _EMAIL_ONLY)

    assert (verdict.reject_reason == CandidateRejectReason.CHAIN) is is_dealer
    if is_dealer:
        assert verdict.detail == "Agent ou concessionnaire Aixam : le patron ne décide pas seul."


def test_a_facebook_page_placed_in_another_commune_of_the_island_is_another_garage_s() -> None:
    """Flash Car is in Ducos; « Garage Flash Auto Carrosserie », found by its name, is in Le Marin."""
    facts = CandidateFacts(
        name="Flash Car",
        trade_key="garage",
        country="FR",
        region="MQ",
        origin=CandidateOrigin.GOOGLE_LOCAL.value,
        searched_city="Ducos",
        address="Z.I Petite Cocotte Ducos, 97224, Martinique",
        phone="+596 596 00 00 93",
    )
    namesake = SearchResultLine(
        link="https://www.facebook.com/garageflashautocarrosserie",
        host="facebook.com",
        title="Garage Flash Auto Carrosserie | Le Marin Martinique",
        description="Nous peignons vos véhicules et réparons vos véhicules accidentés.",
    )
    own_page = SearchResultLine(
        link="https://www.facebook.com/flashcarducos",
        host="facebook.com",
        title="Flash Car | Ducos Martinique",
        description="Garage mécanique et carrosserie à Ducos.",
    )

    assert CandidateVerifier.is_facebook_page_of(namesake, facts, _GARAGE) is False
    assert CandidateVerifier.is_facebook_page_of(own_page, facts, _GARAGE) is True
