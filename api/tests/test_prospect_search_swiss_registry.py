"""The federal company register closes a Swiss company « en liquidation » or struck off."""

import asyncio
from datetime import UTC, datetime, timedelta

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

    async def firms_named(name: str, *, max_entries: int = 10) -> list[SwissRegisterFirm]:
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


@pytest.mark.parametrize(("struck_off_days_ago", "is_closed"), [(30, True), (12 * 365, False)])
def test_only_a_recent_striking_off_closes_a_sole_trader_listed_with_a_civility(
    monkeypatch: pytest.MonkeyPatch, struck_off_days_ago: int, is_closed: bool
) -> None:
    struck_off_on = datetime.now(UTC).date() - timedelta(days=struck_off_days_ago)
    asked_names = _register_listing(
        monkeypatch, SwissRegisterFirm("Paul Rochat", "Yvonand", "GELOESCHT", "CHE-000.000.005", struck_off_on)
    )
    facts = _facts(name="Mr. Paul Rochat", city="Yvonand")

    asyncio.run(swiss_registry.read_closing(facts))

    assert asked_names == ["Paul Rochat"]
    assert facts.is_closed is is_closed


def test_a_firm_working_at_another_address_than_its_seat_is_found_there(monkeypatch: pytest.MonkeyPatch) -> None:
    """« EXM Mécanique Modèle » sits in Vionnaz, its workshop in Bex: the gazette's « Autre adresse » ties it."""
    firm = SwissRegisterFirm(
        name="EXM Mécanique Modèle", seat="Vionnaz", status="EXISTIEREND", uid="CHE-111.222.333", register_id=4
    )

    async def page(firm: SwissRegisterFirm) -> dict[str, object]:
        return {
            "address": {"swissZipCode": "1895", "town": "Vionnaz"},
            "shabPub": [
                {
                    "shabDate": "2026-01-12",
                    "message": "EXM Mécanique Modèle, à Vionnaz, Route Exemple 35, 1895 Vionnaz, entreprise "
                    "individuelle (Nouvelle inscription). Autre adresse: Route Modèle 28, 1880 Bex. But: mécanique.",
                }
            ],
        }

    _register_listing(monkeypatch, firm)
    monkeypatch.setattr(swiss_registry, "_detail", page)

    found = asyncio.run(swiss_registry.firm_by_words_and_address(name="EXM MÉCANIQUE", town="Bex", postal_code="1880"))

    assert found == firm


def test_initials_glued_to_the_next_word_are_the_same_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """The register files « Garage EX Auto » as « Garage EXauto - Modèle Jules »: the glued spelling is searched."""
    firm = SwissRegisterFirm(
        name="Garage EXauto - Modèle Jules", seat="Chamoson", status="EXISTIEREND", uid="CHE-444.555.666", register_id=5
    )
    asked_names = _register_listing(monkeypatch, firm)

    async def addresses_in_town(firm: SwissRegisterFirm) -> list[tuple[str, str]]:
        return [("1955", "Chamoson")]

    monkeypatch.setattr(swiss_registry, "addresses_of", addresses_in_town)

    found = asyncio.run(
        swiss_registry.firm_by_words_and_address(
            name="Garage EX Auto", town="Saint-Pierre-de-Clages", postal_code="1955"
        )
    )

    assert found == firm
    assert "EXAuto" in asked_names
