"""Verifying one candidate: what a single search page proves, with the web and the judge replaced by canned answers."""

import asyncio
from typing import Any

import pytest

from enums.prospect_search import CandidateOrigin, EmailProofLevel
from enums.website_status import WebsiteStatus
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.search_judge import JudgedEmail, JudgeVerdict, SearchJudge
from services.prospect_search.trade_catalog import TradeCatalog
from services.website_liveness_service import website_liveness_service

_LANDSCAPER = TradeCatalog.resolve("paysagiste")
_PLUMBER = TradeCatalog.resolve("plombier")


class _OnePageClient:
    """Stands in for Bright Data: always answers the same parsed page."""

    def __init__(self, page: dict[str, Any] | None) -> None:
        self._page = page
        self.queries: list[str] = []

    async def google_parsed(self, query: str, *, country: str = "FR", start: int = 0, local: bool = False) -> Any:
        self.queries.append(query)
        return self._page


class _ScriptedJudge(SearchJudge):
    """A judge answering a prepared verdict, and counting how often it is asked."""

    def __init__(self, verdict: JudgeVerdict | None = None) -> None:
        self._verdict = verdict
        self.call_count = 0

    async def judge(self, **_: object) -> JudgeVerdict | None:
        self.call_count += 1
        return self._verdict


@pytest.fixture(autouse=True)
def every_website_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    async def live(website: str | None) -> WebsiteStatus | None:
        return WebsiteStatus.LIVE if website else None

    async def no_front_page(domain: str) -> tuple[str, str] | None:
        return None

    monkeypatch.setattr(website_liveness_service, "check_website_status", live)
    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(no_front_page))


def _facts(**overrides: object) -> CandidateFacts:
    values: dict[str, object] = {
        "name": "Tendance Nature",
        "trade_key": "paysagiste",
        "country": "CH",
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "city": "Sion",
        "phone": "078 757 57 42",
    }
    values.update(overrides)
    return CandidateFacts(**values)  # type: ignore[arg-type]


def _verify(
    facts: CandidateFacts, page: dict[str, Any] | None, *, judge: _ScriptedJudge | None = None, trade: Any = _LANDSCAPER
) -> _ScriptedJudge:
    judge = judge or _ScriptedJudge()
    asyncio.run(CandidateVerifier(_OnePageClient(page), judge).verify(facts, trade))  # type: ignore[arg-type]
    return judge


def _result(link: str, title: str, description: str = "") -> dict[str, str]:
    return {"link": link, "title": title, "description": description}


def test_the_panel_gives_the_hidden_website_the_listing_did_not_show() -> None:
    facts = _facts()

    _verify(
        facts,
        {
            "knowledge": {
                "name": "Tendance Nature",
                "site": "http://www.tendance-nature.ch/",
                "rating": 4.8,
                "reviews_cnt": 12,
                "fid": "0x478eddf35a2c984b:0xacfd6b49b12f3549",
                "summary": "Paysagiste à Sion",
            },
            "organic": [],
        },
    )

    assert facts.is_verified is True
    assert (facts.website, facts.website_status) == ("http://www.tendance-nature.ch/", "live")
    assert (facts.google_rating, facts.google_reviews_count, facts.google_category) == (4.8, 12, "Paysagiste")
    assert facts.google_cid == str(int("acfd6b49b12f3549", 16))


def test_a_facebook_page_declared_as_website_is_not_a_website() -> None:
    facts = _facts()

    _verify(
        facts,
        {"knowledge": {"name": "Tendance Nature", "site": "https://www.facebook.com/tendancenature/"}, "organic": []},
    )

    assert facts.website is None
    assert facts.facebook_url == "https://www.facebook.com/tendancenature"


def test_a_closed_listing_is_flagged_with_its_proof() -> None:
    facts = _facts()

    _verify(facts, {"knowledge": {"name": "Tendance Nature", "open_status": "Fermé définitivement"}, "organic": []})

    assert facts.is_closed is True
    assert any(line["fact"] == "closed" for line in facts.evidence)


def test_directories_and_registries_are_not_websites_and_need_no_judge() -> None:
    facts = _facts()

    judge = _verify(
        facts,
        {
            "organic": [
                _result("https://www.local.ch/fr/d/sion/1950/tendance-nature", "Tendance Nature – Paysagiste à Sion"),
                _result(
                    "https://www.moneyhouse.ch/fr/company/tendance-nature-123",
                    "Tendance Nature à Sion",
                    "Tendance Nature, CHE-275.432.850, entreprise individuelle.",
                ),
            ]
        },
    )

    assert facts.website is None
    assert facts.registry_number == "CHE-275.432.850"
    assert judge.call_count == 0


