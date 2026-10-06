"""A whole prospect search, with the web and the language model replaced by canned pages.

What is checked is the chain an operator would do by hand: read the local results,
discard the business with a website, keep the one whose email a directory gives,
remember the discarded one for the next search, and hand the Facebook pages to a
browser.
"""

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

import prospect_search_cli as prospect_search_cli_module
import services.activity_log_service as activity_log_module
import services.prospect_search.facebook_contact as facebook_contact_module
import services.prospect_search.runner as runner_module
import services.prospect_search.service as service_module
from api.v1.routes.prospect_searches import decide_candidates as decide_candidates_route
from api.v1.routes.prospect_searches import get_prospect_search_activity as activity_route
from api.v1.routes.prospect_searches import list_pending_candidates as pending_candidates_route
from api.v1.routes.prospect_searches import record_facebook_contact as record_facebook_contact_route
from api.v1.routes.prospect_searches import router as prospect_searches_router
from core.config import settings
from core.database import Base, get_db
from enums.prospect_search import (
    CandidateOrigin,
    CandidateRejectReason,
    CandidateStatus,
    ProspectSearchChannel,
    ProspectSearchStatus,
    ProspectSearchValidationMode,
)
from enums.website_status import WebsiteStatus
from models.prospect_db import ProspectDB
from models.prospect_search import ProspectSearch
from models.prospect_search_candidate import ProspectSearchCandidate
from prospect_search_cli import ProspectSearchCli
from prospect_search_cli import _parse_args as parse_command_line
from schemas.prospect_search import (
    CandidateDecisions,
    FacebookContactPayload,
    ProspectSearchCandidateResponse,
    ProspectSearchCreate,
    ProspectSearchDetail,
    RefusedCandidateDecision,
)
from scrappers.facebook_enrichment_scraper import facebook_enrichment_scraper
from services.auth_service import require_auth
from services.enrichment_service import enrichment_service
from services.prospect_search.candidate_identity import CandidateIdentity, KnownBusinessIndex
from services.prospect_search.candidate_store import CandidateStore
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.contact_finder import EmailDomainCheck
from services.prospect_search.facebook_contact import FacebookContactRead, facebook_contact_recorder
from services.prospect_search.registry_sources import rge_registry
from services.prospect_search.runner import ProspectSearchRunner
from services.prospect_search.search_judge import search_judge
from services.prospect_search.service import ProspectSearchError, ProspectSearchService, prospect_search_service
from services.prospect_service import prospect_service
from services.website_liveness_service import website_liveness_service

USER_ID = 3
_AUTOMATIC = ProspectSearchValidationMode.AUTOMATIC


def _card(name: str, lines: list[str], *, has_website: bool) -> str:
    body = "".join(f"<div>{line}</div>" for line in lines)
    website = '<a href="/goto?url=X">Site Web</a>' if has_website else ""
    return (
        '<div class="VkpGBb"><div><div class="rllt__details">'
        f'<div role="heading"><span>{name}</span></div>{body}</div></div>{website}</div>'
    )


_LOCAL_PAGE = (
    "<html><body>"
    + "".join(
        [
            _card("Filvert Sarl", ["5,0 (17) · Paysagiste", "Sion", "079 473 19 61"], has_website=True),
            _card("Tendance Nature", ["5,0 (2) · Paysagiste", "Sion", "078 757 57 42"], has_website=False),
            _card("Graine de Vie", ["5,0 (5) · Paysagiste", "Sion", "076 680 31 47"], has_website=False),
            _card("Jardin Fermé", ["4,0 (3) · Paysagiste", "Sion", "Définitivement fermé"], has_website=False),
            _card(
                "Jardishop", ["5,0 (11) · Magasin d'articles pour l'aménagement paysager", "Sion"], has_website=False
            ),
        ]
    )
    + "</body></html>"
)

_PARSED_PAGES: dict[str, dict[str, Any]] = {
    '"Filvert Sarl" Sion': {
        "knowledge": {"name": "Filvert Sarl", "phone": "079 473 19 61", "site": "http://www.filvertsarl.ch/"},
        "organic": [],
    },
    '"Tendance Nature" Sion': {
        "knowledge": {"name": "Tendance Nature", "phone": "078 757 57 42", "rating": 5, "reviews_cnt": 2},
        "organic": [
            {
                "link": "https://www.local.ch/fr/d/sion/1950/paysagiste/tendance-nature",
                "title": "Tendance Nature – Paysagiste à Sion",
                "description": "Tendance Nature, Rte de la Courtaz 70. Emailtendance.nature@bluewin.ch",
            }
        ],
    },
    '"Graine de Vie" Sion': {
        "organic": [
            {
                "link": "https://www.facebook.com/grainedevie/",
                "title": "Graine de Vie | Sion",
                "description": "Paysagiste à Sion.",
            }
        ]
    },
}


class _CannedSearchClient:
    """Stands in for Bright Data: one local page, then canned verification pages."""

    is_configured = True

    def __init__(self) -> None:
        self.request_count = 0
        self.queries: list[str] = []

    def reload_credentials(self) -> None:
        return None

    async def google_local_html(self, query: str, *, country: str = "FR", start: int = 0) -> str | None:
        self.request_count += 1
        return _LOCAL_PAGE if start == 0 and query.startswith("paysagiste") else None

    async def google_parsed(
        self, query: str, *, country: str = "FR", start: int = 0, local: bool = False
    ) -> dict[str, Any] | None:
        self.request_count += 1
        self.queries.append(query)
        return _PARSED_PAGES.get(query, {"organic": []})


# Front pages the domains of the canned emails serve.
_FRONT_PAGES: dict[str, tuple[str, str]] = {
    "graine-de-vie.ch": ("https://graine-de-vie.ch/", "<title>Graine de Vie, paysagiste à Sion</title>"),
}


@pytest.fixture
def canned_world(monkeypatch: pytest.MonkeyPatch, engine: Engine) -> None:
    """Point every session at the test database and replace the network with canned answers."""
    session_factory = sessionmaker(bind=engine)
    for module in (runner_module, facebook_contact_module, service_module, activity_log_module):
        monkeypatch.setattr(module, "SessionLocal", session_factory)
    monkeypatch.setattr(runner_module, "BrightDataClient", _CannedSearchClient)
    monkeypatch.setattr(enrichment_service, "schedule_contact_resolution", lambda prospect_ids: None)

    async def no_judge(**_: object) -> None:
        return None

    async def no_registry(**_: object) -> list[object]:
        return []

    async def live_website(website: str | None) -> WebsiteStatus | None:
        return WebsiteStatus.LIVE if website else None

    async def receives_mail(self: EmailDomainCheck, email: str) -> bool:
        return True

    async def front_page_of(domain: str) -> tuple[str, str] | None:
        return _FRONT_PAGES.get(domain)

    monkeypatch.setattr(CandidateVerifier, "_front_page_of", staticmethod(front_page_of))
    monkeypatch.setattr(search_judge, "judge", no_judge)
    monkeypatch.setattr(rge_registry, "companies_near", no_registry)
    monkeypatch.setattr(website_liveness_service, "check_website_status", live_website)
    monkeypatch.setattr(EmailDomainCheck, "receives_mail", receives_mail)


@pytest.fixture
def snapshot_engine(tmp_path: Path) -> Iterator[Engine]:
    """
    A database where a transaction reads the data as it was at its first read, like production's REPEATABLE READ.

    The in-memory database shares one connection between sessions, so a session there always reads
    the latest data. Here each session has its own connection to a database file in write-ahead log
    mode, and the transactions are begun by SQLAlchemy rather than left to the driver, which begins
    none for a read.
    """
    file_engine = create_engine(f"sqlite:///{tmp_path / 'snapshots.db'}")

    @event.listens_for(file_engine, "connect")
    def leave_the_transactions_to_sqlalchemy(dbapi_connection: Any, _: Any) -> None:
        dbapi_connection.isolation_level = None
        dbapi_connection.execute("PRAGMA journal_mode=WAL")

    @event.listens_for(file_engine, "begin")
    def begin_the_transaction(connection: Connection) -> None:
        connection.exec_driver_sql("BEGIN")

    Base.metadata.create_all(file_engine)
    yield file_engine
    file_engine.dispose()


def _create_search(
    db: Session,
    *,
    count: int = 1,
    cities: tuple[str, ...] = ("Sion",),
    validation_mode: ProspectSearchValidationMode = ProspectSearchValidationMode.MANUAL,
) -> int:
    search = prospect_search_service.create(
        db,
        USER_ID,
        ProspectSearchCreate(
            trades=["Paysagiste"],
            country="CH",
            cities=list(cities),
            count_per_trade=count,
            channel=ProspectSearchChannel.EMAIL,
            validation_mode=validation_mode,
        ),
    )
    return search.id


