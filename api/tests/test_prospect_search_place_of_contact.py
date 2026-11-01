"""
Round 13 of the search training (search n° 17's landscapers and electricians): an email or a page of a namesake
elsewhere in France, a town taken from the search, a page about someone else, another trade, a network. Each case is
a real one, its numbers and its people replaced.
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
from services.prospect_search.contact_finder import ContactFinder
from services.prospect_search.french_registry import FrenchRegistry
from services.prospect_search.place_of_contact import PlaceOfContact
from services.prospect_search.search_judge import JudgedEmail, JudgeVerdict, SearchJudge, SearchResultLine
from services.prospect_search.trade_catalog import TradeCatalog
from services.website_liveness_service import website_liveness_service

_LANDSCAPER = TradeCatalog.resolve("paysagiste")
_ELECTRICIAN = TradeCatalog.resolve("électricien")
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=4.0)
_DEPARTMENT_BY_TOWN: dict[str, str] = {"Reims": "51", "Nancy": "54", "Périgueux": "24", "Niort": "79"}


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
    """Every website answers, no email domain shows a page, and the communes of the cases are known."""

    async def live(website: str | None) -> WebsiteStatus | None:
        return WebsiteStatus.LIVE if website else None

    async def no_front_page(domain: str) -> tuple[str, str] | None:
        return None

    async def communes_named(town: str) -> list[dict[str, Any]]:
        department = _DEPARTMENT_BY_TOWN.get(town)
        return [{"nom": town, "codeDepartement": department}] if department else []

    monkeypatch.setattr(website_liveness_service, "check_website_status", live)
    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(no_front_page))
    monkeypatch.setattr(FrenchDepartments, "_communes_named", staticmethod(communes_named))


def _facts(name: str, searched_city: str, trade: str = "paysagiste", **overrides: object) -> CandidateFacts:
    """A French listing of the search, found from *searched_city*."""
    values: dict[str, object] = {
        "name": name,
        "trade_key": trade,
        "country": "FR",
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "searched_city": searched_city,
        "google_category": "Paysagiste" if trade == "paysagiste" else "Électricien",
        "google_rating": 5.0,
        "google_reviews_count": 12,
    }
    values.update(overrides)
    return CandidateFacts(**values)  # type: ignore[arg-type]


def _result(link: str, title: str, description: str, display_link: str | None = None) -> dict[str, str]:
    result = {"link": link, "title": title, "description": description}
    return {**result, "display_link": display_link} if display_link else result


def _verify(facts: CandidateFacts, results: list[dict[str, str]], judge: _ScriptedJudge, trade: Any) -> None:
    verifier = CandidateVerifier(_OnePageClient({"organic": results}), judge)  # type: ignore[arg-type]
    asyncio.run(verifier.verify(facts, trade))


@pytest.mark.parametrize(
    ("name", "town", "trade", "title", "description", "email"),
    [
        (
            "DAM'ELEC",
            "Coulon",
            _ELECTRICIAN,
            "DAM ELEC services | Péronne",
            "Dam Elec Services ; +33 6 00 00 00 06 ; damelecservice@outlook.fr ...",
            "damelecservice@outlook.fr",
        ),
        (
            "greentouch",
            "Reims",
            _LANDSCAPER,
            "GREEN TOUCH (@greentouchexemple)",
            "N'hésitez pas à nous contacter pour un devis gratuit ! TEL: 0400000048 EMAIL: contact.greentouch@gmail.com",
            "contact.greentouch@gmail.com",
        ),
    ],
)
def test_an_email_written_beside_another_number_is_that_number_s_owner_s(
    name: str, town: str, trade: Any, title: str, description: str, email: str
) -> None:
    """A namesake's page writes its own number beside its address: the judge giving it the business changes nothing."""
    facts = _facts(name, town, trade=trade.key, city=town, phone="06 00 00 00 31")
    judge = _ScriptedJudge(JudgeVerdict(emails=[JudgedEmail(email=email, result_index=0, belongs_to_business=True)]))

    _verify(facts, [_result("https://www.exemple-annuaire.fr/fiche", title, description)], judge, trade)

    assert facts.email is None


def test_the_directory_entry_after_the_business_s_number_gives_its_email_to_the_next_business() -> None:
    """A town's list of businesses: the email follows the next business's number, not Aurelec's."""
    facts = _facts(
        "Aurelec",
        "Clermont-Ferrand",
        trade="electricien",
        city="Beaumont",
        address="Rue Gaspard Monge, 63110 Beaumont",
        phone="04 73 00 00 58",
        is_verified=True,
        facebook_url="https://www.facebook.com/aurelecexemple",
        is_facebook_page_read=True,
    )
    finder = ContactFinder(
        _OnePageClient(
            {
                "organic": [
                    _result(
                        "https://www.beaumont-exemple.fr/vie-des-entreprises/",
                        "La vie des entreprises de Beaumont - BEAU AURELEC",
                        "Rue Gaspard Monge - 04.73.00.00.58. EXEMPLE Marc. 225, route de ... "
                        "04.73.00.00.37 courriel : lannexe@wanadoo.fr. Mécanique générale.",
                    )
                ]
            }
        ),
        _ScriptedJudge(),
    )  # type: ignore[arg-type]

    asyncio.run(finder.find(facts, _ELECTRICIAN))

    assert facts.email is None