def test_a_domain_named_after_the_business_is_its_website_without_the_judge() -> None:
    facts = _facts(name="Plaschy Paysagiste Sàrl")

    judge = _verify(
        facts, {"organic": [_result("https://plaschy-paysagiste.ch/", "Plaschy Paysagiste | Création de jardins")]}
    )

    assert facts.website == "https://plaschy-paysagiste.ch/"
    assert judge.call_count == 0


def test_a_directory_page_the_judge_calls_a_website_is_refused() -> None:
    facts = _facts(name="Etablissements Aubin", trade_key="plombier", country="FR", city="Beauvais")
    judge = _ScriptedJudge(JudgeVerdict(own_website_index=0))

    _verify(
        facts,
        {
            "organic": [
                _result(
                    "https://www.annuaire-des-pros.org/entreprises/fiche-60000",
                    "Etablissements Aubin - Plombier à Beauvais",
                )
            ]
        },
        judge=judge,
        trade=_PLUMBER,
    )

    assert judge.call_count == 1
    assert facts.website is None


def test_the_judge_s_website_is_kept_when_it_is_the_root_of_a_domain() -> None:
    facts = _facts(name="Les Jardins de Charles")
    judge = _ScriptedJudge(JudgeVerdict(own_website_index=0))

    _verify(
        facts,
        {"organic": [_result("https://www.creations-vertes.ch/", "Les Jardins de Charles, paysagiste")]},
        judge=judge,
    )

    assert facts.website == "https://www.creations-vertes.ch/"


def test_a_namesake_s_personal_profile_is_not_taken_for_the_business_page() -> None:
    facts = _facts(name="Lefebvre Alexandre", trade_key="plombier", country="FR", city="Agnetz")

    _verify(
        facts,
        {
            "organic": [
                _result(
                    "https://www.facebook.com/alexandre.lefebvre.146069/",
                    "Alexandre Lefebvre",
                    "Alexandre Lefebvre est sur Facebook. Inscrivez-vous pour communiquer avec lui.",
                )
            ]
        },
        trade=_PLUMBER,
    )

    assert facts.facebook_url is None


def test_a_facebook_page_placed_in_the_town_is_the_business_page() -> None:
    facts = _facts()

    _verify(
        facts,
        {"organic": [_result("https://www.facebook.com/tendancenature/about", "Tendance Nature | Sion", "Jardins.")]},
    )

    assert facts.facebook_url == "https://www.facebook.com/tendancenature"


def test_an_email_in_a_directory_entry_of_the_business_is_proven_by_a_third_party() -> None:
    facts = _facts()

    _verify(
        facts,
        {
            "organic": [
                _result(
                    "https://www.local.ch/fr/d/sion/1950/tendance-nature",
                    "Tendance Nature – Paysagiste à Sion",
                    "Rte de la Courtaz 70. Emailtendance.nature@bluewin.ch",
                )
            ]
        },
    )

    assert (facts.email, facts.email_proof_level) == ("tendance.nature@bluewin.ch", EmailProofLevel.DIRECTORY.value)


def test_a_competitor_s_email_in_a_result_about_someone_else_is_not_taken() -> None:
    facts = _facts(name="Toupet Entretien Paysager", country="CA", city="Trois-Rivières", phone=None)
    results = [
        _result(
            "https://www.instagram.com/p/Dd02SWZx8Jh/",
            "Les feuilles commencent à tomber",
            "Elliotthautepression@gmail.com Entreprise locale à Champlain",
        )
    ]
    judge = _ScriptedJudge(
        JudgeVerdict(
            emails=[JudgedEmail(email="elliotthautepression@gmail.com", result_index=0, belongs_to_business=False)]
        )
    )

    _verify(facts, {"organic": results}, judge=judge)

    assert facts.email is None


def test_a_town_hall_address_is_never_a_business_email() -> None:
    facts = _facts()

    _verify(
        facts,
        {
            "organic": [
                _result(
                    "https://www.local.ch/fr/d/sion/1950/tendance-nature",
                    "Tendance Nature – Paysagiste à Sion",
                    "Contact commune : info@sion.ch",
                )
            ]
        },
    )

    assert facts.email is None


