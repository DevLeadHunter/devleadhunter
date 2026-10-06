"""Verifying one candidate: what a single search page proves, with the web and the judge replaced by canned answers."""

import asyncio
from typing import Any

import pytest

from enums.prospect_search import CandidateOrigin, CandidateRejectReason, EmailProofLevel, ProspectSearchChannel
from enums.website_status import WebsiteStatus
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.contact_finder import ContactFinder
from services.prospect_search.search_judge import JudgedEmail, JudgeVerdict, SearchJudge, SearchResultLine
from services.prospect_search.trade_catalog import TradeCatalog
from services.website_liveness_service import website_liveness_service

_LANDSCAPER = TradeCatalog.resolve("paysagiste")
_PLUMBER = TradeCatalog.resolve("plombier")
_ELECTRICIAN = TradeCatalog.resolve("électricien")
_GARAGE = TradeCatalog.resolve("garage")
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=None)


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


def test_a_register_writing_the_company_in_liquidation_closes_it() -> None:
    facts = _facts(name="ZTD électricité", city="Vernayaz", trade_key="electricien", phone="076 000 00 17")

    _verify(
        facts,
        {
            "organic": [
                _result(
                    "https://www.moneyhouse.ch/fr/company/ztd-electricite-sarl-12378620581",
                    "ZTD Electricité Sàrl en liquidation",
                    "ZTD Electricité Sàrl en liquidation à Vernayaz ✓ en liquidation ✓ Fondée 2022",
                )
            ]
        },
        trade=_ELECTRICIAN,
    )
    verdict = CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY)

    assert (verdict.reject_reason, verdict.detail) == (
        CandidateRejectReason.CLOSED,
        "Société en liquidation selon moneyhouse.ch.",
    )


def test_a_neighbour_in_liquidation_on_the_same_register_page_does_not_close_the_business() -> None:
    facts = _facts(name="Mécanique GT'n'Co", city="Vernayaz", trade_key="garage", phone="027 764 11 22")

    _verify(
        facts,
        {
            "organic": [
                _result(
                    "https://www.help.ch/firma/CHE-206.831.147/ztd-electricite-sarl-en-liquidation-vernayaz",
                    "ZTD Electricité Sàrl en liquidation in Vernayaz",
                    "Unter der Adresse Route de la Cascade 3a, 1904 Vernayaz sind neben ZTD Electricité Sàrl en "
                    "liquidation auch diese Unternehmen eingetragen: Mécanique GT'n'Co",
                )
            ]
        },
        trade=_GARAGE,
    )

    assert facts.is_closed is False


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


def _find_contact(facts: CandidateFacts, results: list[dict[str, str]]) -> None:
    finder = ContactFinder(_OnePageClient({"organic": results}), _ScriptedJudge())  # type: ignore[arg-type]
    asyncio.run(finder.find(facts, _LANDSCAPER))


def test_the_phone_number_finds_the_email_a_directory_lists_under_another_name() -> None:
    facts = _facts(
        name="Architecte paysagiste Déco- Jardin Sàrl",
        city="Troistorrents",
        phone="079 204 45 56",
        facebook_url="https://www.facebook.com/decojardin",
        is_facebook_page_read=True,
    )

    _find_contact(
        facts,
        [
            _result(
                "https://www.local.ch/fr/d/troistorrents/1872/deco-jardin-sarl",
                "DECO-JARDIN Sàrl à Troistorrents",
                "DECO-JARDIN Sàrl · Portable: 079 204 45 56* · E-mail: decojars@bluewin.ch.",
            )
        ],
    )

    assert (facts.email, facts.email_proof_level) == ("decojars@bluewin.ch", EmailProofLevel.DIRECTORY.value)


def test_a_list_of_businesses_showing_the_phone_number_gives_no_email() -> None:
    facts = _facts(phone="079 204 45 56", facebook_url="https://www.facebook.com/x", is_facebook_page_read=True)

    _find_contact(
        facts,
        [
            _result(
                "https://annuaire.example.ch/paysagistes/monthey",
                "Paysagistes à Monthey",
                "Dupont 079 204 45 56 dupont@bluewin.ch ; Martin 079 111 22 33 martin.jardin@bluewin.ch",
            )
        ],
    )

    assert facts.email is None


