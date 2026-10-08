"""
The decision maker of 23 campaign leads checked by hand (first decision-maker round, 8 Oct 2026): 6 of the
app's proposals named someone else — a namesake firm in another département, a firm that had ceased, a
customer thanked in a reply, a director who had left — and a trusted name came from another firm of the
same trade; registry entries filed as « JULES X (EXEMPLE AUTO 64) » or « E.XP' » were missed.
"""

import asyncio
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

from services.decision_maker.french_departments import FrenchDepartments
from services.decision_maker.strategies import (
    LlmAggregateStrategy,
    RegistreGouvStrategy,
    TradeName,
    WebRegistryStrategy,
)
from services.decision_maker.types import NameCandidate, ResolutionContext
from services.enrichment_service import EnrichmentService


def _company(name: str, *, postal_code: str = "46000", town: str = "CAHORS", state: str = "A") -> dict[str, Any]:
    """A registry company with one manager."""
    return {
        "nom_complet": name,
        "nom_raison_sociale": name,
        "nature_juridique": "5499",
        "siren": "123456789",
        "etat_administratif": state,
        "siege": {"code_postal": postal_code, "libelle_commune": town, "activite_principale": "81.30Z"},
        "dirigeants": [
            {"nom": "MODELE", "prenoms": "Jules", "qualite": "Gérant", "type_dirigeant": "personne physique"}
        ],
    }


def test_a_ceased_company_is_never_the_business() -> None:
    """The business's former structure, closed since, names nobody."""
    context = ResolutionContext(company_name="Exemple Jardins", city="Cahors", postal_code="46000")

    assert RegistreGouvStrategy().parse_results([_company("EXEMPLE JARDINS", state="C")], context) == []


def test_a_company_of_another_departement_is_dropped_even_without_a_postal_code() -> None:
    """The town gives the département: a namesake in Normandy is another business, not a proposal."""
    context = ResolutionContext(company_name="Exemple Jardins", city="Cahors", postal_code=None)
    namesake = _company("EXEMPLE JARDINS", postal_code="76280", town="TURRETOT")

    assert RegistreGouvStrategy().parse_results([namesake], context, department="46") == []


def test_a_company_registered_one_commune_away_is_confirmed_by_its_departement() -> None:
    """An artisan of Limoges registered at home in the next commune is the business."""
    context = ResolutionContext(company_name="Exemple Jardins", city="Limoges", postal_code=None)
    candidates = RegistreGouvStrategy().parse_results(
        [_company("EXEMPLE JARDINS", postal_code="87170", town="ISLE")], context, department="87"
    )

    assert [(candidate.first, candidate.geo_confirmed) for candidate in candidates] == [("Jules", True)]


def test_the_trade_name_in_brackets_matches_a_listing_name_written_glued() -> None:
    """« ExempleAuto64 » is the sole trader « JULES MODELE (EXEMPLE AUTO 64) »."""
    context = ResolutionContext(company_name="ExempleAuto64", city="Pau", postal_code="64110")
    company = _company("JULES MODELE (EXEMPLE AUTO 64)", postal_code="64110", town="PAU")

    assert [candidate.last for candidate in RegistreGouvStrategy().parse_results([company], context)] == ["Modele"]


@pytest.mark.parametrize(
    ("name", "searchable"),
    [("E.XP' Jardins", "EXP Jardins"), ("ExempleAuto64", "Exemple Auto 64"), ("2L Automobiles", "2L Automobiles")],
)
def test_a_name_is_searched_the_way_the_registry_files_it(name: str, searchable: str) -> None:
    """Dotted initials are joined and glued words set apart; a number glued to its letters stays as it is."""
    assert TradeName.searchable(name) == searchable


def test_the_departement_of_a_town_comes_from_the_list_of_communes(monkeypatch: pytest.MonkeyPatch) -> None:
    """A town shared by two départements gives none; postal codes give theirs, Corsica aside."""

    async def communes_named(town: str) -> list[dict[str, str]]:
        if town == "Exempleville":
            return [
                {"nom": "Exempleville", "codeDepartement": "46"},
                {"nom": "Exempleville-Haut", "codeDepartement": "12"},
            ]
        return [{"nom": "Modèle-sur-Lot", "codeDepartement": "46"}, {"nom": "Modèle-sur-Lot", "codeDepartement": "47"}]

    monkeypatch.setattr(FrenchDepartments, "_communes_named", staticmethod(communes_named))

    assert asyncio.run(FrenchDepartments.of_town("Exempleville")) == "46"
    assert asyncio.run(FrenchDepartments.of_town("Modèle-sur-Lot")) is None
    assert [FrenchDepartments.of_postal_code(code) for code in ("46000", "97411", "20000")] == ["46", "974", None]