def test_a_chain_outlet_is_discarded_before_any_search() -> None:
    facts = _facts(name="Norauto Sion")
    client_judge = _verify(facts, {"organic": []})

    assert facts.is_chain is True
    assert facts.is_verified is False
    assert client_judge.call_count == 0


def test_a_search_that_does_not_answer_leaves_the_candidate_unverified() -> None:
    facts = _facts()

    _verify(facts, None)

    assert facts.is_verified is False


def test_the_panel_of_a_namesake_elsewhere_is_ignored_for_a_registry_candidate() -> None:
    facts = _facts(
        name="Garage Martin", origin=CandidateOrigin.REGISTRY_RGE.value, city="Beauvais", country="FR", phone=None
    )

    _verify(
        facts,
        {
            "knowledge": {
                "name": "Garage Martin",
                "address": "12 rue de la Gare, 13000 Marseille",
                "site": "https://garage-martin-marseille.fr",
            },
            "organic": [],
        },
    )

    assert facts.website is None
    assert facts.is_other_business is True


def test_a_same_name_panel_without_an_address_does_not_make_another_business() -> None:
    facts = _facts(
        name="Dupont Chauffage",
        trade_key="plombier",
        origin=CandidateOrigin.REGISTRY_RGE.value,
        city="Beauvais",
        country="FR",
        phone=None,
    )

    _verify(
        facts, {"knowledge": {"name": "Dupont Chauffage", "phone": "03 44 00 00 00"}, "organic": []}, trade=_PLUMBER
    )

    assert facts.is_other_business is False


@pytest.mark.parametrize("business_name", ["Plomberie Leclerc", "Truffaut Paysage", "Garage Midason"])
def test_a_family_name_or_a_longer_word_is_not_taken_for_a_chain(business_name: str) -> None:
    facts = _facts(name=business_name, country="FR", city="Dijon")

    _verify(facts, {"organic": []})

    assert facts.is_chain is False
    assert facts.is_verified is True


def test_a_chain_written_with_a_hyphen_is_still_recognised() -> None:
    assert CandidateVerifier.is_chain_name("Feu-Vert Dijon") is True


def _serve_front_page(monkeypatch: pytest.MonkeyPatch, page_url: str, page_text: str) -> None:
    async def front_page(domain: str) -> tuple[str, str] | None:
        return page_url, page_text

    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(front_page))


def test_an_email_on_the_business_s_own_domain_replaces_a_directory_mini_site(monkeypatch: pytest.MonkeyPatch) -> None:
    facts = _facts(
        name="Toitures Morel",
        city="Dijon",
        country="FR",
        phone="06 10 85 23 00",
        email="contact@morel-toitures.fr",
        email_proof_level=EmailProofLevel.PUBLISHED.value,
        website="https://moreltoitures.wixsite.com/accueil",
        website_status=WebsiteStatus.PLACEHOLDER.value,
    )
    _serve_front_page(monkeypatch, "https://morel-toitures.fr/", "<title>Toitures Morel, couvreur à Dijon</title>")

    asyncio.run(CandidateVerifier.consider_email_domain(facts, TradeCatalog.resolve("couvreur")))

    assert (facts.website, facts.website_status) == ("https://morel-toitures.fr/", WebsiteStatus.LIVE.value)
    assert facts.evidence[-1]["source"] == "Le domaine de son email répond"


def test_an_internet_provider_s_front_page_is_not_the_business_s_website(monkeypatch: pytest.MonkeyPatch) -> None:
    facts = _facts(email="tendance.nature@netplus.ch", email_proof_level=EmailProofLevel.PUBLISHED.value)
    _serve_front_page(monkeypatch, "https://www.netplus.ch/", "<title>net+ Internet, TV et téléphonie</title>")

    asyncio.run(CandidateVerifier.consider_email_domain(facts, _LANDSCAPER))

    assert facts.website is None


def test_a_working_website_already_known_is_not_looked_for_again(monkeypatch: pytest.MonkeyPatch) -> None:
    facts = _facts(
        email="info@tendance-nature.ch",
        website="https://tendance-nature.ch/",
        website_status=WebsiteStatus.LIVE.value,
    )

    async def must_not_be_called(domain: str) -> tuple[str, str] | None:
        raise AssertionError("the front page of a business with a working website was fetched")

    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(must_not_be_called))

    asyncio.run(CandidateVerifier.consider_email_domain(facts, _LANDSCAPER))

    assert facts.website == "https://tendance-nature.ch/"
