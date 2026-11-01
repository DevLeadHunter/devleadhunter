"""
Round 17 of the search training (search n° 18 resumed): a region's abbreviation in an email, an email named after
someone other than the person the registry, a page or the listing names, a namesake's Facebook page for a listing
without address, and the owner the search read becoming the prospect's contact. Each case is a real one, its names,
numbers and people replaced.
"""

import asyncio
from typing import Any

import pytest
from sqlalchemy.orm import Session

from enums.prospect_search import CandidateOrigin, CandidateStatus, ProspectSearchChannel
from models.prospect_db import ProspectDB
from models.prospect_search_candidate import ProspectSearchCandidate
from services.decision_maker.email_owner import EmailOwnerStrategy
from services.decision_maker.resolver import DecisionMakerResolver, context_from_prospect
from services.decision_maker.search_owner import SearchOwnerStrategy
from services.decision_maker.strategies import BusinessNameOwnerStrategy
from services.decision_maker.types import NameResolution, ResolutionContext, SearchedOwner
from services.enrichment_service import EnrichmentService
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.french_registry import FrenchRegistry, french_registry
from services.prospect_search.place_of_contact import PlaceOfContact
from services.prospect_search.search_judge import SearchResultLine
from services.prospect_search.trade_catalog import TradeCatalog

_ELECTRICIAN = TradeCatalog.resolve("electricien")
_LANDSCAPER = TradeCatalog.resolve("paysagiste")
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=4.0)
_ALLOVOISINS_PAGE = "https://www.allovoisins.com/p/exemple-1"


def _facts(name: str, trade_key: str, **overrides: object) -> CandidateFacts:
    """A listing of the search, verified on Google."""
    values: dict[str, object] = {
        "name": name,
        "trade_key": trade_key,
        "country": "FR",
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "google_rating": 4.9,
        "google_reviews_count": 21,
        "is_verified": True,
    }
    values.update(overrides)
    return CandidateFacts(**values)  # type: ignore[arg-type]


def _electrician_of_nimes(email: str, name: str = "Exem dépannage d’urgence", **overrides: object) -> CandidateFacts:
    """An electrician of Nîmes whose email was read on a Facebook page a Google search found."""
    facts = _facts(
        name,
        "electricien",
        city="Nîmes",
        searched_city="Nîmes",
        address="25 Bd de l'Exemple, 30000 Nîmes",
        phone="06 00 00 00 01",
        email=email,
        email_proof_level="a",
        **overrides,
    )
    facts.add_evidence("email", email, source="Page Facebook", url="https://www.facebook.com/61500000000001")
    return facts


def _sas_of_nimes(activity: str = "43.21A") -> dict[str, Any]:
    """The company of the electrician's name at its address, run by one person written twice."""
    return {
        "siren": "000000001",
        "nom_complet": "EXEM DEPANNAGE D'URGENCE",
        "etat_administratif": "A",
        "dirigeants": [
            {
                "nom": "EXEMPLE",
                "prenoms": "JULLES",
                "qualite": "Président de SAS",
                "type_dirigeant": "personne physique",
            },
            {
                "nom": "EXEMPLE",
                "prenoms": "JULLES ALEC MAXIME",
                "qualite": "Président de SAS",
                "type_dirigeant": "personne physique",
            },
        ],
        "siege": {"code_postal": "30000", "libelle_commune": "NIMES", "activite_principale": activity},
    }


def _registry(monkeypatch: pytest.MonkeyPatch, companies: list[dict[str, Any]]) -> None:
    """The registry answers the same companies to every query."""

    async def answer(query: str, **_options: object) -> list[dict[str, Any]]:
        return companies

    monkeypatch.setattr(FrenchRegistry, "_companies", staticmethod(answer))


@pytest.mark.parametrize(
    ("address_part", "department", "place"),
    [
        ("exemelecidf", "24", "idf"),
        ("elecbzh", "75", "bzh"),
        ("elecbzh", "35", None),
        ("renovhdf", "33", "hdf"),
        ("ara.elec", "75", "ara"),
        ("clara.paysage", "75", None),
        ("laura.jardin", "13", None),
        ("paysage.languedocroussillon", "34", None),
        ("poitoucharentes", "79", None),
        ("auvergnerhonealpes", "75", "auvergnerhonealpes"),
    ],
)
def test_a_region_s_abbreviation_names_a_place_never_a_first_name_s_ending_nor_the_business_s_own_region(
    address_part: str, department: str, place: str | None
) -> None:
    assert PlaceOfContact.place_named_in_address(address_part, department) == place