def test_a_page_in_another_script_sharing_the_number_s_digits_is_never_the_business_s() -> None:
    """A Korean job offer whose phone has the same digits as the electrician's French number gives no email."""
    facts = _facts(
        "Exemple Électricité",
        "Périgueux",
        trade="electricien",
        city="Périgueux",
        address="110 Rue Exemple, 24000 Périgueux",
        phone="05 00 00 98 85",
        is_verified=True,
        facebook_url="https://www.facebook.com/exempleelectricite",
        is_facebook_page_read=True,
    )
    finder = ContactFinder(
        _OnePageClient(
            {
                "organic": [
                    _result(
                        "https://www.google.com/goto?url=CAESwQEB6zswFZ8NpNSE",
                        "시스템에어컨 전산업무 및 입찰사무원 모집합니다",
                        "관리부. 전화번호, 0500009885. 휴대번호. 팩스. 이메일, exemple@naver.com. 회사주소, 50444 경상남도",
                    )
                ]
            }
        ),
        _ScriptedJudge(),
    )  # type: ignore[arg-type]

    asyncio.run(finder.find(facts, _ELECTRICIAN))

    assert facts.email is None


def test_a_news_page_in_another_script_gives_the_verification_no_email() -> None:
    """GL Énergie's search returned a Korean daily's article signed by a journalist's address."""
    facts = _facts(
        "GL EnergiE électricité générale", "Niort", trade="electricien", city="Niort", phone="06 00 00 00 03"
    )
    news = _result(
        "https://www.google.com/goto?url=CAESbwHrOzAVgUTb",
        "청원 60만 돌파",
        "청원 60만 돌파 '10만 추가에 하루도 안 걸려'. 기자 exemple@imaeil.com. 입력 2024-06-29",
    )
    judge = _ScriptedJudge(
        JudgeVerdict(emails=[JudgedEmail(email="exemple@imaeil.com", result_index=0, belongs_to_business=True)])
    )

    _verify(facts, [news], judge, _ELECTRICIAN)

    assert facts.email is None


def test_an_email_from_a_page_placing_the_business_nowhere_is_left_to_confirm() -> None:
    """« Pierrot Elagage, La Crau, FR »: a namesake's directory entry in the Var, for a tree surgeon found in Reims."""
    facts = _facts("Elagage Pierrot", "Reims", city="Reims", phone="03 00 00 00 79")

    _verify(
        facts,
        [
            _result(
                "https://www.google.com/goto?url=CAESlQEB6zswFQ8hz4Rw",
                "Pierrot Elagage, La Crau, FR | Informations sur l'entreprise",
                "Contact; Photo. email pierrot.elagage@gmail.com · Pierrot Elagage. 0 Commentaires.",
                display_link="https://www.annuaire-exemple.fr › entreprise",
            )
        ],
        _ScriptedJudge(),
        _LANDSCAPER,
    )
    verdict = CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY)

    assert (facts.email, facts.email_proof_level) == ("pierrot.elagage@gmail.com", EmailProofLevel.GUESSED.value)
    assert verdict.status == CandidateStatus.TO_CONFIRM
    assert verdict.detail == (
        "La page qui donne son email (pierrot.elagage@gmail.com) ne dit pas où il est : à vérifier, ce peut être "
        "un homonyme."
    )


def test_an_email_from_a_page_showing_the_business_s_number_stays_proven() -> None:
    """Jardin Authentique: the page giving its email shows its number beside it, which places it."""
    facts = _facts("Jardin Authentique", "Clermont-Ferrand", phone="06 00 00 11 19")

    _verify(
        facts,
        [
            _result(
                "https://www.annuaire-exemple.fr/jardin-authentique",
                "Jardin Authentique - Du rêve au jardin il n'y a qu'un pas",
                "N'hésitez pas à nous contacter 06 00 00 11 19 jardinauthentique63@gmail.com.",
            )
        ],
        _ScriptedJudge(),
        _LANDSCAPER,
    )

    assert (facts.email, facts.email_proof_level) == (
        "jardinauthentique63@gmail.com",
        EmailProofLevel.DIRECTORY.value,
    )


