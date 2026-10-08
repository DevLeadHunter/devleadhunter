"""The owner the web names for a business, the first name customers call the owner by, and the accents kept."""

import asyncio
from typing import Any

import pytest

from services.decision_maker import web_owner
from services.decision_maker.given_names import GivenNames
from services.decision_maker.normalize import initials_in
from services.decision_maker.resolver import DecisionMakerResolver
from services.decision_maker.strategies import BusinessNameOwnerStrategy
from services.decision_maker.types import NameCandidate, NameResolution, ResolutionContext
from services.decision_maker.web_owner import OwnerMentions, WebOwnerStrategy
from services.prospect_search.business_name import BusinessName


def _result(title: str, description: str, link: str = "https://ca.linkedin.com/in/exemple") -> dict[str, str]:
    """One of Google's results."""
    return {"title": title, "description": description, "link": link}


def _owners(results: list[dict[str, str]], context: ResolutionContext) -> list[tuple[str | None, str | None]]:
    """The people the results name as the business's owner."""
    return [(candidate.first, candidate.last) for candidate in OwnerMentions.candidates_in(results, context)]


def test_a_profile_titled_owner_of_the_business_names_its_head() -> None:
    """« Marc Exemple - Propriétaire chez Exemple Paysage », in the business's town, is the person speaking."""
    context = ResolutionContext(company_name="Exemple Paysage", city="Shawinigan", country="CA")
    results = [
        _result(
            "Marc Exemple - Propriétaire chez Exemple Paysage",
            "Propriétaire chez Exemple Paysage · Location: Shawinigan · 50 connections on LinkedIn.",
        )
    ]

    [candidate] = OwnerMentions.candidates_in(results, context)

    assert (candidate.first, candidate.last) == ("Marc", "Exemple")
    assert candidate.self_declared
    assert candidate.confidence >= 0.7


def test_a_facebook_profile_naming_its_business_names_its_head() -> None:
    """« propriétaire at Garage Paul Exemple » on Paul's own profile, living in the business's town."""
    context = ResolutionContext(company_name="Garage Paul Exemple", city="Mascouche", country="CA")
    results = [
        _result(
            "Paul Exemple (@garagepaulexemple)",
            "Paul Exemple ; Lives in Mascouche, Quebec ; propriétaire at Garage Paul Exemple ;",
            link="https://www.facebook.com/garagepaulexemple/",
        )
    ]

    assert _owners(results, context) == [("Paul", "Exemple")]


def test_a_signature_on_the_business_page_holding_its_initials_is_the_surest() -> None:
    """The business's own page signs « Alain Exemple Propriétaire » beside its phone, and its name holds « A.E »."""
    context = ResolutionContext(
        company_name="Modèle Paysagement A.E", city="Shawinigan", phone="819 555-0199", country="CA"
    )
    results = [
        _result(
            "Modèle Paysagement A.E",
            "Merci de votre confiance, Alain Exemple Propriétaire Modèle Paysagement A.E (819)555-0199.",
            link="https://www.facebook.com/p/Modele-Paysagement-AE-100000000000000/",
        )
    ]

    [candidate] = OwnerMentions.candidates_in(results, context)

    assert (candidate.first, candidate.last) == ("Alain", "Exemple")
    assert candidate.self_declared
    assert candidate.confidence > 0.8


def test_an_owner_placed_in_another_town_is_a_namesake() -> None:
    """« J.T. Mécanique » of Terrebonne is not « Jt.mecanique », run from Montréal by someone with the same initials."""
    context = ResolutionContext(company_name="J.T. Mécanique", city="Terrebonne", country="CA")
    results = [
        _result(
            "Jules Témoin - Proprietaire mecanicien",
            "Jules Témoin. Proprietaire mecanicien. Jt.mecanique. Montreal, Quebec, Canada. 9 followers.",
        )
    ]

    assert _owners(results, context) == []


