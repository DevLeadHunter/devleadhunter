"""
Round 5 of the enrichment training: the registry ties an independent tradesman to his initials, and gives a
tradesman without a public address the commune of his registered seat. The real cases' people are replaced.
"""

import asyncio
from typing import Any

import pytest
from sqlalchemy.orm import Session

from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from services.decision_maker.french_departments import FrenchDepartments
from services.decision_maker.resolver import decision_maker_resolver
from services.decision_maker.strategies import RegistreGouvStrategy
from services.decision_maker.types import NameCandidate, NameResolution, ResolutionContext
from services.enrichment_service import EnrichmentService
from services.scraper_diagnostics_service import scraper_diagnostics_service

_USER_ID = 1


def _sole_trader(first_names: str, last_name: str, *, activity: str = "43.21A") -> dict[str, Any]:
    """An electrician registered under his own name, without the trade name he works under."""
    return {
        "nom_complet": f"{first_names.split()[0]} {last_name}",
        "nature_juridique": "1000",
        "siren": "900000003",
        "etat_administratif": "A",
        "activite_principale": activity,
        "siege": {"code_postal": "54510", "libelle_commune": "TOMBLAINE", "activite_principale": activity},
        "dirigeants": [
            {"nom": f"{last_name} ({last_name})", "prenoms": first_names, "type_dirigeant": "personne physique"}
        ],
    }


@pytest.mark.parametrize(
    ("trade_name", "first_names", "last_name", "expected"),
    [
        # KR Électricité Générale (prospect n° 404): the last name's initial first.
        ("EK Électricité Générale", "KARIM", "EXEMPLE", ("Karim", "Exemple")),
        # LDBM Élec (prospect n° 408): every first name, then the last name.
        ("LMJE Élec", "LUC MARC JEAN", "EXEMPLE", ("Luc", "Exemple")),
    ],
)
def test_a_trade_name_made_of_its_head_s_initials_is_his_company(
    trade_name: str, first_names: str, last_name: str, expected: tuple[str, str]
) -> None:
    context = ResolutionContext(company_name=trade_name, city="Nancy", trade="électricien", country="FR")

    [candidate] = RegistreGouvStrategy().parse_results([_sole_trader(first_names, last_name)], context, department="54")

    assert (candidate.first, candidate.last) == expected
    assert candidate.provenance.endswith(f"enseigne aux initiales de son dirigeant ({trade_name.split()[0]})")


def test_initials_of_a_head_of_another_trade_tie_nothing() -> None:
    """A restaurant owner sharing the electrician's initials is not his company."""
    context = ResolutionContext(company_name="EK Électricité Générale", city="Nancy", trade="électricien", country="FR")

    restaurant = _sole_trader("KARIM", "EXEMPLE", activity="56.10C")

    assert RegistreGouvStrategy().parse_results([restaurant], context, department="54") == []


@pytest.fixture
def official_communes(monkeypatch: pytest.MonkeyPatch) -> None:
    """The official list of communes spells the registry's « PONT-DU-CHATEAU » with its accent."""

    async def communes_named(town: str) -> list[dict[str, Any]]:
        return [{"nom": "Pont-du-Château", "codeDepartement": "63"}] if "chateau" in town.lower() else []

    monkeypatch.setattr(FrenchDepartments, "_communes_named", staticmethod(communes_named))


def _landscaper(db: Session, *, address: str | None) -> tuple[ProspectDB, ProspectEnrichment]:
    """Jardin Authentique: found from Clermont-Ferrand, its Google listing gives no address."""
    prospect = ProspectDB(
        name="Jardin Authentique",
        city="Clermont-Ferrand",
        address=address,
        country="FR",
        category="paysagiste",
        source="search",
        confidence=3,
        user_id=_USER_ID,
    )
    db.add(prospect)
    db.commit()
    record = ProspectEnrichment(prospect_id=prospect.id, user_id=_USER_ID)
    db.add(record)
    db.commit()
    return prospect, record


def _registered_head() -> NameCandidate:
    return NameCandidate(
        first="Marc",
        last="Exemple",
        source="registre_gouv",
        confidence=0.95,
        primary=True,
        geo_confirmed=True,
        provenance="Registre officiel (SIRENE) : JARDIN AUTHENTIQUE, SIREN 900000004 — localisation confirmée",
        raw={"siren": "900000004", "siege_postal_code": "63430", "siege_commune": "PONT-DU-CHATEAU"},
    )


def _resolve_with_the_registry(monkeypatch: pytest.MonkeyPatch, db: Session, prospect: ProspectDB, record: Any) -> None:
    async def resolve(context: ResolutionContext) -> NameResolution:
        head = _registered_head()
        return NameResolution(status=NameResolution.AUTO, candidate=head, candidates=[head])

    monkeypatch.setattr(decision_maker_resolver, "resolve", resolve)
    monkeypatch.setattr(scraper_diagnostics_service, "record", lambda **_fields: None)
    asyncio.run(EnrichmentService()._resolve_contact(db, prospect, record))


def test_a_tradesman_without_address_gets_the_commune_of_his_registered_seat(
    db: Session, monkeypatch: pytest.MonkeyPatch, official_communes: None
) -> None:
    prospect, record = _landscaper(db, address=None)

    _resolve_with_the_registry(monkeypatch, db, prospect, record)

    assert (prospect.city, prospect.address) == ("Pont-du-Château", "63430 Pont-du-Château")
    assert record.contact_last_name == "Exemple"


def test_a_public_address_is_never_replaced_by_the_registered_seat(
    db: Session, monkeypatch: pytest.MonkeyPatch, official_communes: None
) -> None:
    prospect, record = _landscaper(db, address="5 Rue Exemple, 63000 Clermont-Ferrand")

    _resolve_with_the_registry(monkeypatch, db, prospect, record)

    assert (prospect.city, prospect.address) == ("Clermont-Ferrand", "5 Rue Exemple, 63000 Clermont-Ferrand")