@pytest.mark.parametrize(
    ("name", "searched_city", "trade", "overrides", "place"),
    [
        (
            "Rg Élec",
            "Nancy",
            "electricien",
            {"email": "rg.elec.89@gmail.com"},
            "89",
        ),
        (
            "Ogelec",
            "Périgueux",
            "electricien",
            {"email": "kisscool29@aol.com"},
            "29",
        ),
        (
            "Flash Elec 24",
            "Périgueux",
            "electricien",
            {"email": "flashelecidf@outlook.com", "city": "Périgueux", "address": "4 Rue Exemple, 24000 Périgueux"},
            "idf",
        ),
        (
            "Les Jardins d'Eden",
            "Reims",
            "paysagiste",
            {
                "email": "lejardindeden.occitanie@gmail.com",
                "facebook_url": "https://www.facebook.com/Lejardindeden.occitanie",
            },
            "occitanie",
        ),
        (
            "JS ÉLECTRICITÉ",
            "Nancy",
            "electricien",
            {"email": "js-electricite@hotmail.com", "facebook_url": "https://www.facebook.com/jselectricitebelux"},
            "belux",
        ),
    ],
)
def test_an_email_or_a_page_naming_another_place_leaves_the_business_to_confirm(
    name: str, searched_city: str, trade: str, overrides: dict[str, str], place: str
) -> None:
    facts = _facts(name, searched_city, trade=trade, is_verified=True, phone="06 00 00 00 11", **overrides)
    facts.add_evidence("email", overrides["email"], source="Page Facebook", url=overrides.get("facebook_url"))

    asyncio.run(PlaceOfContact.note_contact_elsewhere(facts))
    verdict = CandidateDecision.decide(facts, TradeCatalog.resolve(trade), _EMAIL_ONLY)

    assert verdict.status == CandidateStatus.TO_CONFIRM
    assert verdict.detail is not None and f"désigne un autre endroit ({place})" in verdict.detail


def test_the_facebook_page_an_email_was_read_on_tells_its_place() -> None:
    """Asser of Nancy: the email comes from the page « Asser84700 », a sports club of Sorgues."""
    facts = _facts(
        "Asser",
        "Nancy",
        trade="electricien",
        city="Nancy",
        address="69 Rue Exemple, 54000 Nancy",
        is_verified=True,
        email="assercommunication@gmail.com",
    )
    facts.add_evidence(
        "email", "assercommunication@gmail.com", source="facebook.com", url="https://www.facebook.com/Asser84700/"
    )

    asyncio.run(PlaceOfContact.note_contact_elsewhere(facts))

    assert facts.contact_elsewhere is not None
    assert (facts.contact_elsewhere["source"], facts.contact_elsewhere["value"]) == (
        "La page Facebook de son email",
        "84700",
    )


def test_an_email_of_the_business_s_own_department_names_no_other_place() -> None:
    facts = _facts("La petite Maçonnerie", "Reims", is_verified=True, email="lapetitemaconnerie51@gmail.com")
    facts.add_evidence("email", "lapetitemaconnerie51@gmail.com", source="google.com")

    asyncio.run(PlaceOfContact.note_contact_elsewhere(facts))

    assert facts.contact_elsewhere is None


def test_a_listing_without_address_is_not_kept_on_the_searched_town_alone() -> None:
    facts = _facts("Exemple Paysage", "Périgueux", is_verified=True, phone="06 00 00 00 86")
    facts.offer_email("exemplepaysage@gmail.com", EmailProofLevel.PUBLISHED, source="Page Facebook")

    verdict = CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY)

    assert (verdict.status, verdict.detail) == (
        CandidateStatus.TO_CONFIRM,
        "Sa fiche Google ne donne pas d'adresse : rien ne montre qu'il est à Périgueux, à vérifier.",
    )


def test_the_registry_gives_a_listing_without_address_the_commune_of_the_company_of_its_name() -> None:
    """« Les Jardins d'Odin » found from Reims is the trade name of a sole trader of Cormontreuil."""
    facts = _facts("Les jardins d'Odin", "Reims", is_verified=True, phone="06 00 00 00 54")
    facts.offer_email("lesjardinsdodin@gmail.com", EmailProofLevel.PUBLISHED, source="Page Facebook")
    named = [
        {
            "siren": "900000001",
            "nom_complet": "MARC EXEMPLE (LES JARDINS D'ODIN)",
            "etat_administratif": "A",
            "siege": {"code_postal": "51350", "libelle_commune": "CORMONTREUIL"},
        },
        {
            "siren": "900000002",
            "nom_complet": "JARDINS ET ODIN SERVICES",
            "etat_administratif": "A",
            "siege": {"code_postal": "51100", "libelle_commune": "REIMS"},
        },
    ]

    FrenchRegistry.place_listing_without_address(facts, named)
    verdict = CandidateDecision.decide(facts, _LANDSCAPER, _EMAIL_ONLY)

    assert (facts.address, facts.city) == ("51350 Cormontreuil", "Cormontreuil")
    assert verdict.status == CandidateStatus.KEPT


