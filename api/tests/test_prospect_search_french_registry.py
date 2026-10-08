"""The French company registry closes a French business whose company ceased lately at its place."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from enums.prospect_search import CandidateOrigin
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.french_registry import FrenchRegistry, french_registry


def _facts(**overrides: object) -> CandidateFacts:
    """A garage of Cahors a search found."""
    values: dict[str, object] = {
        "name": "Garage Exemple Auto 46",
        "trade_key": "garage",
        "country": "FR",
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "city": "Cahors",
        "address": "836 Rue Exemple, 46000 Cahors",
    }
    values.update(overrides)
    return CandidateFacts(**values)  # type: ignore[arg-type]


def _company(state: str, *, closed_days_ago: int | None = None, postal_code: str = "46000") -> dict[str, object]:
    """A registry company of the garage's name."""
    closed_on = (datetime.now(UTC).date() - timedelta(days=closed_days_ago)).isoformat() if closed_days_ago else None
    return {
        "nom_complet": "JULES MODELE (EXEMPLE AUTO 46)",
        "etat_administratif": state,
        "date_fermeture": closed_on,
        "nature_juridique": "1000",
        "dirigeants": [{"nom": "MODELE", "prenoms": "JULES PAUL"}],
        "siege": {"code_postal": postal_code, "libelle_commune": "CAHORS", "liste_enseignes": ["EXEMPLE AUTO 46"]},
    }


def _tenant(last_name: str, first_name: str) -> dict[str, object]:
    """A company of the trade open at the garage's address, run by the given person."""
    return {
        "nom_complet": "TEMOIN AUTOMOBILES",
        "etat_administratif": "A",
        "dirigeants": [{"nom": last_name, "prenoms": first_name, "qualite": "Président de SAS"}],
        "matching_etablissements": [
            {"adresse": "836 RUE EXEMPLE 46000 CAHORS", "etat_administratif": "A", "activite_principale": "45.20A"}
        ],
    }


def _registry(monkeypatch: pytest.MonkeyPatch, *answers: list[dict[str, object]]) -> None:
    """Script the registry's answers, one per query."""
    remaining = list(answers)

    async def companies(query: str, **_options: object) -> list[dict[str, object]]:
        return remaining.pop(0) if remaining else []

    monkeypatch.setattr(FrenchRegistry, "_companies", staticmethod(companies))


def test_a_company_ceased_lately_at_the_business_place_closes_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """The garage's sole trader ceased ten months ago at Cahors: the garage is closed, nobody took it over."""
    _registry(monkeypatch, [_company("C", closed_days_ago=300)], [])
    facts = _facts()

    asyncio.run(french_registry.read_closing(facts))

    assert facts.is_closed
    assert facts.evidence[-1]["fact"] == "closed"


def test_an_open_company_an_old_closing_or_the_same_head_s_new_company_leaves_the_business_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An open company of the name, a closing six years old, or the same head's new company at the address: open."""
    open_too = _facts()
    _registry(monkeypatch, [_company("C", closed_days_ago=300), _company("A")])
    asyncio.run(french_registry.read_closing(open_too))

    old_closing = _facts()
    _registry(monkeypatch, [_company("C", closed_days_ago=6 * 365)])
    asyncio.run(french_registry.read_closing(old_closing))

    carried_on = _facts()
    _registry(monkeypatch, [_company("C", closed_days_ago=300)], [_tenant("MODELE", "JULES")])
    asyncio.run(french_registry.read_closing(carried_on))

    elsewhere = _facts()
    _registry(monkeypatch, [_company("C", closed_days_ago=300, postal_code="46100")])
    asyncio.run(french_registry.read_closing(elsewhere))

    assert [facts.is_closed for facts in (open_too, old_closing, carried_on, elsewhere)] == [False] * 4


def test_a_newcomer_at_the_address_does_not_carry_the_closed_business_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """Another person opened a car business at the address after the closing: the listing's business is closed."""
    _registry(monkeypatch, [_company("C", closed_days_ago=200)], [_tenant("TEMOIN", "ANNE")])
    facts = _facts()

    asyncio.run(french_registry.read_closing(facts))

    assert facts.is_closed


def test_the_same_head_s_company_of_the_name_elsewhere_in_the_departement_goes_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sole trader of Cahors closed when he made a company of the same name, seated at his home nearby: open."""
    sole_trader = _company("C", closed_days_ago=200)
    sole_trader["dirigeants"] = [{"nom": "MODELE (MODELE)", "prenoms": "JULES PAUL"}]
    company_nearby = _company("A", postal_code="46090")
    company_nearby["dirigeants"] = [{"nom": "MODELE", "prenoms": "JULES", "qualite": "Président de SAS"}]
    _registry(monkeypatch, [sole_trader, company_nearby])
    facts = _facts()

    asyncio.run(french_registry.read_closing(facts))

    assert not facts.is_closed