def test_an_email_in_a_result_without_the_phone_number_is_not_taken_by_the_phone_search() -> None:
    facts = _facts(phone="079 204 45 56", facebook_url="https://www.facebook.com/x", is_facebook_page_read=True)

    _find_contact(
        facts,
        [
            _result(
                "https://www.local.ch/fr/d/sion/autre",
                "Autre Jardin à Sion",
                "Portable: 079 999 88 77 · autre@bluewin.ch",
            )
        ],
    )

    assert facts.email is None


def test_a_long_listing_title_is_searched_unquoted_and_its_phone_proves_the_directory_entry() -> None:
    facts = _facts(name="Architecte paysagiste Déco- Jardin Sàrl", city="Troistorrents", phone="079 204 45 56")
    client = _OnePageClient(
        {
            "organic": [
                _result(
                    "https://www.local.ch/fr/d/troistorrents/1872/deco-jardin-sarl",
                    "DECO-JARDIN Sàrl à Troistorrents",
                    "DECO-JARDIN Sàrl · Portable: 079 204 45 56* · E-mail: decojars@bluewin.ch.",
                )
            ]
        }
    )

    asyncio.run(ContactFinder(client, _ScriptedJudge()).find(facts, _LANDSCAPER))  # type: ignore[arg-type]

    assert client.queries[1].startswith("Architecte paysagiste Déco- Jardin Sàrl Troistorrents email")
    assert (facts.email, facts.email_proof_level) == ("decojars@bluewin.ch", EmailProofLevel.DIRECTORY.value)


def test_a_short_name_is_searched_word_for_word() -> None:
    facts = _facts(phone=None)
    client = _OnePageClient({"organic": []})

    asyncio.run(ContactFinder(client, _ScriptedJudge()).find(facts, _LANDSCAPER))  # type: ignore[arg-type]

    assert client.queries[-1].startswith('"Tendance Nature" Sion email')


def test_a_name_inside_a_longer_word_does_not_name_the_business() -> None:
    facts = _facts(name="André & Jardin", city="Diesse", phone="076 000 00 18")

    assert CandidateVerifier.names_business("Jardins Alexandre SA - Corminboeuf", facts, _LANDSCAPER) is False
    assert CandidateVerifier.names_business("André & Jardin, paysagiste à Diesse", facts, _LANDSCAPER) is True


def test_a_post_of_another_page_naming_the_business_is_not_its_page() -> None:
    facts = _facts(name="Jardin-Création", city="Aigle", phone="079 000 00 19")
    magazine_post = SearchResultLine(
        link="https://www.facebook.com/ZEmag36/posts/daniel-moquet-signe-vos-jardins-creation-paysagere-123/",
        host="facebook.com",
        title="Jardin Création - Daniel Moquet signe vos jardins",
        description="Entretien, création paysagère, aménagement de jardin.",
    )
    own_post = SearchResultLine(
        link="https://www.facebook.com/jardincreationaigle/posts/456/",
        host="facebook.com",
        title="Jardin Création - Nos réalisations",
        description="Création paysagère à Aigle.",
    )

    assert CandidateVerifier.is_facebook_page_of(magazine_post, facts, _LANDSCAPER) is False
    assert CandidateVerifier.is_facebook_page_of(own_post, facts, _LANDSCAPER) is True


def test_the_email_of_a_namesake_showing_another_number_is_not_taken() -> None:
    facts = _facts(name="Les jardins de Valentin", city="Bienne", phone="078 000 00 20")
    page = {
        "organic": [
            _result(
                "https://www.facebook.com/lesjardinsdevalentin/?locale=fr_FR",
                "Les jardins de valentin (@lesjardinsdevalentin)",
                "Pour tout renseignement : Mail : valentin.jardins@gmail.com Tél : 0470.00.00.01.",
            )
        ]
    }

    asyncio.run(ContactFinder(_OnePageClient(page), _ScriptedJudge()).find(facts, _LANDSCAPER))  # type: ignore[arg-type]

    assert facts.email is None


def test_a_listing_named_after_its_website_has_that_website() -> None:
    facts = _facts(name="Brunet Dijon-Paysagiste.fr", city="Dijon", country="FR", phone="06 12 34 56 78")

    _verify(facts, {"organic": []})

    assert facts.website == "https://dijon-paysagiste.fr/"