def _store_candidate(
    db: Session,
    search_id: int,
    name: str,
    status: CandidateStatus,
    *,
    user_id: int = USER_ID,
    email: str | None = None,
    phone: str | None = None,
    detail: str | None = None,
    reject_reason: CandidateRejectReason | None = None,
    prospect_id: int | None = None,
    identity_keys: list[str] | None = None,
) -> ProspectSearchCandidate:
    """A candidate as a search would have left it, without running the search."""
    candidate = ProspectSearchCandidate(
        search_id=search_id,
        user_id=user_id,
        trade="paysagiste",
        origin=CandidateOrigin.GOOGLE_LOCAL.value,
        name=name,
        country="CH",
        city="Sion",
        email=email,
        email_proof_level="a" if email else None,
        phone=phone,
        phone_is_mobile=phone is not None,
        status=status.value,
        reject_reason=reject_reason.value if reject_reason else None,
        reject_detail=detail,
        prospect_id=prospect_id,
        identity_keys=identity_keys or [],
        evidence=[],
    )
    db.add(candidate)
    db.commit()
    return candidate


def _signed_in_user(user_id: int = USER_ID) -> Any:
    """The user the routes receive from the auth guard."""
    return SimpleNamespace(id=user_id)


def _client(db: Session, user_id: int = USER_ID) -> TestClient:
    """The prospect search routes, called by a signed-in user on the test database."""
    application = FastAPI()
    application.include_router(prospect_searches_router)
    application.dependency_overrides[require_auth] = lambda: _signed_in_user(user_id)
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


async def _wait_for_started_runs() -> None:
    """Let the runs the service started in the background finish before the loop closes."""
    await asyncio.gather(*list(prospect_search_service._tasks.values()))


def _candidates(db: Session, search_id: int) -> dict[str, ProspectSearchCandidate]:
    rows = db.execute(select(ProspectSearchCandidate).where(ProspectSearchCandidate.search_id == search_id)).scalars()
    return {row.name: row for row in rows}


def test_an_automatic_search_keeps_the_proven_contact_as_a_prospect_and_discards_with_reasons(
    canned_world: None, db: Session
) -> None:
    search_id = _create_search(db, count=2, validation_mode=_AUTOMATIC)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    candidates = _candidates(db, search_id)

    kept = candidates["Tendance Nature"]
    assert kept.status == CandidateStatus.KEPT.value
    assert kept.email == "tendance.nature@bluewin.ch"
    assert kept.email_proof_level == "b"
    assert kept.phone_is_mobile is True
    assert any(line["fact"] == "email" and "local.ch" in line["url"] for line in kept.evidence)

    assert candidates["Filvert Sarl"].reject_reason == CandidateRejectReason.HAS_WEBSITE.value
    assert candidates["Jardin Fermé"].reject_reason == CandidateRejectReason.CLOSED.value
    assert candidates["Jardishop"].reject_reason == CandidateRejectReason.WRONG_TRADE.value
    assert candidates["Graine de Vie"].status == CandidateStatus.NEEDS_BROWSER.value

    prospect = db.get(ProspectDB, kept.prospect_id)
    assert prospect is not None
    assert (prospect.source, prospect.country, prospect.email) == ("search", "CH", "tendance.nature@bluewin.ch")
    assert prospect.category == "paysagiste"

    search = db.get(ProspectSearch, search_id)
    assert search is not None
    assert search.status == ProspectSearchStatus.WAITING_BROWSER.value
    assert search.request_count > 0
    assert any("Tendance Nature : gardé" in line["message"] for line in search.journal)


@pytest.mark.parametrize(
    ("validation_mode", "expected_lines"),
    [
        (
            ProspectSearchValidationMode.MANUAL,
            {
                "Tendance Nature : complet, à valider (tendance.nature@bluewin.ch).",
                "Graine de Vie : page Facebook lue, un seul moyen de contact, à valider.",
                "Paysagiste : 1 complet(s) sur 2 demandé(s).",
            },
        ),
        (
            _AUTOMATIC,
            {
                "Tendance Nature : gardé (tendance.nature@bluewin.ch).",
                "Graine de Vie : page Facebook lue, mis de côté.",
                "Paysagiste : 1 gardé(s) sur 2 demandé(s).",
            },
        ),
    ],
)
def test_the_journal_says_kept_only_when_the_search_creates_the_prospects(
    canned_world: None,
    monkeypatch: pytest.MonkeyPatch,
    db: Session,
    validation_mode: ProspectSearchValidationMode,
    expected_lines: set[str],
) -> None:
    async def page_without_email(**_: object) -> SimpleNamespace:
        return SimpleNamespace(place_title="Graine de Vie", emails=[], phone=None, website=None)

    monkeypatch.setattr(settings, "prospect_search_local_browser", True)
    monkeypatch.setattr(facebook_enrichment_scraper, "read_contact", page_without_email)
    search_id = _create_search(db, count=2, validation_mode=validation_mode)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    search = db.get(ProspectSearch, search_id)

    assert search is not None
    assert expected_lines <= {line["message"] for line in search.journal}
    set_aside = _candidates(db, search_id)["Graine de Vie"]
    assert (set_aside.status, set_aside.reject_detail) == (
        CandidateStatus.SET_ASIDE.value,
        "Portable sans email : joignable par SMS.",
    )


def test_each_journal_line_carries_its_time_as_naive_utc_to_the_second(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2)
    before_the_run = datetime.now(UTC).replace(tzinfo=None, microsecond=0)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    search = db.get(ProspectSearch, search_id)

    assert search is not None
    stored_line = search.journal[0]
    assert set(stored_line) == {"at", "message"}
    assert stored_line["at"] == datetime.fromisoformat(stored_line["at"]).isoformat(timespec="seconds")
    line = ProspectSearchDetail.model_validate(search).journal[0]
    assert line.at.tzinfo is None
    assert line.at >= before_the_run
    assert line.message == stored_line["message"]


def test_the_command_line_shows_a_journal_time_in_the_machine_s_timezone() -> None:
    expected = datetime(2026, 10, 4, 12, 34, 56, tzinfo=UTC).astimezone().strftime("%H:%M:%S")

    assert ProspectSearchCli.local_clock_time("2026-10-04T12:34:56") == expected


class _SilentFirstPagesClient(_CannedSearchClient):
    """Bright Data under load: the first local requests get no readable page, the later ones are answered."""

    silent_local_requests: int = 1

    def __init__(self) -> None:
        super().__init__()
        self._local_requests = 0

    async def google_local_html(self, query: str, *, country: str = "FR", start: int = 0) -> str | None:
        self._local_requests += 1
        if self._local_requests <= self.silent_local_requests:
            self.request_count += 1
            return None
        return await super().google_local_html(query, country=country, start=start)

    async def google_parsed(
        self, query: str, *, country: str = "FR", start: int = 0, local: bool = False
    ) -> dict[str, Any] | None:
        if local and self._local_requests <= self.silent_local_requests:
            self.request_count += 1
            return None
        return await super().google_parsed(query, country=country, start=start, local=local)


def test_a_town_google_did_not_answer_is_read_again_before_the_search_ends(
    canned_world: None, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner_module, "BrightDataClient", _SilentFirstPagesClient)
    search_id = _create_search(db)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    search = db.get(ProspectSearch, search_id)

    assert _candidates(db, search_id)["Tendance Nature"].status == CandidateStatus.KEPT.value
    assert search.progress["trades"]["paysagiste"]["towns"] == ["Sion"]
    assert any("Sion : Google n'a pas répondu" in line["message"] for line in search.journal)


def test_a_town_google_never_answered_is_not_counted_as_scanned(
    canned_world: None, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_SilentFirstPagesClient, "silent_local_requests", 100)
    monkeypatch.setattr(runner_module, "BrightDataClient", _SilentFirstPagesClient)
    search_id = _create_search(db)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    search = db.get(ProspectSearch, search_id)

    assert search.progress["trades"]["paysagiste"]["towns"] == []
    assert _candidates(db, search_id) == {}


