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


def test_the_firm_of_the_number_the_search_read_closes_the_business_wherever_it_sits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Jules Exemple, listed at Le Landeron: the number the search read is « Exemple Jules Jardinier-Paysagiste »,
    seated at Cornaux and struck off last year."""
    struck_off_on = datetime.now(UTC).date() - timedelta(days=260)
    asked_names = _register_listing(
        monkeypatch,
        SwissRegisterFirm(
            "Exemple Jules Jardinier-Paysagiste", "Cornaux", "GELOESCHT", "CHE-000.000.010", struck_off_on
        ),
    )
    facts = _facts(name="Jules Exemple", city="Le Landeron", registry_number="CHE-000.000.010")

    asyncio.run(swiss_registry.read_closing(facts))
    verdict = CandidateDecision.decide(facts, _ELECTRICIAN, _EMAIL_ONLY)

    assert asked_names == ["CHE-000.000.010"]
    assert verdict.detail == "Société radiée selon Registre du commerce (Zefix)."


def test_a_firm_of_a_merged_commune_is_found_by_its_postal_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """« Exemple Jules », Domdidier: the register files « Garage Exemple Jules » under Belmont-Broye, the commune
    Domdidier merged into, at the same postal code; it was struck off a month ago."""
    struck_off_on = datetime.now(UTC).date() - timedelta(days=30)
    _register_listing(
        monkeypatch,
        SwissRegisterFirm(
            "Garage Exemple Jules", "Belmont-Broye", "GELOESCHT", "CHE-000.000.011", struck_off_on, register_id=11
        ),
    )

    async def registered_address(firm: SwissRegisterFirm) -> tuple[str, str]:
        return "1564", "Domdidier"

    monkeypatch.setattr(swiss_registry, "address_of", registered_address)
    facts = _facts(name="Exemple Jules", city="Domdidier", address="Vy-d'Exemple 8, 1564 Domdidier")

    asyncio.run(swiss_registry.read_closing(facts))

    assert facts.is_closed is True


def test_a_family_firm_of_another_trade_is_not_the_business(monkeypatch: pytest.MonkeyPatch) -> None:
    """« Exemple Carrosserie Sàrl », struck off at Sion, is not « Exemple Auto », the family's garage."""
    struck_off_on = datetime.now(UTC).date() - timedelta(days=30)
    _register_listing(
        monkeypatch,
        SwissRegisterFirm("Exemple Carrosserie Sàrl", "Sion", "GELOESCHT", "CHE-000.000.012", struck_off_on),
    )
    facts = _facts(name="Exemple Auto", city="Sion")

    asyncio.run(swiss_registry.read_closing(facts))

    assert facts.is_closed is False


def test_the_register_is_searched_without_the_trade_word_google_adds(monkeypatch: pytest.MonkeyPatch) -> None:
    """« Garage JX services Sàrl » on Google is « JX Services Sàrl » in the register, at the same postal code."""
    firm = SwissRegisterFirm(
        name="JX Services Sàrl", seat="Grimisuat", status="EXISTIEREND", uid="CHE-000.000.013", register_id=13
    )
    asked_names = _register_listing(monkeypatch, firm)

    async def registered_addresses(firm: SwissRegisterFirm) -> list[tuple[str, str]]:
        return [("1971", "Grimisuat")]

    monkeypatch.setattr(swiss_registry, "addresses_of", registered_addresses)

    found = asyncio.run(
        swiss_registry.firm_by_words_and_address(name="Garage JX services Sàrl", town="Grimisuat", postal_code="1971")
    )

    assert found == firm
    assert "JX services" in asked_names


def test_the_cantonal_excerpt_is_asked_with_the_token_its_catalog_sets(monkeypatch: pytest.MonkeyPatch) -> None:
    """The excerpt's software answers only a request carrying the anti-forgery token its catalog set as a cookie."""
    import httpx

    from services.prospect_search import swiss_registry as registry_module

    asked: list[tuple[str, str | None]] = []

    def answer(request: httpx.Request) -> httpx.Response:
        asked.append((request.method, request.headers.get("x-xsrf-token")))
        if request.url.path.endswith("/api/public/catalog/configuration"):
            return httpx.Response(200, json={}, headers={"Set-Cookie": "XSRF-TOKEN=jeton; Path=/pub/1"})
        if request.url.path.endswith("/api/public/hrcexcerpts/"):
            if request.headers.get("x-xsrf-token") != "jeton":
                return httpx.Response(403)
            person = {"codeEtat": "A", "pers": "Exemple Jules, de Bex, à Bex", "fonction": "titulaire "}
            return httpx.Response(200, json=[{"adms": [person]}])
        return httpx.Response(200, text="<html></html>")

    real_client = httpx.AsyncClient

    def client_on_fake_web(**options: object) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(answer), **options)  # type: ignore[arg-type]

    async def firm_page(firm: SwissRegisterFirm) -> dict[str, object]:
        return {"cantonalExcerptWeb": "https://registre.exemple.ch/pub/1/extract?lang=FR&companyOfsUid=CHE-000.000.014"}

    monkeypatch.setattr(registry_module.httpx, "AsyncClient", client_on_fake_web)
    monkeypatch.setattr(swiss_registry, "_detail", firm_page)
    firm = SwissRegisterFirm("Exemple Jules", "Bex", "EXISTIEREND", "CHE-000.000.014", register_id=14)

    people = asyncio.run(swiss_registry.excerpt_people(firm))

    assert [(person.first_name, person.last_name) for person in people] == [("Jules", "Exemple")]
    assert asked == [("GET", None), ("GET", None), ("POST", "jeton")]
