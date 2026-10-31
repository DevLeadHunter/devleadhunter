"""A search of Martinique, and a search that skips the public registries.

A Martinique search stays a French search (``country = "FR"``, every French rule) whose ``region`` is the
department: it walks the communes of the island, biggest first, names « Martinique » in every query, keeps
the postal code and the +596 numbers of its listings (so its prospects read the Martinique clock), and
discards a business placed elsewhere. A search with ``use_registries`` off never reads the RGE nor the RBQ
files: it starts from Google Maps and Facebook only, as the electricians of wave 5 must.
"""

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import services.activity_log_service as activity_log_module
import services.prospect_search.facebook_contact as facebook_contact_module
import services.prospect_search.runner as runner_module
import services.prospect_search.service as service_module
from enums.prospect_search import (
    CandidateRejectReason,
    CandidateStatus,
    ProspectSearchChannel,
    ProspectSearchValidationMode,
)
from models.prospect_db import ProspectDB
from models.prospect_search import ProspectSearch
from models.prospect_search_candidate import ProspectSearchCandidate
from prospect_search_cli import ProspectSearchCli
from prospect_search_cli import _parse_args as parse_command_line
from schemas.prospect_search import ProspectSearchCreate, ProspectSearchSummary
from scrappers.google_local_results import GoogleLocalResultsParser
from services.enrichment_service import enrichment_service
from services.prospect_search.candidate_decision import CandidateDecision, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.contact_finder import EmailDomainCheck
from services.prospect_search.registry_sources import RegistryCompany, rbq_registry, rge_registry
from services.prospect_search.runner import ProspectSearchRunner
from services.prospect_search.search_judge import search_judge
from services.prospect_search.search_zones import SearchZones
from services.prospect_search.service import ProspectSearchError, prospect_search_service
from services.prospect_search.trade_catalog import TradeCatalog
from services.prospect_timezone import prospect_timezone
from services.website_liveness_service import website_liveness_service

USER_ID = 5


def _card(name: str, lines: list[str], *, directions: str, feature_id: str) -> str:
    """One business card in the shape Google serves it, its directions link holding the address and the identifier."""
    body = "".join(f"<div>{line}</div>" for line in lines)
    link = (
        f'<a href="/maps/dir//{directions}/data=!4m6!4m5!1m1!4e2!1m2!1m1!1s0x8c6a:0x{feature_id}?sa=X">Itinéraire</a>'
    )
    return (
        '<div class="VkpGBb"><div><div class="rllt__details">'
        f'<div role="heading"><span>{name}</span></div>{body}</div></div>{link}</div>'
    )


_MARTINIQUE_PAGE = (
    "<html><body>"
    + _card(
        "Garage Eden Meca",
        ["4,5 (19) · Garage automobile", "Plus de 5 ans en activité · Le Lamentin, Martinique", "+596 696 80 10 23"],
        directions="Garage+Eden+Meca,+Les+Hauts+De+Californie,+Le+Lamentin+97232,+Martinique",
        feature_id="1a01",
    )
    + _card(
        "Garage Universel",
        ["4,7 (39) · Garage automobile", "Plus de 7 ans en activité · Le Lamentin, Martinique", "+596 596 50 03 43"],
        directions="JX87%2B8JF+Garage+Universel,+Le+Lamentin,+Martinique",
        feature_id="1a02",
    )
    + _card(
        "Garage du Centre",
        ["4,1 (8) · Garage automobile", "Blois", "02 54 00 00 00"],
        directions="Garage+du+Centre,+12+Rue+Nationale,+41000+Blois",
        feature_id="1a03",
    )
    + "</body></html>"
)


class _MartiniqueSearchClient:
    """Stands in for Bright Data: the same Martinique local page for every local query, empty web pages."""

    is_configured = True

    def __init__(self) -> None:
        self.request_count = 0
        self.local_queries: list[str] = []
        self.web_queries: list[str] = []

    def reload_credentials(self) -> None:
        return None

    async def google_local_html(self, query: str, *, country: str = "FR", start: int = 0) -> str | None:
        self.request_count += 1
        self.local_queries.append(query)
        return _MARTINIQUE_PAGE if start == 0 else None

    async def google_parsed(
        self, query: str, *, country: str = "FR", start: int = 0, local: bool = False
    ) -> dict[str, Any] | None:
        self.request_count += 1
        self.web_queries.append(query)
        return {"organic": []}