def test_a_legal_name_found_on_the_web_must_share_a_distinctive_word() -> None:
    """« AB ÉLECTRICITÉ » shares only its trade with « ABS électricité »; « SECOMAN EXEMPLE » keeps the name."""
    page = "<p>AB ELECTRICITE à Limoges</p><p>SECOMAN EXEMPLE paysagiste</p>"
    strategy = WebRegistryStrategy(client=SimpleNamespace(is_configured=True))

    assert strategy.extract_company_names(page, "ABS électricité") == []
    assert strategy.extract_company_names(page, "Exemple Paysagiste") == ["SECOMAN EXEMPLE"]


def test_an_activity_code_does_not_demote_a_company_bearing_the_business_name() -> None:
    """« ABC Exemple & Piscine » files under building works for its pools: same name, same business."""
    prospect = SimpleNamespace(name="ABC Exemple & Piscine", city="Garons", category="paysagiste")
    own = NameCandidate(
        first="Jules",
        last="Modele",
        source="registre_gouv",
        confidence=0.9,
        primary=True,
        raw={"nom_complet": "ABC EXEMPLE & PISCINE", "activite": "43.99D"},
    )
    other = NameCandidate(
        first="Jules",
        last="Modele",
        source="registre_gouv",
        confidence=0.9,
        primary=True,
        raw={"nom_complet": "MODELE JULES", "activite": "43.99D"},
    )

    assert EnrichmentService._activity_check(prospect, own) == (None, None)
    assert EnrichmentService._activity_check(prospect, other)[0] is False


def test_a_name_the_owner_thanks_in_a_reply_is_a_customer_s() -> None:
    """« Merci beaucoup Jules pour ton commentaire » names the reviewer; « Jules Exemple, paysagiste » the head."""
    corpus = "Merci beaucoup Jules pour ton commentaire. Jules Exemple, paysagiste de formation."
    strategy = LlmAggregateStrategy()

    thanked = strategy.parse_answer("PRENOM: Jules\nNOM:\nCITATION: Merci beaucoup Jules pour ton commentaire", corpus)
    named = strategy.parse_answer(
        "PRENOM: Jules\nNOM: Exemple\nCITATION: Jules Exemple, paysagiste de formation.", corpus
    )

    assert (thanked, [candidate.last for candidate in named]) == ([], ["Exemple"])


def test_a_neighbour_found_on_the_web_is_not_the_business() -> None:
    """« EXEMPLE HOME RENOV » shares two words with « Exemple Home Services »: its head is someone else's."""
    context = ResolutionContext(company_name="Exemple Home Services", city="Pau", postal_code="64000")
    neighbour = NameCandidate(
        first="Jules",
        last="Modele",
        source="registre_gouv",
        confidence=0.95,
        primary=True,
        raw={"nom_complet": "JULES MODELE (EXEMPLE HOME RENOV)"},
    )
    itself = NameCandidate(
        first="Anne",
        last="Temoin",
        source="registre_gouv",
        confidence=0.85,
        primary=True,
        raw={"nom_complet": "EXEMPLE HOME SERVICES (EXEMPLE HOME SERVICES)"},
    )
    named_after = NameCandidate(
        first="Germain",
        last="Secoman",
        source="registre_gouv",
        confidence=0.95,
        primary=True,
        raw={"nom_complet": "SECOMAN GERMAIN"},
    )

    assert [WebRegistryStrategy.is_company_of(candidate, context) for candidate in (neighbour, itself)] == [False, True]
    assert WebRegistryStrategy.is_company_of(named_after, replace(context, company_name="Germain Paysagiste"))


def test_a_firm_sharing_only_the_region_and_generic_words_is_another_business() -> None:
    """« EXEMPLE SERVICES », a cleaning firm, is not « Exemple Services Extérieurs », a landscaper."""
    context = ResolutionContext(company_name="Exemple Services Exterieurs", city="Pau", postal_code="64000")
    cleaning_firm = NameCandidate(
        first="Jules",
        last="Modele",
        source="registre_gouv",
        confidence=0.85,
        primary=True,
        raw={"nom_complet": "EXEMPLE SERVICES", "activite": "81.21Z"},
    )
    prospect = SimpleNamespace(name="Exemple Services Exterieurs", city="Pau", category="paysagiste")

    assert WebRegistryStrategy.is_company_of(cleaning_firm, context) is False
    assert EnrichmentService._activity_check(prospect, cleaning_firm)[0] is False