def test_the_site_publishing_the_email_under_a_name_from_that_address_is_the_website() -> None:
    facts = _facts(
        name="Plaisir Paysage", city="Dijon", country="FR", phone="06 00 00 00 21", email="passion.paysage21@gmail.com"
    )
    facts.add_evidence(
        "email", facts.email or "", source="passion-paysage-dijon.fr", url="https://passion-paysage-dijon.fr/contact"
    )

    asyncio.run(CandidateVerifier.consider_email_source_site(facts, _LANDSCAPER))

    assert (facts.website, facts.website_status) == ("https://passion-paysage-dijon.fr/", WebsiteStatus.LIVE.value)


def test_a_town_hall_page_quoting_the_email_is_not_the_website() -> None:
    facts = _facts(name="Jardin Conseil", city="Le Noirmont", email="secretariat@jardinconseil.ch")
    facts.add_evidence(
        "email", facts.email or "", source="noirmont.ch", url="https://www.noirmont.ch/Entreprises/Paysagistes"
    )

    asyncio.run(CandidateVerifier.consider_email_source_site(facts, _LANDSCAPER))

    assert facts.website is None


def test_an_email_domain_spelling_the_business_name_is_its_website(monkeypatch: pytest.MonkeyPatch) -> None:
    facts = _facts(name="Bcp Paysagistes", city="Dijon", country="FR", phone=None, email="contact@bcp-paysagiste.com")
    _serve_front_page(
        monkeypatch,
        "https://bcp-paysagiste.com/",
        "<title>Votre paysagiste à Dijon, Bourgogne Création Paysage</title>",
    )

    asyncio.run(CandidateVerifier.consider_email_domain(facts, _LANDSCAPER))

    assert facts.website == "https://bcp-paysagiste.com/"


def test_an_email_under_a_facebook_group_post_is_a_stranger_s() -> None:
    facts = _facts(name="Pelouse Sylex", city="Victoriaville", country="CA", phone="(819) 352-0428")
    page = {
        "organic": [
            _result(
                "https://www.facebook.com/groups/EmploiVictoriaville/posts/24567126339604367/",
                "Pelouse Sylex recrute!",
                "Emploi Victoriaville et sa région. Nettoyage A+ menage.aplus@outlook.com · Read more",
            )
        ]
    }

    asyncio.run(ContactFinder(_OnePageClient(page), _ScriptedJudge()).find(facts, _LANDSCAPER))  # type: ignore[arg-type]

    assert facts.email is None


@pytest.mark.parametrize(
    ("link", "title", "description"),
    [
        (
            "https://turismoroma.it/de/node/116484",
            "Casa per Ferie Suore",
            "Casa per Ferie Suore 0600000022. Email: casaferie.roma@gmail.com",
        ),
        (
            "https://www.facebook.com/groups/1283255909671137/posts/1647369846593073/",
            "Entraide Pau",
            "Votre extérieur, notre métier 06 00 00 00 22 servicepau@gmail.com",
        ),
        (
            "https://paysdenay.fr/item/download/2002_986807a36e4a7ecec877bf2c515dad94",
            "Décision du président",
            "Lot 13 : 06 00 00 00 22. Lot 14 : entreprise voisine sgr.voisin@orange.fr",
        ),
    ],
)
def test_the_phone_search_takes_no_email_from_a_foreign_page_a_group_or_a_document(
    link: str, title: str, description: str
) -> None:
    facts = _facts(name="Garage Négoce Auto Paloise", city="Pau", country="FR", phone="06 00 00 00 22")
    page = {"organic": [_result(link, title, description)]}

    asyncio.run(ContactFinder(_OnePageClient(page), _ScriptedJudge()).find(facts, TradeCatalog.resolve("garage")))  # type: ignore[arg-type]

    assert facts.email is None


def test_an_email_domain_spelling_the_name_without_its_legal_form_is_its_website(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    facts = _facts(name="ADN Autos Sàrl", city="Bulle", phone=None, email="info@adnauto.ch")
    _serve_front_page(monkeypatch, "https://adnauto.ch/", "<title>Bienvenue</title>")

    asyncio.run(CandidateVerifier.consider_email_domain(facts, TradeCatalog.resolve("garage")))

    assert facts.website == "https://adnauto.ch/"