_CLIENTS: list[_MartiniqueSearchClient] = []
_TOWNS_ASKED_TO_REGISTRIES: list[str] = []


def _recording_client() -> _MartiniqueSearchClient:
    client = _MartiniqueSearchClient()
    _CLIENTS.append(client)
    return client


@pytest.fixture
def canned_web(monkeypatch: pytest.MonkeyPatch, engine: Engine) -> None:
    """Every session on the test database, the web canned, the registries recording the towns they are asked about."""
    session_factory = sessionmaker(bind=engine)
    for module in (runner_module, facebook_contact_module, service_module, activity_log_module):
        monkeypatch.setattr(module, "SessionLocal", session_factory)
    _CLIENTS.clear()
    _TOWNS_ASKED_TO_REGISTRIES.clear()
    monkeypatch.setattr(runner_module, "BrightDataClient", _recording_client)
    monkeypatch.setattr(enrichment_service, "schedule_contact_resolution", lambda prospect_ids: None)

    async def no_judge(**_: object) -> None:
        return None

    async def recorded_registry(*, trade: object, city: str, limit: int) -> list[RegistryCompany]:
        _TOWNS_ASKED_TO_REGISTRIES.append(city)
        return []

    async def no_website(website: str | None) -> None:
        return None

    async def receives_mail(self: EmailDomainCheck, email: str) -> bool:
        return True

    async def no_front_page(domain: str) -> None:
        return None

    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(no_front_page))
    monkeypatch.setattr(search_judge, "judge", no_judge)
    monkeypatch.setattr(rge_registry, "companies_near", recorded_registry)
    monkeypatch.setattr(rbq_registry, "companies_in", recorded_registry)
    monkeypatch.setattr(website_liveness_service, "check_website_status", no_website)
    monkeypatch.setattr(EmailDomainCheck, "receives_mail", receives_mail)


def _create(db: Session, **objective: Any) -> ProspectSearch:
    payload = ProspectSearchCreate(
        trades=["garage"], count_per_trade=1, validation_mode=ProspectSearchValidationMode.AUTOMATIC, **objective
    )
    return prospect_search_service.create(db, USER_ID, payload)


def test_a_martinique_search_walks_the_island_s_communes_biggest_first() -> None:
    towns = SearchZones.plan(country="FR", region="MQ", asked_cities=[], already_scanned=set(), seed=7)
    rescanned = SearchZones.plan(country="FR", region="MQ", asked_cities=[], already_scanned={"fort-de-france"}, seed=7)

    assert towns[:4] == ["Fort-de-France", "Le Lamentin", "Le Robert", "Schœlcher"]
    assert "Blois" not in towns and len(towns) == 34
    assert rescanned[0] == "Le Lamentin" and rescanned[-1] == "Fort-de-France"


def test_the_search_is_open_in_martinique_only_and_remembers_its_objective(db: Session) -> None:
    search = _create(db, country="FR", region="mq", use_registries=False)

    assert (search.country, search.region, search.use_registries) == ("FR", "MQ", False)
    summary = ProspectSearchSummary.model_validate(search)
    assert (summary.region, summary.use_registries) == ("MQ", False)
    with pytest.raises(ProspectSearchError):
        _create(db, country="FR", region="GP")
    with pytest.raises(ProspectSearchError):
        _create(db, country="CH", region="MQ")
    assert _create(db, country="FR").region is None and _create(db, country="FR").use_registries is True