def test_an_email_read_on_a_namesake_s_page_whose_address_says_another_region_is_left_to_confirm() -> None:
    """« exemelecidf@ », read beside another number on another « Exem Elec »'s page, for a Périgueux electrician."""
    facts = _facts(
        "Exem Elec 24",
        "electricien",
        city="Périgueux",
        searched_city="Périgueux",
        address="4 Rue de l'Exemple, 24000 Périgueux",
        phone="06 00 00 00 01",
        email="exemelecidf@outlook.com",
        email_proof_level="b",
    )
    facts.add_evidence(
        "email",
        "exemelecidf@outlook.com",
        source="facebook.com",
        url="https://www.facebook.com/p/Exem-Elec-61500000000002/",
        snippet="Exem Elec Personal details ; exemelecidf ; +33 7 00 00 00 02 ; exemelecidf@outlook.com ...",
    )

    asyncio.run(PlaceOfContact.note_contact_elsewhere(facts))
    verdict = CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY)

    assert (verdict.status, verdict.detail) == (
        CandidateStatus.TO_CONFIRM,
        "Son email (exemelecidf@outlook.com) désigne un autre endroit (idf) que Périgueux : à vérifier, ce peut "
        "être un homonyme.",
    )


@pytest.mark.parametrize(
    ("head", "person"),
    [
        ({"nom": "EXEMPLE", "prenoms": "JULLES ALEC", "qualite": "Président de SAS"}, "Julles Exemple"),
        ({"nom": "MODELE (TEMOIN)", "prenoms": "MARIE CLAIRE", "qualite": "Gérant"}, "Marie Modele (Temoin)"),
        ({"nom": "EXEMPLE (EXEMPLE)", "prenoms": "JULES", "qualite": "Entrepreneur"}, "Jules Exemple"),
        ({"nom": "TEMOIN", "prenoms": "PAUL", "qualite": "Liquidateur"}, None),
        ({"denomination": "EXEMPLE HOLDING", "qualite": "Président"}, None),
    ],
)
def test_a_head_of_the_registry_is_read_as_a_person_name_of_use_kept(head: dict[str, str], person: str | None) -> None:
    assert FrenchRegistry.person_of_head(head) == person


def test_an_email_named_after_someone_else_than_the_registry_s_head_is_left_to_confirm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """« temoin.jules@ » on a page a search found, while the registry writes Julles Exemple at the head of the SAS."""
    _registry(monkeypatch, [_sas_of_nimes()])
    facts = _electrician_of_nimes("temoin.jules@exemple.fr")

    asyncio.run(french_registry.read_closing(facts))
    verdict = CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY)

    assert [line["value"] for line in facts.evidence if line["fact"] == "registered_head"] == ["Julles Exemple"]
    assert (verdict.status, verdict.detail) == (
        CandidateStatus.TO_CONFIRM,
        "Son email (temoin.jules@exemple.fr) porte le nom de Jules Temoin, mais le registre des entreprises nomme "
        "Julles Exemple : à vérifier, ce n'est peut-être pas son adresse.",
    )


def test_the_email_rule_speaks_before_the_registered_activity_of_another_trade(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real SAS is registered for plumbing too: the email's doubt is the one the user must read first."""
    _registry(monkeypatch, [_sas_of_nimes(activity="43.22A")])
    facts = _electrician_of_nimes("temoin.jules@exemple.fr")

    asyncio.run(french_registry.read_closing(facts))
    verdict = CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY)

    assert facts.activity_of_another_trade is not None
    assert verdict.detail is not None and verdict.detail.startswith("Son email (temoin.jules@exemple.fr) porte le nom")


