"""A whole prospect search, with the web and the language model replaced by canned pages.

What is checked is the chain an operator would do by hand: read the local results,
discard the business with a website, keep the one whose email a directory gives,
remember the discarded one for the next search, and hand the Facebook pages to a
browser.
"""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import services.activity_log_service as activity_log_module
import services.prospect_search.facebook_contact as facebook_contact_module
import services.prospect_search.runner as runner_module
import services.prospect_search.service as service_module
from api.v1.routes.prospect_searches import record_facebook_contact as record_facebook_contact_route
from core.config import settings
from enums.prospect_search import (
    CandidateOrigin,
    CandidateRejectReason,
    CandidateStatus,
    ProspectSearchChannel,
    ProspectSearchStatus,
)
from enums.website_status import WebsiteStatus
from models.prospect_db import ProspectDB
from models.prospect_search import ProspectSearch
from models.prospect_search_candidate import ProspectSearchCandidate
from prospect_search_cli import ProspectSearchCli
from schemas.prospect_search import FacebookContactPayload, ProspectSearchCreate, ProspectSearchDetail
from scrappers.facebook_enrichment_scraper import facebook_enrichment_scraper
from services.enrichment_service import enrichment_service
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


def _create_search(db: Session, *, count: int = 1, cities: tuple[str, ...] = ("Sion",)) -> int:
    search = prospect_search_service.create(
        db,
        USER_ID,
        ProspectSearchCreate(
            trades=["Paysagiste"],
            country="CH",
            cities=list(cities),
            count_per_trade=count,
            channel=ProspectSearchChannel.EMAIL,
        ),
    )
    return search.id


async def _wait_for_started_runs() -> None:
    """Let the runs the service started in the background finish before the loop closes."""
    await asyncio.gather(*list(prospect_search_service._tasks.values()))


def _candidates(db: Session, search_id: int) -> dict[str, ProspectSearchCandidate]:
    rows = db.execute(select(ProspectSearchCandidate).where(ProspectSearchCandidate.search_id == search_id)).scalars()
    return {row.name: row for row in rows}


def test_a_search_keeps_the_proven_contact_and_discards_with_reasons(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2)

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


def test_the_website_button_of_a_listing_is_stored_with_its_candidate(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2)

    asyncio.run(ProspectSearchRunner(search_id).run())
    db.expire_all()
    candidates = _candidates(db, search_id)

    assert candidates["Filvert Sarl"].has_website_button is True
    assert candidates["Tendance Nature"].has_website_button is False
    assert CandidateStore.facts_of(candidates["Filvert Sarl"]).has_website_button is True


def test_a_facebook_read_completes_the_waiting_candidate(canned_world: None, db: Session) -> None:
    search_id = _create_search(db, count=2)
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
    first_search_id = _create_search(db, count=2)
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
    first_search_id, second_search_id = _create_search(db, count=2), _create_search(db, count=2)

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
    search_id = _create_search(db, count=2)
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
    search_id = _create_search(db, count=2)
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
    search_id = _create_search(db, count=2)

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


def test_a_finished_run_does_not_untrack_the_run_that_replaced_it(monkeypatch: pytest.MonkeyPatch) -> None:
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