def test_a_martinique_search_names_the_island_and_keeps_its_postal_code_numbers_and_clock(
    canned_web: None, db: Session
) -> None:
    search = _create(db, country="FR", region="MQ", cities=["Le Lamentin"])

    asyncio.run(ProspectSearchRunner(search.id).run())
    db.expire_all()

    client = _CLIENTS[0]
    assert client.local_queries[0] == "garage automobile Le Lamentin Martinique"
    assert 'site:facebook.com "garage automobile" "Le Lamentin" Martinique' in client.web_queries
    candidates = {
        row.name: row
        for row in db.execute(
            select(ProspectSearchCandidate).where(ProspectSearchCandidate.search_id == search.id)
        ).scalars()
    }
    eden = candidates["Garage Eden Meca"]
    assert eden.address == "Les Hauts De Californie, Le Lamentin 97232, Martinique"
    assert (eden.city, eden.country, eden.phone_is_mobile) == ("Le Lamentin", "FR", True)
    assert eden.status == CandidateStatus.SET_ASIDE.value
    assert candidates["Garage Universel"].address == "Le Lamentin, Martinique"
    mainland = candidates["Garage du Centre"]
    assert (mainland.status, mainland.reject_reason) == (
        CandidateStatus.REJECTED.value,
        CandidateRejectReason.OUT_OF_COUNTRY.value,
    )
    assert "Martinique" in (mainland.reject_detail or "")

    prospect = db.get(ProspectDB, eden.prospect_id)
    assert prospect is not None and prospect.country == "FR"
    assert prospect_timezone(prospect) == "America/Martinique"


def test_a_search_without_registries_never_reads_them(canned_web: None, db: Session) -> None:
    with_registries = _create(db, country="FR", cities=["Limoges"])
    without_registries = _create(db, country="FR", cities=["Limoges"], use_registries=False)

    asyncio.run(ProspectSearchRunner(with_registries.id).run())
    asyncio.run(ProspectSearchRunner(without_registries.id).run())

    assert _TOWNS_ASKED_TO_REGISTRIES == ["Limoges"]


def _martinique_lead(name: str, *, address: str | None = None, phone: str | None = None) -> CandidateFacts:
    """A lead of a Martinique search, before its verification."""
    return CandidateFacts(
        name=name, trade_key="garage", country="FR", origin="google_local", region="MQ", address=address, phone=phone
    )


def test_a_business_placed_outside_the_searched_department_is_discarded() -> None:
    criteria = SearchCriteria(channel=ProspectSearchChannel.EMAIL, only_without_website=True, minimum_rating=None)
    in_guadeloupe = _martinique_lead("Garage Pointe", address="Rue Frébault, 97110 Pointe-à-Pitre")
    with_a_mobile_only = _martinique_lead("Garage Mobile", phone="06 12 34 56 78")
    with_a_mainland_landline = _martinique_lead("Garage Fixe", phone="02 54 00 00 00")

    assert in_guadeloupe.is_outside_region is True
    assert with_a_mobile_only.is_outside_region is False
    assert with_a_mainland_landline.is_outside_region is True
    verdict = CandidateDecision.decide(in_guadeloupe, TradeCatalog.resolve("garage"), criteria)
    assert verdict.reject_reason == CandidateRejectReason.OUT_OF_COUNTRY


def test_a_martinique_card_gives_its_town_without_the_island_s_name() -> None:
    listing = GoogleLocalResultsParser.parse_html(_MARTINIQUE_PAGE, country="FR")[1]

    assert listing.locality == "Le Lamentin"
    assert listing.phone == "+596 596 50 03 43"


def test_the_command_line_passes_the_region_and_the_registries_switch() -> None:
    class _RecordingApi:
        def __init__(self) -> None:
            self.created_searches: list[dict[str, Any]] = []

        async def post(self, path: str, json: dict[str, Any]) -> SimpleNamespace:
            self.created_searches.append(json)
            return SimpleNamespace(status_code=201, json=lambda: {"id": 9}, raise_for_status=lambda: None)

    api = _RecordingApi()
    cli = ProspectSearchCli(api, reads_facebook_pages=False)  # type: ignore[arg-type]

    asyncio.run(cli.create(parse_command_line(["--trades", "garage", "--region", "mq", "--no-registries"])))
    asyncio.run(cli.create(parse_command_line(["--trades", "garage"])))

    assert [(search["region"], search["use_registries"]) for search in api.created_searches] == [
        ("MQ", False),
        (None, True),
    ]