def test_a_former_owner_a_co_owner_or_the_owner_of_something_else_is_not_the_head() -> None:
    """A former owner, the co-owners, a building's or another business's owner never name this business's head."""
    former = _result(
        "Luc Exemple (@lucexemple)",
        "Lives in Victoriaville, Quebec ; Former propriétaire at Entretien JXM ;",
        link="https://www.facebook.com/lucexemple/",
    )
    building = _result(
        "Paul Exemple | Repentigny QC",
        "Nous sommes enfin propriétaire de notre local !!! ... Le Garage Modèle et fils sera fermé lundi ...",
        link="https://www.facebook.com/p/Paul-Exemple-100000000000000/",
    )
    others = _result(
        "Garage Témoin (@garagetemoin) - Mentions",
        "Une journée chez CX services mécaniques ... Michel Exemple, propriétaire de Garage Témoin à Victoriaville.",
        link="https://www.facebook.com/garagetemoin/mentions/",
    )
    co_owners = _result(
        "Exemple Terrassement",
        "Les propriétaires, Jean Exemple et Paul Modèle, répondent à vos demandes à Victoriaville.",
        link="https://exemple-terrassement.com/",
    )
    article = _result(
        "Les entrepreneurs de la région",
        "Luc Témoin, propriétaire ... Modèle, fondateur et gérant, Modèle Électrique, à Victoriaville ...",
        link="https://journal-exemple.ca/entrepreneurs",
    )
    directory = _result(
        "Garages près de Exempleville, QC",
        "... Garage Paul Exemple - Mécanique à Victoriaville ... Le propriétaire Hervé Témoin est serviable ...",
        link="https://annuaire-exemple.ca/garages",
    )
    own_page_owner = _result(
        "Exemple Terrassement",
        "Le propriétaire, Jean Exemple, répond à vos demandes à Victoriaville.",
        link="https://exemple-terrassement.com/",
    )

    here = ResolutionContext(company_name="Exemple Terrassement", city="Victoriaville")

    assert _owners([own_page_owner], here) == [("Jean", "Exemple")]
    assert _owners([former], ResolutionContext(company_name="Entretien JXM", city="Victoriaville")) == []
    assert _owners([building], ResolutionContext(company_name="Garage Modèle et Fils inc.", city="Repentigny")) == []
    assert _owners([others], ResolutionContext(company_name="C.X. Services Mécaniques", city="Victoriaville")) == []
    assert _owners([co_owners], ResolutionContext(company_name="Exemple Terrassement", city="Victoriaville")) == []
    assert _owners([article], ResolutionContext(company_name="Modèle Électrique Inc", city="Victoriaville")) == []
    assert _owners([directory], ResolutionContext(company_name="Garage Paul Exemple", city="Victoriaville")) == []


def test_a_name_saying_only_a_trade_and_a_town_is_never_searched() -> None:
    """« Entretien paysager Victoriaville » finds every landscaper of the town: the web is not asked."""

    class _Client:
        """A search engine that must not be asked."""

        is_configured = True

        async def google_parsed(self, query: str, **_options: Any) -> dict[str, Any]:
            """Fail the test."""
            raise AssertionError(f"searched {query}")

    context = ResolutionContext(company_name="Entretien paysager Victoriaville", city="Victoriaville", country="CA")

    assert asyncio.run(WebOwnerStrategy(client=_Client()).resolve(context)) == []


def test_a_search_answering_an_empty_page_is_asked_again(monkeypatch: pytest.MonkeyPatch) -> None:
    """The search engine often answers an empty page: the owner found on the next try is not lost."""
    monkeypatch.setattr(web_owner, "_SEARCH_RETRY_PAUSE_SECONDS", 0.0)
    profile = _result("Marc Exemple - Propriétaire chez Exemple Paysage", "Location: Shawinigan")
    answers: list[dict[str, Any] | None] = [None, {"organic": [profile]}]

    class _Client:
        """A search engine answering nothing the first time."""

        is_configured = True

        async def google_parsed(self, query: str, **_options: Any) -> dict[str, Any] | None:
            """The next answer."""
            return answers.pop(0)

    context = ResolutionContext(company_name="Exemple Paysage", city="Shawinigan", country="CA")

    [candidate] = asyncio.run(WebOwnerStrategy(client=_Client()).resolve(context))

    assert (candidate.first, candidate.last) == ("Marc", "Exemple")


def test_customers_naming_the_first_name_of_the_business_name_need_no_cue_word() -> None:
    """« Paul prend le temps d'expliquer » about « Garage Paul Exemple »: Paul Exemple, a proposal."""
    context = ResolutionContext(
        company_name="Garage Paul Exemple",
        review_texts=["Paul prend le temps d'expliquer, je recommande.", "Le Garage Paul Exemple est honnête."],
    )

    [candidate] = BusinessNameOwnerStrategy().candidates_of(context)

    assert (candidate.first, candidate.last) == ("Paul", "Exemple")
    assert candidate.confidence < 0.7


def test_the_initials_of_the_business_give_the_first_name_customers_call_the_owner_by() -> None:
    """« Atelier Mécanique JX » thanked twice as « Jules »: Jules, the J of JX; two first names tell nothing."""
    reviews = ["Jules est le meilleur mécano du coin.", "Merci Jules pour le travail !"]
    context = ResolutionContext(company_name="Atelier Mécanique JX", review_texts=reviews)
    two_first_names = ResolutionContext(
        company_name="Atelier Mécanique JX", review_texts=[*reviews, "Julien a tout réparé.", "Merci Julien !"]
    )

    [candidate] = BusinessNameOwnerStrategy().candidates_of(context)

    assert (candidate.first, candidate.last) == ("Jules", None)
    assert BusinessNameOwnerStrategy().candidates_of(two_first_names) == []