def test_the_website_button_of_a_listing_is_stored_with_its_candidate(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    candidates = _candidates(db, search_id)

    assert candidates["Filvert Sarl"].has_website_button is True
    assert candidates["Tendance Nature"].has_website_button is False
    assert CandidateStore.facts_of(candidates["Filvert Sarl"]).has_website_button is True


def test_a_facebook_read_completes_the_waiting_candidate(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2, validation_mode=_AUTOMATIC)
    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    waiting = _candidates(db, search_id)["Graine de Vie"]

    async def read_page() -> ProspectSearchCandidate | None:
        updated = await prospect_search_service.record_facebook_contact(
            USER_ID,
            search_id,
            waiting.id,
            FacebookContactRead(is_readable=True, emails=["grainedevie@gmail.com"], phone=None, website=None),
        )
        # The read ends the browser round and restarts the run.
        await _wait_for_started_runs()
        return updated

    updated = asyncio.run(read_page())
    db.expire_all()

    assert updated is not None
    assert ProspectSearchCandidateResponse.model_validate(updated).status == "kept"
    candidate = db.get(ProspectSearchCandidate, waiting.id)
    assert candidate is not None
    assert (candidate.status, candidate.email, candidate.email_proof_level) == ("kept", "grainedevie@gmail.com", "a")
    assert candidate.prospect_id is not None
    search = db.get(ProspectSearch, search_id)
    assert search is not None and search.status == ProspectSearchStatus.COMPLETED.value


def test_a_facebook_email_on_the_business_s_own_domain_reveals_its_website(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2)
    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    waiting = _candidates(db, search_id)["Graine de Vie"]

    async def read_page() -> None:
        await prospect_search_service.record_facebook_contact(
            USER_ID,
            search_id,
            waiting.id,
            FacebookContactRead(is_readable=True, emails=["contact@graine-de-vie.ch"], phone=None, website=None),
        )
        await _wait_for_started_runs()

    asyncio.run(read_page())
    db.expire_all()

    candidate = db.get(ProspectSearchCandidate, waiting.id)
    assert candidate is not None
    assert (candidate.status, candidate.reject_reason) == ("rejected", "has_website")
    assert candidate.website == "https://graine-de-vie.ch/"
    assert candidate.prospect_id is None


def test_a_business_discarded_once_costs_nothing_to_the_next_search(canned_world: None, db: Session) -> None:
    first_search_id = _create_search(db, count=2, validation_mode=_AUTOMATIC)
    asyncio.run(ProspectSearchRunner(first_search_id).run())
    second_search_id = _create_search(db)
    second_run = ProspectSearchRunner(second_search_id)

    asyncio.run(second_run.run())
    db.expire_all()
    candidates = _candidates(db, second_search_id)

    assert candidates["Filvert Sarl"].reject_reason == CandidateRejectReason.PREVIOUSLY_REJECTED.value
    assert candidates["Tendance Nature"].reject_reason == CandidateRejectReason.ALREADY_KNOWN.value
    assert '"Filvert Sarl" Sion' not in second_run._client.queries


def test_another_user_cannot_read_or_correct_a_search(canned_world: None, db: Session) -> None:
    search_id = _create_search(db)

    assert prospect_search_service.get_for_user(db, USER_ID + 1, search_id) is None
    assert prospect_search_service.cancel(db, USER_ID + 1, search_id) is None
    assert prospect_search_service.browser_tasks(db, USER_ID + 1, search_id) is None


def test_a_cancelled_search_does_not_run(canned_world: None, db: Session) -> None:
    search_id = _create_search(db)
    prospect_search_service.cancel(db, USER_ID, search_id)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()

    assert _candidates(db, search_id) == {}
    search = db.get(ProspectSearch, search_id)
    assert search is not None and search.status == ProspectSearchStatus.CANCELLED.value


def test_two_searches_running_at_once_give_a_business_a_single_prospect(canned_world: None, db: Session) -> None:
    first_search_id = _create_search(db, count=2, validation_mode=_AUTOMATIC)
    second_search_id = _create_search(db, count=2, validation_mode=_AUTOMATIC)

    async def run_both() -> None:
        await asyncio.gather(ProspectSearchRunner(first_search_id).run(), ProspectSearchRunner(second_search_id).run())

    asyncio.run(run_both())
    db.expire_all()
    prospects = db.execute(select(ProspectDB).where(ProspectDB.email == "tendance.nature@bluewin.ch")).scalars().all()
    kept = _candidates(db, first_search_id)["Tendance Nature"]
    twin = _candidates(db, second_search_id)["Tendance Nature"]

    assert len(prospects) == 1
    assert (kept.status, kept.prospect_id) == (CandidateStatus.KEPT.value, prospects[0].id)
    assert (twin.status, twin.reject_reason, twin.prospect_id) == (
        CandidateStatus.REJECTED.value,
        CandidateRejectReason.ALREADY_KNOWN.value,
        prospects[0].id,
    )
    second_search = db.get(ProspectSearch, second_search_id)
    assert second_search is not None
    assert any(
        line["message"] == "Tendance Nature : écarté. Déjà dans vos prospects." for line in second_search.journal
    )


def test_keeping_by_hand_a_business_that_became_a_prospect_is_refused(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2, validation_mode=_AUTOMATIC)
    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    kept = _candidates(db, search_id)["Tendance Nature"]
    later_search_id = _create_search(db)
    twin = ProspectSearchCandidate(
        search_id=later_search_id,
        user_id=USER_ID,
        trade="paysagiste",
        origin=CandidateOrigin.GOOGLE_LOCAL.value,
        name="Tendance Nature",
        country="CH",
        city="Sion",
        phone=kept.phone,
        email=kept.email,
        email_proof_level="c",
        status=CandidateStatus.TO_CONFIRM.value,
        identity_keys=list(kept.identity_keys),
        evidence=[],
    )
    db.add(twin)
    db.commit()

    with pytest.raises(ProspectSearchError):
        asyncio.run(prospect_search_service.keep_candidate(db, USER_ID, later_search_id, twin.id))
    db.expire_all()

    assert len(db.execute(select(ProspectDB).where(ProspectDB.email == kept.email)).scalars().all()) == 1
    assert (twin.status, twin.reject_reason, twin.prospect_id) == (
        CandidateStatus.REJECTED.value,
        CandidateRejectReason.ALREADY_KNOWN.value,
        kept.prospect_id,
    )


def test_two_reads_of_the_same_page_at_once_keep_the_candidate_once(
    canned_world: None, monkeypatch: pytest.MonkeyPatch, db: Session
) -> None:
    search_id = _create_search(db, count=2, validation_mode=_AUTOMATIC)
    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    waiting = _candidates(db, search_id)["Graine de Vie"]

    async def mail_check_over_the_network(self: EmailDomainCheck, email: str) -> bool:
        await asyncio.sleep(0)
        return True

    monkeypatch.setattr(EmailDomainCheck, "receives_mail", mail_check_over_the_network)
    read = FacebookContactRead(is_readable=True, emails=["grainedevie@gmail.com"])

    async def read_twice() -> list[object]:
        return await asyncio.gather(
            facebook_contact_recorder.record(waiting.id, read), facebook_contact_recorder.record(waiting.id, read)
        )

    verdicts = asyncio.run(read_twice())
    db.expire_all()
    candidate = db.get(ProspectSearchCandidate, waiting.id)

    assert candidate is not None
    assert (candidate.status, candidate.reject_reason) == (CandidateStatus.KEPT.value, None)
    assert candidate.prospect_id is not None
    assert [verdict is None for verdict in verdicts] == [False, True]


def test_a_page_the_browser_could_not_read_leaves_its_candidate_waiting(
    canned_world: None, monkeypatch: pytest.MonkeyPatch, db: Session
) -> None:
    async def browser_unavailable(**_: object) -> None:
        return None

    monkeypatch.setattr(settings, "prospect_search_local_browser", True)
    monkeypatch.setattr(facebook_enrichment_scraper, "read_contact", browser_unavailable)
    search_id = _create_search(db, count=2)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    search = db.get(ProspectSearch, search_id)

    assert search is not None
    assert _candidates(db, search_id)["Graine de Vie"].status == CandidateStatus.NEEDS_BROWSER.value
    assert search.status == ProspectSearchStatus.WAITING_BROWSER.value
    unread_lines = [line for line in search.journal if "n'a pas pu être lue" in line["message"]]
    assert len(unread_lines) == 1


def test_resuming_a_finished_search_grants_one_more_run_of_towns(
    canned_world: None, monkeypatch: pytest.MonkeyPatch, db: Session
) -> None:
    monkeypatch.setattr(runner_module, "_MAX_TOWNS_PER_TRADE", 1)
    search_id = _create_search(db, count=5, cities=())

    def scanned_towns() -> list[str]:
        db.expire_all()
        search = db.get(ProspectSearch, search_id)
        assert search is not None
        return list(search.progress["trades"]["paysagiste"]["towns"])

    async def run_then_resume() -> tuple[list[str], list[str]]:
        await ProspectSearchRunner(search_id).run()
        db.expire_all()
        waiting = _candidates(db, search_id)["Graine de Vie"]
        # The end of the browser round starts the run again on its own: no more towns are granted.
        await prospect_search_service.record_facebook_contact(
            USER_ID, search_id, waiting.id, FacebookContactRead(is_readable=False)
        )
        await _wait_for_started_runs()
        towns_after_the_automatic_restart = scanned_towns()
        prospect_search_service.resume(db, USER_ID, search_id)
        await _wait_for_started_runs()
        return towns_after_the_automatic_restart, scanned_towns()

    towns_after_the_automatic_restart, towns_after_the_resume = asyncio.run(run_then_resume())
    search = db.get(ProspectSearch, search_id)

    assert search is not None
    assert len(towns_after_the_automatic_restart) == 1
    assert len(towns_after_the_resume) == 2
    assert search.progress["resume_count"] == 1
    assert search.status == ProspectSearchStatus.COMPLETED.value


def test_discarding_the_last_waiting_candidate_by_hand_lets_the_search_end(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2)
    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    waiting = _candidates(db, search_id)["Graine de Vie"]

    async def discard_by_hand() -> None:
        prospect_search_service.reject_candidate(db, USER_ID, search_id, waiting.id)
        await _wait_for_started_runs()

    asyncio.run(discard_by_hand())
    db.expire_all()
    search = db.get(ProspectSearch, search_id)

    assert search is not None and search.status == ProspectSearchStatus.COMPLETED.value


def test_stopping_a_search_leaves_the_candidates_not_verified_yet_untouched(
    canned_world: None, monkeypatch: pytest.MonkeyPatch, engine: Engine, db: Session
) -> None:
    search_id = _create_search(db, count=2)

    class _ClientOfASearchStoppedMidPage(_CannedSearchClient):
        async def google_parsed(
            self, query: str, *, country: str = "FR", start: int = 0, local: bool = False
        ) -> dict[str, Any] | None:
            if not self.queries:
                with sessionmaker(bind=engine)() as session:
                    prospect_search_service.cancel(session, USER_ID, search_id)
            return await super().google_parsed(query, country=country, start=start, local=local)

    monkeypatch.setattr(runner_module, "BrightDataClient", _ClientOfASearchStoppedMidPage)
    runner = ProspectSearchRunner(search_id)

    asyncio.run(runner.run())
    db.expire_all()
    candidates = _candidates(db, search_id)

    assert runner._client.queries == ['"Tendance Nature" Sion']
    assert candidates["Graine de Vie"].status == CandidateStatus.DISCOVERED.value
    assert candidates["Filvert Sarl"].status == CandidateStatus.DISCOVERED.value


def test_a_prospect_that_cannot_be_created_leaves_its_candidate_to_the_user(
    canned_world: None, monkeypatch: pytest.MonkeyPatch, db: Session
) -> None:
    async def creation_refused_by_the_database(db: Session, **_: object) -> None:
        db.add(ProspectDB(name=None, category="paysagiste", source="search", user_id=USER_ID))
        db.commit()

    monkeypatch.setattr(prospect_service, "create_prospect", creation_refused_by_the_database)
    search_id = _create_search(db, count=2, validation_mode=_AUTOMATIC)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    candidate = _candidates(db, search_id)["Tendance Nature"]
    search = db.get(ProspectSearch, search_id)

    assert (candidate.status, candidate.prospect_id) == (CandidateStatus.TO_CONFIRM.value, None)
    assert "n'a pas pu être créé" in (candidate.reject_detail or "")
    assert search is not None and search.status == ProspectSearchStatus.WAITING_BROWSER.value


def test_a_listing_with_a_website_button_waits_unverified_when_the_budget_runs_low(
    canned_world: None, db: Session
) -> None:
    search_id = _create_search(db, count=2)
    search = db.get(ProspectSearch, search_id)
    assert search is not None
    search.request_count = 110
    db.commit()
    runner = ProspectSearchRunner(search_id)

    asyncio.run(runner.run())
    db.expire_all()
    listing_with_a_website = _candidates(db, search_id)["Filvert Sarl"]

    assert (listing_with_a_website.status, listing_with_a_website.reject_reason) == (
        CandidateStatus.DISCOVERED.value,
        None,
    )
    assert '"Filvert Sarl" Sion' not in runner._client.queries


def test_trades_typed_under_two_spellings_are_searched_once(db: Session) -> None:
    search = prospect_search_service.create(
        db, USER_ID, ProspectSearchCreate(trades=["Paysagiste", "paysagiste", "jardinier"], country="CH")
    )

    assert search.trades == ["Paysagiste"]
    assert [line.trade for line in prospect_search_service.trade_counts(db, [search])[search.id]] == ["paysagiste"]


def test_a_finished_run_does_not_untrack_the_run_that_replaced_it(
    monkeypatch: pytest.MonkeyPatch, engine: Engine
) -> None:
    monkeypatch.setattr(service_module, "SessionLocal", sessionmaker(bind=engine))

    async def restart_as_the_first_run_ends() -> bool:
        second_run_may_end = asyncio.Event()
        started_runs: list[int] = []

        class _RunEndingAtOnceThenWaiting:
            def __init__(self, search_id: int) -> None:
                self._is_first_run = not started_runs
                started_runs.append(search_id)

            async def run(self) -> None:
                if not self._is_first_run:
                    await second_run_may_end.wait()

        monkeypatch.setattr(service_module, "ProspectSearchRunner", _RunEndingAtOnceThenWaiting)
        service = ProspectSearchService()
        service.start(1)
        # The first run ends during this pause; its end-of-run callback is queued, not fired yet.
        await asyncio.sleep(0)
        service.start(1)
        await asyncio.sleep(0)
        is_second_run_tracked = 1 in service._tasks
        second_run_may_end.set()
        await asyncio.gather(*list(service._tasks.values()))
        return is_second_run_tracked

    assert asyncio.run(restart_as_the_first_run_ends()) is True


def test_the_facebook_contact_route_hands_its_connection_back_before_the_network_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    steps: list[str] = []

    class _RequestSession:
        def commit(self) -> None:
            steps.append("connection handed back")

    async def record(*_: object) -> None:
        steps.append("facebook contact recorded")

    monkeypatch.setattr(prospect_search_service, "record_facebook_contact", record)

    with pytest.raises(HTTPException):
        asyncio.run(
            record_facebook_contact_route(
                1,
                2,
                FacebookContactPayload(is_readable=False),
                current_user=SimpleNamespace(id=USER_ID),  # type: ignore[arg-type]
                db=_RequestSession(),  # type: ignore[arg-type]
            )
        )

    assert steps == ["connection handed back", "facebook contact recorded"]


def test_a_manual_search_creates_no_prospect_and_leaves_its_candidates_pending(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    candidates = _candidates(db, search_id)
    kept = candidates["Tendance Nature"]

    assert (kept.status, kept.prospect_id, kept.is_pending) == (CandidateStatus.KEPT.value, None, True)
    assert db.execute(select(ProspectDB)).scalars().all() == []
    assert candidates["Filvert Sarl"].is_pending is False
    assert candidates["Graine de Vie"].is_pending is False
    assert [candidate.name for candidate in prospect_search_service.pending_candidates(db, USER_ID)] == [
        "Tendance Nature"
    ]


def test_a_facebook_read_in_a_manual_search_leaves_the_candidate_to_the_user(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2)
    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    waiting = _candidates(db, search_id)["Graine de Vie"]

    async def read_page() -> None:
        await prospect_search_service.record_facebook_contact(
            USER_ID, search_id, waiting.id, FacebookContactRead(is_readable=True, emails=["grainedevie@gmail.com"])
        )
        await _wait_for_started_runs()

    asyncio.run(read_page())
    db.expire_all()
    candidate = db.get(ProspectSearchCandidate, waiting.id)

    assert candidate is not None
    assert (candidate.status, candidate.prospect_id, candidate.is_pending) == (CandidateStatus.KEPT.value, None, True)
    assert db.execute(select(ProspectDB)).scalars().all() == []


def test_accepting_a_candidate_a_manual_search_kept_makes_it_a_prospect(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2)
    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    kept = _candidates(db, search_id)["Tendance Nature"]

    accepted = asyncio.run(prospect_search_service.keep_candidate(db, USER_ID, search_id, kept.id))

    assert accepted is not None
    assert (accepted.status, accepted.reject_detail, accepted.is_pending) == (CandidateStatus.KEPT.value, None, False)
    prospect = db.get(ProspectDB, accepted.prospect_id)
    assert prospect is not None
    assert (prospect.source, prospect.country, prospect.email) == ("search", "CH", "tendance.nature@bluewin.ch")


def test_accepting_a_set_aside_candidate_creates_its_prospect_without_moving_it(
    canned_world: None, db: Session
) -> None:
    search_id = _create_search(db)
    set_aside = _store_candidate(
        db,
        search_id,
        "Jardins Bravo",
        CandidateStatus.SET_ASIDE,
        phone="078 111 22 33",
        detail="Portable sans email : joignable par SMS.",
    )

    accepted = asyncio.run(prospect_search_service.keep_candidate(db, USER_ID, search_id, set_aside.id))

    assert accepted is not None
    assert (accepted.status, accepted.reject_detail) == (
        CandidateStatus.SET_ASIDE.value,
        "Portable sans email : joignable par SMS.",
    )
    assert accepted.is_pending is False
    prospect = db.get(ProspectDB, accepted.prospect_id)
    assert prospect is not None and prospect.phone == "078 111 22 33"


def test_accepting_a_candidate_to_confirm_keeps_it_by_hand(canned_world: None, db: Session) -> None:
    search_id = _create_search(db)
    to_confirm = _store_candidate(
        db,
        search_id,
        "Jardins Charlie",
        CandidateStatus.TO_CONFIRM,
        email="charlie@bluewin.ch",
        detail="Un email a été trouvé sans preuve franche qu'il lui appartient : à vous de voir.",
    )

    accepted = asyncio.run(prospect_search_service.keep_candidate(db, USER_ID, search_id, to_confirm.id))

    assert accepted is not None
    assert (accepted.status, accepted.reject_detail) == (CandidateStatus.KEPT.value, "Gardé à la main.")
    assert db.get(ProspectDB, accepted.prospect_id) is not None


@pytest.mark.parametrize(
    ("refuses_the_kept_candidate", "scanned_towns", "stop_reason"),
    [(False, ["Sion"], None), (True, ["Sion", "Bulle"], "towns")],
)
def test_refusing_a_kept_candidate_while_the_search_runs_sends_it_on_to_the_next_town(
    canned_world: None,
    monkeypatch: pytest.MonkeyPatch,
    engine: Engine,
    db: Session,
    refuses_the_kept_candidate: bool,
    scanned_towns: list[str],
    stop_reason: str | None,
) -> None:
    search_id = _create_search(db, cities=("Sion", "Bulle"))
    scan_town = ProspectSearchRunner._scan_town

    async def scan_town_then_refuse_what_sion_gave(
        runner: ProspectSearchRunner, state: Any, profile: Any, town: str
    ) -> bool:
        was_read = await scan_town(runner, state, profile, town)
        if town != "Sion" or not refuses_the_kept_candidate:
            return was_read
        with sessionmaker(bind=engine)() as session:
            kept = _candidates(session, search_id)["Tendance Nature"]
            assert kept.status == CandidateStatus.KEPT.value
            prospect_search_service.reject_candidate(session, USER_ID, search_id, kept.id)
        return was_read

    monkeypatch.setattr(ProspectSearchRunner, "_scan_town", scan_town_then_refuse_what_sion_gave)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    search = db.get(ProspectSearch, search_id)

    assert search is not None
    trade_progress = search.progress["trades"]["paysagiste"]
    assert (trade_progress["towns"], trade_progress["stop_reason"]) == (scanned_towns, stop_reason)


def test_a_candidate_refused_during_the_last_town_no_longer_counts_at_the_end_of_the_search(
    canned_world: None, monkeypatch: pytest.MonkeyPatch, engine: Engine, db: Session
) -> None:
    search_id = _create_search(db)
    scan_town = ProspectSearchRunner._scan_town

    async def scan_town_then_refuse_what_it_kept(
        runner: ProspectSearchRunner, state: Any, profile: Any, town: str
    ) -> bool:
        was_read = await scan_town(runner, state, profile, town)
        with sessionmaker(bind=engine)() as session:
            kept = _candidates(session, search_id)["Tendance Nature"]
            prospect_search_service.reject_candidate(session, USER_ID, search_id, kept.id)
        return was_read

    monkeypatch.setattr(ProspectSearchRunner, "_scan_town", scan_town_then_refuse_what_it_kept)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    search = db.get(ProspectSearch, search_id)

    assert search is not None
    assert search.progress["trades"]["paysagiste"]["stop_reason"] == "towns"
    assert "Paysagiste : 0 complet(s) sur 1 demandé(s)." in {line["message"] for line in search.journal}


def test_a_business_another_search_proposed_meanwhile_is_not_proposed_again_in_the_next_town(
    canned_world: None, monkeypatch: pytest.MonkeyPatch, engine: Engine, db: Session
) -> None:
    bulle_page = (
        "<html><body>"
        + _card("Jardins Bravo", ["4,8 (12) · Paysagiste", "Bulle", "078 111 22 33"], has_website=False)
        + "</body></html>"
    )

    class _ClientWithAnotherBusinessInBulle(_CannedSearchClient):
        async def google_local_html(self, query: str, *, country: str = "FR", start: int = 0) -> str | None:
            if "Bulle" not in query:
                return await super().google_local_html(query, country=country, start=start)
            self.request_count += 1
            return bulle_page if start == 0 else None

    monkeypatch.setattr(runner_module, "BrightDataClient", _ClientWithAnotherBusinessInBulle)
    search_id = _create_search(db, count=2, cities=("Sion", "Bulle"))
    other_search_id = _create_search(db)
    scan_town = ProspectSearchRunner._scan_town

    async def scan_town_while_another_search_proposes_bravo(
        runner: ProspectSearchRunner, state: Any, profile: Any, town: str
    ) -> None:
        await scan_town(runner, state, profile, town)
        if town != "Sion":
            return
        with sessionmaker(bind=engine)() as session:
            _store_candidate(
                session,
                other_search_id,
                "Jardins Bravo",
                CandidateStatus.SET_ASIDE,
                phone="078 111 22 33",
                identity_keys=CandidateIdentity.keys(
                    name="Jardins Bravo", city="Bulle", country="CH", phone="078 111 22 33"
                ),
            )

    monkeypatch.setattr(ProspectSearchRunner, "_scan_town", scan_town_while_another_search_proposes_bravo)
    runner = ProspectSearchRunner(search_id)

    asyncio.run(runner.run())
    db.expire_all()
    proposed_again = _candidates(db, search_id)["Jardins Bravo"]

    assert (proposed_again.status, proposed_again.reject_reason, proposed_again.is_pending) == (
        CandidateStatus.REJECTED.value,
        CandidateRejectReason.AWAITING_DECISION.value,
        False,
    )
    assert '"Jardins Bravo" Bulle' not in runner._client.queries


def test_the_candidates_waiting_for_a_decision_are_listed_across_searches_newest_first(db: Session) -> None:
    first_search_id, second_search_id = _create_search(db), _create_search(db)
    _store_candidate(db, first_search_id, "Gardé en attente", CandidateStatus.KEPT, email="garde@bluewin.ch")
    _store_candidate(db, first_search_id, "Déjà prospect", CandidateStatus.KEPT, prospect_id=41)
    _store_candidate(db, first_search_id, "Écarté", CandidateStatus.REJECTED)
    _store_candidate(db, first_search_id, "Page à lire", CandidateStatus.NEEDS_BROWSER)
    _store_candidate(db, second_search_id, "Mis de côté", CandidateStatus.SET_ASIDE, phone="078 111 22 33")
    _store_candidate(db, second_search_id, "À confirmer", CandidateStatus.TO_CONFIRM, email="doute@bluewin.ch")
    _store_candidate(db, second_search_id, "D'un autre compte", CandidateStatus.KEPT, user_id=USER_ID + 1)

    pending = asyncio.run(pending_candidates_route(current_user=_signed_in_user(), db=db))

    assert [(candidate.name, candidate.search_id, candidate.is_pending) for candidate in pending] == [
        ("À confirmer", second_search_id, True),
        ("Mis de côté", second_search_id, True),
        ("Gardé en attente", first_search_id, True),
    ]
    assert all(isinstance(candidate.created_at, datetime) for candidate in pending)


def test_the_list_of_pending_candidates_stops_at_its_limit(monkeypatch: pytest.MonkeyPatch, db: Session) -> None:
    monkeypatch.setattr(service_module, "_PENDING_CANDIDATES_LIMIT", 2)
    search_id = _create_search(db)
    for name in ("Premier", "Deuxième", "Troisième"):
        _store_candidate(db, search_id, name, CandidateStatus.KEPT)

    pending = prospect_search_service.pending_candidates(db, USER_ID)

    assert [candidate.name for candidate in pending] == ["Troisième", "Deuxième"]


def test_the_activity_counts_what_waits_and_shows_the_latest_search_at_work(db: Session) -> None:
    finished_search_id, running_search_id = _create_search(db), _create_search(db)
    finished, running = db.get(ProspectSearch, finished_search_id), db.get(ProspectSearch, running_search_id)
    assert finished is not None and running is not None
    finished.status, running.status = ProspectSearchStatus.COMPLETED.value, ProspectSearchStatus.RUNNING.value
    db.commit()
    _store_candidate(db, finished_search_id, "Gardé hier", CandidateStatus.KEPT)
    _store_candidate(db, running_search_id, "Gardé aujourd'hui", CandidateStatus.KEPT)
    _store_candidate(db, running_search_id, "Mis de côté", CandidateStatus.SET_ASIDE, phone="078 111 22 33")
    _store_candidate(db, running_search_id, "Déjà accepté", CandidateStatus.KEPT, prospect_id=41)
    _store_candidate(db, running_search_id, "D'un autre compte", CandidateStatus.KEPT, user_id=USER_ID + 1)

    activity = asyncio.run(activity_route(from_desktop_app=False, current_user=_signed_in_user(), db=db))

    assert activity.pending_count == 3
    assert activity.active_search is not None
    assert (activity.active_search.id, activity.active_search.status, activity.active_search.validation_mode) == (
        running_search_id,
        ProspectSearchStatus.RUNNING.value,
        ProspectSearchValidationMode.MANUAL.value,
    )
    counts = activity.active_search.trade_counts[0]
    assert (counts.trade, counts.wanted, counts.kept, counts.set_aside) == ("paysagiste", 1, 3, 1)


def test_the_activity_reads_the_search_at_work_without_its_journal(engine: Engine, db: Session) -> None:
    search = db.get(ProspectSearch, _create_search(db))
    assert search is not None
    search.status = ProspectSearchStatus.RUNNING.value
    search.journal = [{"at": "2026-10-05T08:00:00", "message": "Paysagiste · Sion : recherche en cours."}]
    db.commit()

    with sessionmaker(bind=engine)() as session:
        active_search = prospect_search_service.active_search(session, USER_ID)

        assert active_search is not None
        assert "journal" in inspect(active_search).unloaded


@pytest.mark.parametrize(
    ("status", "is_shown_as_active"),
    [
        (ProspectSearchStatus.QUEUED, False),
        (ProspectSearchStatus.PENDING, True),
        (ProspectSearchStatus.RUNNING, True),
        (ProspectSearchStatus.WAITING_BROWSER, True),
        (ProspectSearchStatus.COMPLETED, False),
        (ProspectSearchStatus.CANCELLED, False),
        (ProspectSearchStatus.FAILED, False),
    ],
)
def test_only_a_search_still_at_work_is_the_active_search(
    db: Session, status: ProspectSearchStatus, is_shown_as_active: bool
) -> None:
    search = db.get(ProspectSearch, _create_search(db))
    assert search is not None
    search.status = status.value
    db.commit()

    assert (prospect_search_service.active_search(db, USER_ID) is not None) is is_shown_as_active
    assert prospect_search_service.active_search(db, USER_ID + 1) is None


def _set_statuses(db: Session, statuses: dict[int, ProspectSearchStatus]) -> None:
    """Give searches the statuses a test starts from, one commit each, in the order given."""
    for search_id, search_status in statuses.items():
        search = db.get(ProspectSearch, search_id)
        assert search is not None
        search.status = search_status.value
        db.commit()


def _status_of(db: Session, search_id: int) -> str:
    db.expire_all()
    search = db.get(ProspectSearch, search_id)
    assert search is not None
    return search.status


def _end_runs_at_once(monkeypatch: pytest.MonkeyPatch, db: Session) -> None:
    """Replace the runner by one that ends its search as completed, without searching anything."""

    class _RunEndingCompleted:
        def __init__(self, search_id: int) -> None:
            self._search_id = search_id

        async def run(self) -> None:
            search = db.get(ProspectSearch, self._search_id)
            assert search is not None
            if search.status != ProspectSearchStatus.CANCELLED.value:
                search.status = ProspectSearchStatus.COMPLETED.value
            db.commit()

    monkeypatch.setattr(service_module, "ProspectSearchRunner", _RunEndingCompleted)


_SEARCH_PAYLOAD: dict[str, Any] = {"trades": ["Paysagiste"], "country": "CH", "cities": ["Sion"], "count_per_trade": 1}


def test_a_search_launched_while_another_is_at_work_waits_its_turn(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    started_search_ids: list[int] = []
    monkeypatch.setattr(prospect_search_service, "start", started_search_ids.append)
    client = _client(db)

    first = client.post("/prospect-searches", json=_SEARCH_PAYLOAD).json()
    second = client.post("/prospect-searches", json=_SEARCH_PAYLOAD).json()
    third = client.post("/prospect-searches", json=_SEARCH_PAYLOAD).json()
    activity = client.get("/prospect-searches/activity").json()

    assert (first["status"], second["status"], third["status"]) == ("pending", "queued", "queued")
    assert started_search_ids == [first["id"]]
    assert activity["active_search"]["id"] == first["id"]
    assert [search["id"] for search in activity["queued_searches"]] == [second["id"], third["id"]]


def test_the_search_queued_first_starts_when_the_search_at_work_ends(
    canned_world: None, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    at_work_id, first_queued_id, second_queued_id = _create_search(db), _create_search(db), _create_search(db)
    _set_statuses(
        db,
        {
            at_work_id: ProspectSearchStatus.RUNNING,
            first_queued_id: ProspectSearchStatus.QUEUED,
            second_queued_id: ProspectSearchStatus.QUEUED,
        },
    )
    _end_runs_at_once(monkeypatch, db)
    started_search_ids: list[int] = []
    monkeypatch.setattr(prospect_search_service, "start", started_search_ids.append)

    asyncio.run(prospect_search_service._run_then_start_the_next(at_work_id))

    assert started_search_ids == [first_queued_id]
    assert [_status_of(db, search_id) for search_id in (at_work_id, first_queued_id, second_queued_id)] == [
        "completed",
        "pending",
        "queued",
    ]


def test_a_search_taken_out_of_the_queue_never_runs(
    canned_world: None, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    at_work_id, queued_id = _create_search(db), _create_search(db)
    _set_statuses(db, {at_work_id: ProspectSearchStatus.RUNNING, queued_id: ProspectSearchStatus.QUEUED})
    _end_runs_at_once(monkeypatch, db)
    started_search_ids: list[int] = []
    monkeypatch.setattr(prospect_search_service, "start", started_search_ids.append)

    taken_out = _client(db).post(f"/prospect-searches/{queued_id}/cancel").json()
    asyncio.run(prospect_search_service._run_then_start_the_next(at_work_id))

    assert taken_out["status"] == "cancelled"
    assert started_search_ids == []
    assert _status_of(db, queued_id) == "cancelled"


def test_the_queue_refuses_a_search_past_its_limit(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(prospect_search_service, "start", lambda search_id: None)
    client = _client(db)

    statuses = [client.post("/prospect-searches", json=_SEARCH_PAYLOAD).json()["status"] for _ in range(6)]
    refused = client.post("/prospect-searches", json=_SEARCH_PAYLOAD)

    assert statuses == ["pending", "queued", "queued", "queued", "queued", "queued"]
    assert refused.status_code == 422
    assert refused.json()["detail"].startswith("La file d'attente est pleine : 5 recherches attendent déjà.")
    assert len(client.get("/prospect-searches").json()) == 6


def test_carrying_on_a_search_while_another_is_at_work_queues_it(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    at_work_id, stopped_id = _create_search(db), _create_search(db)
    _set_statuses(db, {at_work_id: ProspectSearchStatus.RUNNING, stopped_id: ProspectSearchStatus.CANCELLED})
    started_search_ids: list[int] = []
    monkeypatch.setattr(prospect_search_service, "start", started_search_ids.append)

    resumed = _client(db).post(f"/prospect-searches/{stopped_id}/resume").json()

    assert resumed["status"] == "queued"
    assert started_search_ids == []


def test_a_search_whose_facebook_pages_are_read_queues_behind_the_search_at_work(
    canned_world: None, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    waiting_id, at_work_id = _create_search(db), _create_search(db)
    _set_statuses(db, {waiting_id: ProspectSearchStatus.WAITING_BROWSER, at_work_id: ProspectSearchStatus.RUNNING})
    unread = _store_candidate(db, waiting_id, "Page à lire", CandidateStatus.NEEDS_BROWSER)
    started_search_ids: list[int] = []
    monkeypatch.setattr(prospect_search_service, "start", started_search_ids.append)

    asyncio.run(prospect_search_service.decide_candidates(db, USER_ID, CandidateDecisions(reject=[unread.id])))

    assert _status_of(db, waiting_id) == "queued"
    assert started_search_ids == []


def test_the_startup_starts_a_queue_left_without_a_search_at_work(
    canned_world: None, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    first_queued_id, second_queued_id = _create_search(db), _create_search(db)
    _set_statuses(db, {first_queued_id: ProspectSearchStatus.QUEUED, second_queued_id: ProspectSearchStatus.QUEUED})
    started_search_ids: list[int] = []
    monkeypatch.setattr(prospect_search_service, "start", started_search_ids.append)

    prospect_search_service.resume_interrupted()

    assert started_search_ids == [first_queued_id]
    assert (_status_of(db, first_queued_id), _status_of(db, second_queued_id)) == ("pending", "queued")


def test_the_fixed_paths_are_not_taken_for_a_search_id(db: Session) -> None:
    client = _client(db)

    assert client.get("/prospect-searches/activity").json() == {
        "pending_count": 0,
        "active_search": None,
        "queued_searches": [],
        "is_desktop_app_online": False,
    }
    assert client.get("/prospect-searches/pending-candidates").json() == []
    decisions = client.post("/prospect-searches/candidates/decisions", json={"accept": [], "reject": []})
    assert decisions.json() == {"accepted": 0, "rejected": 0, "refused": []}


def test_decisions_taken_together_accept_refuse_and_report_the_business_already_known(
    canned_world: None, db: Session
) -> None:
    search_id = _create_search(db)
    kept = _store_candidate(db, search_id, "Jardins Alpha", CandidateStatus.KEPT, email="alpha@bluewin.ch")
    set_aside = _store_candidate(db, search_id, "Jardins Bravo", CandidateStatus.SET_ASIDE, phone="078 111 22 33")
    unwanted = _store_candidate(db, search_id, "Jardins Charlie", CandidateStatus.TO_CONFIRM, email="c@bluewin.ch")
    already_known = _store_candidate(db, search_id, "Jardins Delta", CandidateStatus.KEPT, email="delta@bluewin.ch")
    db.add(
        ProspectDB(
            name="Delta Paysages", category="paysagiste", source="manual", user_id=USER_ID, email="delta@bluewin.ch"
        )
    )
    db.commit()

    outcome = asyncio.run(
        decide_candidates_route(
            CandidateDecisions(accept=[kept.id, set_aside.id, already_known.id], reject=[unwanted.id]),
            current_user=_signed_in_user(),
            db=db,
        )
    )
    db.expire_all()

    assert (outcome.accepted, outcome.rejected) == (2, 1)
    assert outcome.refused == [
        RefusedCandidateDecision(candidate_id=already_known.id, detail="Cette entreprise est déjà dans vos prospects.")
    ]
    assert kept.prospect_id is not None
    assert (set_aside.status, set_aside.prospect_id is not None) == (CandidateStatus.SET_ASIDE.value, True)
    assert (unwanted.status, unwanted.reject_reason) == (
        CandidateStatus.REJECTED.value,
        CandidateRejectReason.MANUAL.value,
    )
    assert (already_known.status, already_known.reject_reason) == (
        CandidateStatus.REJECTED.value,
        CandidateRejectReason.ALREADY_KNOWN.value,
    )
    assert len(db.execute(select(ProspectDB)).scalars().all()) == 3


def test_two_pending_candidates_of_one_business_accepted_together_give_a_single_prospect(
    canned_world: None, db: Session
) -> None:
    search_id = _create_search(db)
    first = _store_candidate(db, search_id, "Jardins Alpha", CandidateStatus.KEPT, email="alpha@bluewin.ch")
    twin = _store_candidate(db, search_id, "Alpha Paysages", CandidateStatus.KEPT, email="alpha@bluewin.ch")

    outcome = asyncio.run(
        prospect_search_service.decide_candidates(db, USER_ID, CandidateDecisions(accept=[first.id, twin.id]))
    )

    assert (outcome.accepted, [refusal.candidate_id for refusal in outcome.refused]) == (1, [twin.id])
    assert len(db.execute(select(ProspectDB)).scalars().all()) == 1


def test_an_acceptance_that_read_the_candidate_before_another_one_ended_does_not_create_it_again(
    canned_world: None, monkeypatch: pytest.MonkeyPatch, snapshot_engine: Engine
) -> None:
    open_session = sessionmaker(bind=snapshot_engine)
    with open_session() as setup:
        search_id = _create_search(setup)
        candidate_id = _store_candidate(
            setup, search_id, "Jardins Alpha", CandidateStatus.KEPT, email="alpha@bluewin.ch"
        ).id
    created_names: list[str] = []
    create_prospect = prospect_service.create_prospect

    async def create_and_note(**arguments: Any) -> Any:
        created_names.append(arguments["prospect"].name)
        return await create_prospect(**arguments)

    monkeypatch.setattr(prospect_service, "create_prospect", create_and_note)

    with open_session() as first_request, open_session() as late_request:
        candidate_read_before_the_first_acceptance = late_request.get(ProspectSearchCandidate, candidate_id)
        assert candidate_read_before_the_first_acceptance is not None
        asyncio.run(prospect_search_service.keep_candidate(first_request, USER_ID, search_id, candidate_id))
        accepted_again = asyncio.run(
            prospect_search_service.keep_candidate(late_request, USER_ID, search_id, candidate_id)
        )
        prospects = late_request.execute(select(ProspectDB)).scalars().all()

        assert created_names == ["Jardins Alpha"]
        assert len(prospects) == 1
        assert accepted_again is not None
        assert (accepted_again.status, accepted_again.prospect_id) == (CandidateStatus.KEPT.value, prospects[0].id)


def test_a_decision_on_another_user_s_candidate_is_not_applied(canned_world: None, db: Session) -> None:
    search_id = _create_search(db)
    candidate = _store_candidate(db, search_id, "Jardins Alpha", CandidateStatus.KEPT, email="alpha@bluewin.ch")

    outcome = asyncio.run(
        prospect_search_service.decide_candidates(
            db, USER_ID + 1, CandidateDecisions(accept=[candidate.id], reject=[candidate.id + 1])
        )
    )
    db.expire_all()

    assert (outcome.accepted, outcome.rejected) == (0, 0)
    assert {(refusal.candidate_id, refusal.detail) for refusal in outcome.refused} == {
        (candidate.id, "Ce candidat est introuvable."),
        (candidate.id + 1, "Ce candidat est introuvable."),
    }
    assert (candidate.status, candidate.prospect_id) == (CandidateStatus.KEPT.value, None)


def test_an_accepted_candidate_whose_prospect_cannot_be_created_stays_pending(
    canned_world: None, monkeypatch: pytest.MonkeyPatch, db: Session
) -> None:
    async def creation_refused_by_the_database(db: Session, **_: object) -> None:
        db.add(ProspectDB(name=None, category="paysagiste", source="search", user_id=USER_ID))
        db.commit()

    monkeypatch.setattr(prospect_service, "create_prospect", creation_refused_by_the_database)
    search_id = _create_search(db)
    kept = _store_candidate(db, search_id, "Jardins Alpha", CandidateStatus.KEPT, email="alpha@bluewin.ch")

    outcome = asyncio.run(prospect_search_service.decide_candidates(db, USER_ID, CandidateDecisions(accept=[kept.id])))
    db.expire_all()

    assert outcome.accepted == 0
    assert outcome.refused == [
        RefusedCandidateDecision(
            candidate_id=kept.id, detail="Le prospect n'a pas pu être créé. Réessayez dans un instant."
        )
    ]
    assert (kept.status, kept.prospect_id, kept.is_pending) == (CandidateStatus.KEPT.value, None, True)


def test_decisions_that_fail_unexpectedly_are_reported_while_the_others_are_applied(
    canned_world: None, monkeypatch: pytest.MonkeyPatch, db: Session
) -> None:
    waiting_search_id, other_search_id = _create_search(db), _create_search(db)
    waiting_search, other_search = db.get(ProspectSearch, waiting_search_id), db.get(ProspectSearch, other_search_id)
    assert waiting_search is not None and other_search is not None
    waiting_search.status = ProspectSearchStatus.WAITING_BROWSER.value
    other_search.status = ProspectSearchStatus.COMPLETED.value
    db.commit()
    unread = _store_candidate(db, waiting_search_id, "Page à lire", CandidateStatus.NEEDS_BROWSER)
    refusal_lost = _store_candidate(db, waiting_search_id, "Jardins Charlie", CandidateStatus.TO_CONFIRM)
    accepted = _store_candidate(db, waiting_search_id, "Jardins Alpha", CandidateStatus.KEPT, email="alpha@bluewin.ch")
    acceptance_lost = _store_candidate(db, other_search_id, "Jardins Bravo", CandidateStatus.KEPT, email="b@bluewin.ch")
    write_back = CandidateStore.write_back
    load_known_businesses = KnownBusinessIndex.load

    def write_back_failing_for_charlie(row: ProspectSearchCandidate, facts: Any, verdict: Any) -> None:
        if row.name == "Jardins Charlie":
            raise OperationalError("UPDATE prospect_search_candidates", None, ConnectionError("connexion perdue"))
        write_back(row, facts, verdict)

    def known_businesses_unreadable_for_the_other_search(session: Session, **scope: Any) -> KnownBusinessIndex:
        if scope["search_id"] == other_search_id:
            raise OperationalError("SELECT prospects", None, ConnectionError("connexion perdue"))
        return load_known_businesses(session, **scope)

    monkeypatch.setattr(CandidateStore, "write_back", write_back_failing_for_charlie)
    monkeypatch.setattr(KnownBusinessIndex, "load", known_businesses_unreadable_for_the_other_search)
    started_search_ids: list[int] = []
    monkeypatch.setattr(prospect_search_service, "start", started_search_ids.append)

    outcome = asyncio.run(
        prospect_search_service.decide_candidates(
            db,
            USER_ID,
            CandidateDecisions(accept=[accepted.id, acceptance_lost.id], reject=[unread.id, refusal_lost.id]),
        )
    )
    db.expire_all()

    assert (outcome.accepted, outcome.rejected) == (1, 1)
    assert outcome.refused == [
        RefusedCandidateDecision(
            candidate_id=refusal_lost.id, detail="Le refus n'a pas pu être enregistré. Réessayez dans un instant."
        ),
        RefusedCandidateDecision(
            candidate_id=acceptance_lost.id, detail="Le prospect n'a pas pu être créé. Réessayez dans un instant."
        ),
    ]
    assert accepted.prospect_id is not None
    assert (refusal_lost.status, acceptance_lost.status, acceptance_lost.prospect_id) == (
        CandidateStatus.TO_CONFIRM.value,
        CandidateStatus.KEPT.value,
        None,
    )
    assert started_search_ids == [waiting_search_id]


def test_a_batch_of_decisions_interrupted_midway_still_lets_the_waiting_search_carry_on(
    canned_world: None, monkeypatch: pytest.MonkeyPatch, db: Session
) -> None:
    search_id = _create_search(db)
    search = db.get(ProspectSearch, search_id)
    assert search is not None
    search.status = ProspectSearchStatus.WAITING_BROWSER.value
    db.commit()
    unread = _store_candidate(db, search_id, "Page à lire", CandidateStatus.NEEDS_BROWSER)
    kept = _store_candidate(db, search_id, "Jardins Alpha", CandidateStatus.KEPT, email="alpha@bluewin.ch")

    async def request_cancelled(*_: object, **__: object) -> None:
        raise asyncio.CancelledError

    monkeypatch.setattr(CandidateStore, "promote_accepted", request_cancelled)
    started_search_ids: list[int] = []
    monkeypatch.setattr(prospect_search_service, "start", started_search_ids.append)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            prospect_search_service.decide_candidates(
                db, USER_ID, CandidateDecisions(accept=[kept.id], reject=[unread.id])
            )
        )

    assert started_search_ids == [search_id]


def test_deciding_the_last_candidate_waiting_for_a_browser_lets_the_search_end(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2)
    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    waiting = _candidates(db, search_id)["Graine de Vie"]

    async def refuse_among_other_decisions() -> None:
        await prospect_search_service.decide_candidates(db, USER_ID, CandidateDecisions(reject=[waiting.id]))
        await _wait_for_started_runs()

    asyncio.run(refuse_among_other_decisions())
    db.expire_all()
    search = db.get(ProspectSearch, search_id)

    assert search is not None and search.status == ProspectSearchStatus.COMPLETED.value


@pytest.mark.parametrize("validation_mode", [ProspectSearchValidationMode.MANUAL, _AUTOMATIC])
def test_restoring_a_kept_candidate_refused_by_hand_puts_it_back_in_waiting_without_a_prospect(
    db: Session, validation_mode: ProspectSearchValidationMode
) -> None:
    search_id = _create_search(db, validation_mode=validation_mode)
    kept = _store_candidate(db, search_id, "Jardins Alpha", CandidateStatus.KEPT, email="alpha@bluewin.ch")
    candidate_path = f"/prospect-searches/{search_id}/candidates/{kept.id}"
    client = _client(db)

    refused = client.post(f"{candidate_path}/reject").json()
    restored_by_someone_else = _client(db, user_id=USER_ID + 1).post(f"{candidate_path}/restore")
    restored = client.post(f"{candidate_path}/restore")

    assert (refused["status"], refused["reject_reason"]) == ("rejected", "manual")
    assert restored_by_someone_else.status_code == 404
    assert restored.status_code == 200
    assert {key: restored.json()[key] for key in ("status", "reject_reason", "prospect_id", "is_pending")} == {
        "status": "kept",
        "reject_reason": None,
        "prospect_id": None,
        "is_pending": True,
    }
    assert db.execute(select(ProspectDB)).scalars().all() == []


@pytest.mark.parametrize(
    ("status", "reject_reason"),
    [(CandidateStatus.KEPT, None), (CandidateStatus.REJECTED, CandidateRejectReason.HAS_WEBSITE)],
)
def test_restoring_a_candidate_the_user_did_not_refuse_is_refused(
    db: Session, status: CandidateStatus, reject_reason: CandidateRejectReason | None
) -> None:
    search_id = _create_search(db)
    candidate = _store_candidate(
        db, search_id, "Jardins Alpha", status, email="alpha@bluewin.ch", reject_reason=reject_reason
    )

    response = _client(db).post(f"/prospect-searches/{search_id}/candidates/{candidate.id}/restore")
    db.expire_all()

    assert response.status_code == 409
    assert response.json() == {"detail": "Seuls les candidats que vous avez refusés peuvent être remis en attente."}
    assert candidate.status == status.value


@pytest.mark.parametrize(
    ("status", "detail", "email", "phone"),
    [
        (CandidateStatus.KEPT, None, "alpha@bluewin.ch", None),
        (CandidateStatus.SET_ASIDE, "Portable sans email : joignable par SMS.", None, "079 473 19 61"),
        (
            CandidateStatus.TO_CONFIRM,
            "La vérification sur Google n'a pas répondu : fiche non contrôlée.",
            "alpha@bluewin.ch",
            None,
        ),
    ],
)
def test_undoing_a_refusal_gives_the_lead_back_the_place_it_had(
    db: Session, status: CandidateStatus, detail: str | None, email: str | None, phone: str | None
) -> None:
    search_id = _create_search(db)
    lead = _store_candidate(db, search_id, "Jardins Alpha", status, email=email, phone=phone, detail=detail)
    candidate_path = f"/prospect-searches/{search_id}/candidates/{lead.id}"
    client = _client(db)

    client.post(f"{candidate_path}/reject")
    restored = client.post(f"{candidate_path}/restore").json()
    db.expire_all()

    assert (restored["status"], restored["reject_reason"], restored["reject_detail"], restored["is_pending"]) == (
        status.value,
        None,
        detail,
        True,
    )
    assert (lead.status_before_refusal, lead.detail_before_refusal) == (None, None)


def test_a_lead_refused_twice_still_comes_back_with_the_place_it_had(db: Session) -> None:
    search_id = _create_search(db)
    unverified_detail = "La vérification sur Google n'a pas répondu : fiche non contrôlée."
    lead = _store_candidate(
        db, search_id, "Jardins Alpha", CandidateStatus.TO_CONFIRM, email="alpha@bluewin.ch", detail=unverified_detail
    )
    client = _client(db)

    client.post(f"/prospect-searches/{search_id}/candidates/{lead.id}/reject")
    client.post("/prospect-searches/candidates/decisions", json={"accept": [], "reject": [lead.id]})
    restored = client.post(f"/prospect-searches/{search_id}/candidates/{lead.id}/restore").json()

    assert (restored["status"], restored["reject_detail"]) == ("to_confirm", unverified_detail)


def test_a_restored_candidate_the_rules_would_discard_is_left_to_the_user(db: Session) -> None:
    search_id = _create_search(db)
    refused_before_places_were_kept = _store_candidate(
        db,
        search_id,
        "Jardins Sans Contact",
        CandidateStatus.REJECTED,
        detail="Écarté à la main.",
        reject_reason=CandidateRejectReason.MANUAL,
    )
    candidate_path = f"/prospect-searches/{search_id}/candidates/{refused_before_places_were_kept.id}"
    client = _client(db)

    restored = client.post(f"{candidate_path}/restore").json()

    assert (restored["status"], restored["reject_reason"], restored["reject_detail"], restored["is_pending"]) == (
        "to_confirm",
        None,
        "Remis à valider à la main.",
        True,
    )


def test_the_command_line_starts_an_automatic_search_unless_told_otherwise() -> None:
    class _RecordingApi:
        def __init__(self) -> None:
            self.created_searches: list[dict[str, Any]] = []

        async def post(self, path: str, json: dict[str, Any]) -> SimpleNamespace:
            self.created_searches.append(json)
            return SimpleNamespace(status_code=201, json=lambda: {"id": 7}, raise_for_status=lambda: None)

    api = _RecordingApi()
    cli = ProspectSearchCli(api, reads_facebook_pages=False)  # type: ignore[arg-type]

    asyncio.run(cli.create(parse_command_line(["--trades", "paysagiste"])))
    asyncio.run(cli.create(parse_command_line(["--trades", "paysagiste", "--validation", "manual"])))

    assert [search["validation_mode"] for search in api.created_searches] == ["automatic", "manual"]


def test_the_command_line_waits_for_an_api_that_does_not_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("GET", "https://api.example/prospect-searches/7")

    class _RestartingApi:
        def __init__(self) -> None:
            self.answers: list[httpx.Response | Exception] = [
                httpx.ConnectError("connection refused", request=request),
                httpx.Response(502, request=request),
                httpx.Response(200, request=request, json={"status": "completed", "journal": []}),
            ]

        async def get(self, path: str) -> httpx.Response:
            answer = self.answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer

    async def no_wait(seconds: float) -> None:
        return None

    monkeypatch.setattr(prospect_search_cli_module.asyncio, "sleep", no_wait)
    cli = ProspectSearchCli(_RestartingApi(), reads_facebook_pages=False)  # type: ignore[arg-type]

    assert asyncio.run(cli.follow(7))["status"] == "completed"


def test_a_refused_request_is_not_tried_again() -> None:
    request = httpx.Request("POST", "https://api.example/prospect-searches/7/candidates/1/facebook-contact")
    refusal = httpx.HTTPStatusError("refused", request=request, response=httpx.Response(422, request=request))

    assert ProspectSearchCli.is_transient_api_error(refusal) is False