@pytest.mark.parametrize("email", ["exemple.jules@exemple.fr", "julles.exemple30@exemple.fr", "contact@exemple.fr"])
def test_an_email_bearing_the_head_s_name_or_naming_nobody_is_kept(monkeypatch: pytest.MonkeyPatch, email: str) -> None:
    _registry(monkeypatch, [_sas_of_nimes()])
    facts = _electrician_of_nimes(email)

    asyncio.run(french_registry.read_closing(facts))

    assert CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY).status == CandidateStatus.KEPT


def test_an_email_in_the_head_s_name_of_use_is_kept() -> None:
    facts = _electrician_of_nimes("temoin.marie@exemple.fr")
    facts.add_evidence("registered_head", "Marie Modele (Temoin)", source="Registre des entreprises (INSEE)")

    assert CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY).status == CandidateStatus.KEPT


def test_an_email_named_after_someone_else_than_the_owner_a_page_names_is_left_to_confirm() -> None:
    facts = _electrician_of_nimes("temoin.jules@exemple.fr", owner_name="Jules Exemple")
    facts.add_evidence("owner", "Jules Exemple", source="allovoisins.com", url=_ALLOVOISINS_PAGE)

    verdict = CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY)

    assert verdict.detail == (
        "Son email (temoin.jules@exemple.fr) porte le nom de Jules Temoin, mais allovoisins.com nomme Jules Exemple : "
        "à vérifier, ce n'est peut-être pas son adresse."
    )


def test_an_email_named_after_someone_else_than_the_person_the_listing_s_name_spells_is_left_to_confirm() -> None:
    facts = _electrician_of_nimes("temoin.jules@exemple.fr", name="Max'Elec Jules Exemple")

    verdict = CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY)

    assert verdict.status == CandidateStatus.TO_CONFIRM
    assert verdict.detail is not None and "mais le nom de sa fiche Google nomme Jules Exemple" in verdict.detail


def _listing_without_address() -> CandidateFacts:
    """A landscaper's Google listing found from Metz, with a phone but neither address nor town."""
    return _facts("JARDINS EXEMPLE", "paysagiste", searched_city="Metz", phone="06 00 00 00 03")


def _facebook_line(description: str) -> SearchResultLine:
    return SearchResultLine(
        link="https://www.facebook.com/jardinsexemple.fr/",
        host="facebook.com",
        title="Jardins Exemple | Facebook",
        description=description,
    )


def test_a_listing_without_address_takes_no_facebook_page_that_only_says_its_trade() -> None:
    """The namesake of Villeurbanne says « paysagiste »: so does every Jardins Exemple of France."""
    line = _facebook_line("Jardins Exemple, paysagiste à Villeurbanne et Lyon. Création et entretien de jardins.")

    assert not CandidateVerifier.is_facebook_page_of(line, _listing_without_address(), _LANDSCAPER)


@pytest.mark.parametrize(
    "description",
    [
        "Jardins Exemple, paysagiste à Metz. Création et entretien de jardins.",
        "Jardins Exemple, paysagiste. Devis gratuit au 06 00 00 00 03.",
    ],
)
def test_a_listing_without_address_takes_the_facebook_page_naming_its_town_or_showing_its_number(
    description: str,
) -> None:
    assert CandidateVerifier.is_facebook_page_of(_facebook_line(description), _listing_without_address(), _LANDSCAPER)


def test_a_listing_with_an_address_still_takes_a_page_saying_its_trade() -> None:
    facts = _facts(
        "JARDINS EXEMPLE", "paysagiste", city="Metz", searched_city="Metz", address="1 Rue de l'Exemple, 57000 Metz"
    )

    assert CandidateVerifier.is_facebook_page_of(
        _facebook_line("Jardins Exemple, paysagiste. Création et entretien de jardins."), facts, _LANDSCAPER
    )


@pytest.mark.parametrize(
    ("full_name", "person"),
    [
        ("Aurelie Exemple", ("Aurelie", "Exemple")),
        ("EXEMPLE Aurélie", ("Aurélie", "Exemple")),
        ("Jean-Pierre Exemple Temoin", ("Jean-Pierre", "Exemple Temoin")),
        ("Temoin Exemple", None),
        ("Aurelie", None),
    ],
)
def test_the_searched_owner_is_read_first_name_first_or_last(full_name: str, person: tuple[str, str] | None) -> None:
    assert SearchOwnerStrategy.first_and_last_name(full_name) == person