@pytest.mark.parametrize(
    ("name", "trade"),
    [("La petite Maçonnerie", "paysagiste"), ("Solosecc Chauffagiste", "electricien")],
)
def test_a_name_saying_another_trade_is_not_the_searched_trade(name: str, trade: str) -> None:
    facts = _facts(name, "Reims", trade=trade, city="Reims", is_verified=True, email="contact@exemple.fr")

    verdict = CandidateDecision.decide(facts, TradeCatalog.resolve(trade), _EMAIL_ONLY)

    assert (verdict.status, verdict.reject_reason) == (CandidateStatus.REJECTED, CandidateRejectReason.WRONG_TRADE)
    assert verdict.detail == f"Son nom dit un autre métier que celui cherché : « {name} »."


@pytest.mark.parametrize(
    ("facebook_page", "is_association"),
    [
        ("https://www.facebook.com/p/N%C3%AEmes-Gazelec-Sportif-Gardois-100057202699574/", True),
        ("https://www.facebook.com/gazelecexemple", False),
    ],
)
def test_a_club_the_registry_files_as_an_association_is_no_business(facebook_page: str, is_association: bool) -> None:
    """Gazelec S. Gardois: sports associations at the registry, and a page saying « Sportif »."""
    facts = _facts(
        "Gazelec S. Gardois", "Nîmes", trade="electricien", city="Nîmes", is_verified=True, email="club@exemple.fr"
    )
    facts.add_evidence(
        "facebook", "https://www.facebook.com/100057202699574", source="Recherche Facebook", url=facebook_page
    )
    named = [
        {
            "nom_complet": f"ASS SPORTIVE GAZELEC GARDOIS {section}",
            "nature_juridique": "9220",
            "etat_administratif": "A",
            "siege": {"code_postal": "30000", "libelle_commune": "NIMES"},
        }
        for section in ("FOOTBALL", "TIR")
    ]

    FrenchRegistry.note_association(facts, named)
    verdict = CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY)

    assert (verdict.reject_reason == CandidateRejectReason.WRONG_TRADE) is is_association


def test_an_email_on_the_domain_of_the_ppf_network_makes_an_outlet() -> None:
    facts = _facts(
        "PPF Niort",
        "Niort",
        trade="electricien",
        city="Chauray",
        is_verified=True,
        email="contact@preservationdupatrimoine.fr",
    )

    asyncio.run(CandidateVerifier.consider_email_domain(facts, _ELECTRICIAN))
    verdict = CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY)

    assert (verdict.status, verdict.reject_reason) == (CandidateStatus.REJECTED, CandidateRejectReason.CHAIN)


def test_a_page_putting_another_word_in_place_of_the_trade_is_another_business_s() -> None:
    """« La Taverne d'Odin » is not the page of « Les jardins d'Odin », though it carries « Odin »."""
    facts = _facts("Les jardins d'Odin", "Reims")
    tavern = SearchResultLine(
        link="https://www.facebook.com/tavernedodin",
        host="facebook.com",
        title="La Taverne d'Odin | Facebook",
        description="La Taverne d'Odin, Reims. Bar à jeux, bières artisanales.",
    )
    own_page = SearchResultLine(
        link="https://www.facebook.com/jardinsdodin",
        host="facebook.com",
        title="Les Jardins d'Odin - Paysagiste",
        description="Entretien de jardins à Reims et alentours.",
    )

    assert CandidateVerifier.is_facebook_page_of(tavern, facts, _LANDSCAPER) is False
    assert CandidateVerifier.is_facebook_page_of(own_page, facts, _LANDSCAPER) is True


def test_elec_is_a_trade_word_so_another_elec_s_page_does_not_name_the_business() -> None:
    """« BC Elec » shares only « Elec » with « M.A.S ELEC 30 »: its page and its email are another electrician's."""
    facts = _facts("M.A.S ELEC 30", "Nîmes", trade="electricien", city="Nîmes")

    assert CandidateVerifier.names_business("BC Elec", facts, _ELECTRICIAN) is False


def test_the_panel_s_address_gives_a_listing_without_town_its_town() -> None:
    facts = _facts("Les jardins d'Odin", "Reims", phone="06 00 00 00 54")
    page = {
        "organic": [_result("https://www.exemple-sans-rapport.fr/", "Une autre entreprise", "Rien sur elle.")],
        "knowledge": {"name": "Les Jardins d'Odin", "address": "12 Rue Exemple, 51350 Cormontreuil"},
    }

    asyncio.run(CandidateVerifier(_OnePageClient(page), _ScriptedJudge()).verify(facts, _LANDSCAPER))  # type: ignore[arg-type]

    assert (facts.address, facts.city) == ("12 Rue Exemple, 51350 Cormontreuil", "Cormontreuil")
