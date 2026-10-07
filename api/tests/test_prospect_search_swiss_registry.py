"""The federal company register closes a Swiss company « en liquidation » or struck off."""

import asyncio

import pytest

from enums.prospect_search import CandidateOrigin, CandidateRejectReason, EmailProofLevel, ProspectSearchChannel
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.swiss_registry import SwissRegisterFirm, swiss_registry
from services.prospect_search.trade_catalog import TradeCatalog

_ELECTRICIAN = TradeCatalog.resolve("électricien")
_EMAIL_ONLY = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=None)


def _facts(**overrides: object) -> CandidateFacts:
    values: dict[str, object] = {
        "name": "Rochat & Fils Sàrl",
        "trade_key": "electricien",
        "country": "CH",
        "origin": CandidateOrigin.GOOGLE_LOCAL.value,
        "city": "Genève",
        "email": "rochat-fils@bluewin.ch",
        "email_proof_level": EmailProofLevel.DIRECTORY.value,
        "is_verified": True,
    }
    values.update(overrides)
    return CandidateFacts(**values)  # type: ignore[arg-type]


def _register_listing(monkeypatch: pytest.MonkeyPatch, *firms: SwissRegisterFirm) -> list[str]:
    asked_names: list[str] = []

    async def firms_named(name: str) -> list[SwissRegisterFirm]:
        asked_names.append(name)
        return list(firms)

    monkeypatch.setattr(swiss_registry, "firms_named", firms_named)
    return asked_names


def test_a_company_in_liquidation_at_its_seat_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    asked_names = _register_listing(
        monkeypatch,
        SwissRegisterFirm("Rochat & Fils Sàrl, en liquidation", "Genève", "IN_AUFLOESUNG", "CHE-000.000.001"),
    )
    facts = _facts()

    asyncio.run(swiss_registry.read_closing(facts))
    verdict = CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY)

    assert asked_names == ["Rochat & Fils"]
    assert verdict.reject_reason is CandidateRejectReason.CLOSED
    assert verdict.detail == "Société en liquidation selon Registre du commerce (Zefix)."


def test_an_active_company_of_the_same_name_and_seat_clears_the_business(monkeypatch: pytest.MonkeyPatch) -> None:
    _register_listing(
        monkeypatch,
        SwissRegisterFirm("Rochat & Fils Sàrl, en liquidation", "Genève", "IN_AUFLOESUNG", "CHE-000.000.001"),
        SwissRegisterFirm("Rochat & Fils SA", "Genève", "EXISTIEREND", "CHE-000.000.002"),
    )
    facts = _facts()

    asyncio.run(swiss_registry.read_closing(facts))

    assert facts.is_closed is False
    assert facts.registry_number == "CHE-000.000.002"


@pytest.mark.parametrize(
    ("firm", "city", "country"),
    [
        (
            SwissRegisterFirm("Rochat & Fils Sàrl, en liquidation", "Lausanne", "IN_AUFLOESUNG", "CHE-000.000.001"),
            "Genève",
            "CH",
        ),
        (SwissRegisterFirm("Rochat & Fils Électricité Sàrl", "Genève", "GELOESCHT", "CHE-000.000.003"), "Genève", "CH"),
        (SwissRegisterFirm("Rochat & Fils Sàrl", "Genève", "GELOESCHT", "CHE-000.000.004"), "Genève", "FR"),
    ],
)
def test_another_firm_or_a_business_outside_switzerland_is_left_open(
    monkeypatch: pytest.MonkeyPatch, firm: SwissRegisterFirm, city: str, country: str
) -> None:
    _register_listing(monkeypatch, firm)
    facts = _facts(city=city, country=country)

    asyncio.run(swiss_registry.read_closing(facts))

    assert facts.is_closed is False