def _landscaper_context(*emails: str) -> ResolutionContext:
    """A micro-entrepreneur landscaper with no register entry, whose owner the search read on a directory."""
    return ResolutionContext(
        company_name="AURÉLIE PAYSAGES",
        city="Exempleville-sur-Charente",
        emails=list(emails),
        searched_owner=SearchedOwner("Aurelie Exemple", "allovoisins.com", _ALLOVOISINS_PAGE),
    )


def _resolve(context: ResolutionContext) -> NameResolution:
    resolver = DecisionMakerResolver([BusinessNameOwnerStrategy(), EmailOwnerStrategy(), SearchOwnerStrategy()])
    return asyncio.run(resolver.resolve(context))


def test_the_searched_owner_spelled_by_the_business_s_email_is_its_contact() -> None:
    """« exempleaureliedu17@ » holds the first and last name allovoisins.com gives: « Bonjour Aurélie »."""
    resolution = _resolve(_landscaper_context("exempleaureliedu17@gmail.com"))

    assert resolution.status == NameResolution.AUTO
    assert resolution.candidate is not None
    assert (resolution.candidate.first, resolution.candidate.last) == ("Aurélie", "Exemple")
    assert resolution.candidate.provenance == (
        "Lu par la recherche de prospects sur allovoisins.com, et l'adresse mail « exempleaureliedu17@gmail.com » "
        "porte ce nom"
    )


def test_the_searched_owner_alone_is_a_proposal() -> None:
    resolution = _resolve(_landscaper_context("aurelie.paysages17@gmail.com"))

    assert resolution.status == NameResolution.PROPOSED
    assert resolution.candidate is not None
    assert (resolution.candidate.first, resolution.candidate.last) == ("Aurélie", "Exemple")


def _prospect_found_by_the_search(db: Session, evidence: list[dict[str, str]]) -> ProspectDB:
    """The landscaper's prospect, and the candidate of the search it was created from."""
    prospect = ProspectDB(name="AURÉLIE PAYSAGES", category="paysagiste", source="search", user_id=7)
    db.add(prospect)
    db.commit()
    db.add(
        ProspectSearchCandidate(
            search_id=18,
            user_id=7,
            trade="paysagiste",
            origin=CandidateOrigin.GOOGLE_LOCAL.value,
            name="AURÉLIE PAYSAGES",
            country="FR",
            status=CandidateStatus.KEPT.value,
            phone_is_mobile=True,
            owner_name="Aurelie Exemple",
            prospect_id=prospect.id,
            identity_keys=[],
            evidence=evidence,
        )
    )
    db.commit()
    return prospect


def test_the_enrichment_reads_the_owner_the_search_read_for_the_prospect(db: Session) -> None:
    prospect = _prospect_found_by_the_search(
        db,
        [
            {"fact": "facebook", "value": "https://www.facebook.com/61500000000003", "source": "Fiche Google"},
            {"fact": "owner", "value": "Aurelie Exemple", "source": "allovoisins.com", "url": _ALLOVOISINS_PAGE},
        ],
    )

    searched_owner = EnrichmentService._searched_owner(db, prospect)

    assert searched_owner == SearchedOwner("Aurelie Exemple", "allovoisins.com", _ALLOVOISINS_PAGE)
    assert context_from_prospect(prospect, searched_owner=searched_owner).searched_owner == searched_owner


def test_an_owner_read_on_a_register_list_is_proposed_without_a_page(db: Session) -> None:
    """A register the search starts from (RGE, RBQ) gives the owner without an « owner » line of its own."""
    prospect = _prospect_found_by_the_search(db, [])

    searched_owner = EnrichmentService._searched_owner(db, prospect)
    candidates = SearchOwnerStrategy().candidates_of(
        ResolutionContext(company_name="AURÉLIE PAYSAGES", searched_owner=searched_owner)
    )

    assert searched_owner == SearchedOwner("Aurelie Exemple")
    assert [candidate.provenance for candidate in candidates] == ["Lu par la recherche de prospects"]