def test_a_legal_form_is_never_read_as_initials() -> None:
    """« SA » closes « Garage Exemple SA »: no initials; « A.E » and « JX » are."""
    assert initials_in(BusinessName.without_legal_form("Garage Exemple SA")) == []
    assert initials_in("Paysagiste Exemple A.E") == ["AE"]
    assert initials_in("Atelier Exemple JX") == ["JX"]


def test_the_name_keeps_the_accents_another_source_writes_it_with() -> None:
    """A profile writes « Jerome » without its accents where the business name writes « Jérôme »: the accents stay."""
    web = NameCandidate(
        first="Jerome",
        last="Exemple",
        source="web_owner",
        confidence=0.75,
        evidence_group="web_owner",
        self_declared=True,
    )
    business_name = NameCandidate(
        first="Jérôme", last="Exemple", source="business_name", confidence=0.6, evidence_group="customer_reviews"
    )

    resolution = DecisionMakerResolver().pick_best([web, business_name])

    assert resolution.status == NameResolution.AUTO
    assert resolution.candidate is not None
    assert resolution.candidate.first == "Jérôme"


def test_a_first_name_written_without_accents_takes_its_usual_spelling() -> None:
    """The registry writes « STEPHANE »: the greeting says « Stéphane », the way nearly all of them write it."""
    registry = NameCandidate(
        first="Stephane",
        last="Exemple",
        source="registre_gouv",
        confidence=0.9,
        primary=True,
        geo_confirmed=True,
        evidence_group="registry",
    )

    resolution = DecisionMakerResolver().pick_best([registry])

    assert resolution.candidate is not None
    assert resolution.candidate.first == "Stéphane"
    assert GivenNames.usual_spelling("FREDERIC") == "Frédéric"
    assert GivenNames.usual_spelling("Cedric") == "Cedric"


def test_a_trade_word_or_a_last_name_said_with_monsieur_names_nobody() -> None:
    """« Elec » is no last name, and « M. Martin » in a review calls Martin by a last name, not a first name."""
    strategy = BusinessNameOwnerStrategy()
    trade_word = ResolutionContext(company_name="Eurl Martin Elec", review_texts=["Martin a tout réparé."])
    civility = ResolutionContext(company_name="Garage Martin Exemple", review_texts=["M. Martin est très sérieux."])

    assert strategy.candidates_of(trade_word) == []
    assert strategy.candidates_of(civility) == []


def test_an_owner_placed_nowhere_and_without_the_phone_names_nobody() -> None:
    """« Jean Modèle, fondateur de Exemple Garage » on a page naming no town nor phone may be a namesake's owner."""
    context = ResolutionContext(company_name="Exemple Garage", city="Lausanne", phone="021 555 01 99", country="CH")
    results = [
        _result(
            "Exemple Garage - Soirée des entrepreneurs",
            "Jean Modèle, fondateur de Exemple Garage, partagera son parcours.",
            link="https://evenements-exemple.ch/soiree",
        )
    ]

    assert _owners(results, context) == []


def test_a_french_manager_is_the_head_and_a_quebec_one_is_not() -> None:
    """« Gérant | Exemple Services Extérieurs … à Pau » names the head in France; in Québec a gérant runs a shop."""
    profile = _result(
        "Luc Exemple - Gérant | Exemple Services Extérieurs",
        "Luc Exemple · Gérant | Exemple Services Extérieurs | Jardinier Paysagiste à Pau",
        link="https://fr.linkedin.com/in/exemple",
    )
    france = ResolutionContext(company_name="Exemple Services Extérieurs", city="Pau", country="FR")
    quebec = ResolutionContext(company_name="Exemple Services Extérieurs", city="Pau", country="CA")

    [candidate] = OwnerMentions.candidates_in([profile], france)

    assert (candidate.first, candidate.last, candidate.self_declared) == ("Luc", "Exemple", True)
    assert _owners([profile], quebec) == []


def test_a_presentation_opening_with_a_person_and_a_trade_names_the_owner() -> None:
    """The business presents itself as « Luc Exemple - Paysagiste indépendant »: Luc Exemple runs it."""
    context = ResolutionContext(
        company_name="Modèle Paysage",
        city="Exempleville",
        description="Luc Exemple - Paysagiste indépendant à Exempleville. Tonte, taille, création.",
    )
    without_trade = ResolutionContext(
        company_name="Modèle Paysage", description="Luc Exemple - Merci de votre visite !"
    )

    [candidate] = OwnerMentions.in_presentation(context)

    assert (candidate.first, candidate.last, candidate.self_declared) == ("Luc", "Exemple", True)
    assert candidate.evidence_group == "scraped_text"
    assert OwnerMentions.in_presentation(without_trade) == []
