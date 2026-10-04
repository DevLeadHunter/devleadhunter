"""
Prospect search service — creates, starts, reads and corrects objective-driven searches.
"""

from __future__ import annotations

import asyncio
import functools
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.database import SessionLocal
from enums.prospect_search import CandidateRejectReason, CandidateStatus, ProspectSearchStatus
from models.prospect_search import ProspectSearch
from models.prospect_search_candidate import ProspectSearchCandidate
from schemas.prospect_search import ProspectSearchCreate, SearchTradeCounts
from services.country_profiles import CountryProfiles
from services.organization_service import organization_service
from services.prospect_search.candidate_decision import CandidateVerdict
from services.prospect_search.candidate_store import CandidateStore
from services.prospect_search.facebook_contact import FacebookContactRead, facebook_contact_recorder
from services.prospect_search.runner import ProspectSearchRunner
from services.prospect_search.trade_catalog import TradeCatalog

logger = logging.getLogger(__name__)

_RECENT_SEARCHES_LIMIT: int = 30
_ACTIVE_STATUSES: tuple[str, ...] = (ProspectSearchStatus.PENDING.value, ProspectSearchStatus.RUNNING.value)
_KNOWN_BUSINESS_REASONS: tuple[str, ...] = (
    CandidateRejectReason.ALREADY_KNOWN.value,
    CandidateRejectReason.DO_NOT_CONTACT.value,
)
_ALREADY_A_PROSPECT: str = "Cette entreprise est déjà dans vos prospects."


class ProspectSearchError(ValueError):
    """A search request the user must correct (message shown as is)."""


class ProspectSearchService:
    """Entry point of the prospect search for the routes and the application startup."""

    def __init__(self) -> None:
        self._tasks: dict[int, asyncio.Task[None]] = {}

    def create(self, db: Session, user_id: int, payload: ProspectSearchCreate) -> ProspectSearch:
        """
        Store a new search.

        Args:
            db: Active database session.
            user_id: Owner of the search.
            payload: The objective.

        Returns:
            The stored search, still pending (call :meth:`start` to run it).

        Raises:
            ProspectSearchError: No usable trade, or a country the prospection is not open to.
        """
        typed_trade_by_key: dict[str, str] = {}
        for trade in payload.trades:
            typed_trade = trade.strip()
            if typed_trade:
                typed_trade_by_key.setdefault(TradeCatalog.resolve(typed_trade).key, typed_trade)
        trades = list(typed_trade_by_key.values())
        if not trades:
            raise ProspectSearchError("Indiquez au moins un métier.")
        profile = CountryProfiles.declared(payload.country)
        if profile is None or not profile.enabled:
            raise ProspectSearchError("La prospection n'est pas ouverte dans ce pays.")

        search = ProspectSearch(
            user_id=user_id,
            trades=trades,
            country=profile.code,
            cities=[city.strip() for city in payload.cities if city.strip()],
            count_per_trade=payload.count_per_trade,
            channel=payload.channel.value,
            only_without_website=payload.only_without_website,
            minimum_rating=payload.minimum_rating,
            status=ProspectSearchStatus.PENDING.value,
            progress={},
            journal=[],
        )
        db.add(search)
        db.commit()
        db.refresh(search)
        return search

    def start(self, search_id: int) -> None:
        """Run a search in the background; a search already running is left alone."""
        running = self._tasks.get(search_id)
        if running is not None and not running.done():
            return
        task = asyncio.create_task(ProspectSearchRunner(search_id).run())
        self._tasks[search_id] = task
        task.add_done_callback(functools.partial(self._forget_finished_run, search_id))

    def _forget_finished_run(self, search_id: int, finished: asyncio.Task[None]) -> None:
        """Drop a finished run, unless a newer run of the same search already took its place."""
        if self._tasks.get(search_id) is finished:
            del self._tasks[search_id]

    def list_for_user(self, db: Session, user_id: int) -> list[ProspectSearch]:
        """The user's most recent searches, newest first."""
        return list(
            db.execute(
                select(ProspectSearch)
                .where(ProspectSearch.user_id == user_id)
                .order_by(ProspectSearch.id.desc())
                .limit(_RECENT_SEARCHES_LIMIT)
            ).scalars()
        )

    def get_for_user(self, db: Session, user_id: int, search_id: int) -> ProspectSearch | None:
        """The user's search, or ``None``."""
        search = db.get(ProspectSearch, search_id)
        return search if search is not None and search.user_id == user_id else None

    def candidates_of(self, db: Session, search: ProspectSearch) -> list[ProspectSearchCandidate]:
        """Every candidate a search looked at, in the order it met them."""
        return list(
            db.execute(
                select(ProspectSearchCandidate)
                .where(ProspectSearchCandidate.search_id == search.id)
                .order_by(ProspectSearchCandidate.id)
            ).scalars()
        )

    def trade_counts(self, db: Session, searches: list[ProspectSearch]) -> dict[int, list[SearchTradeCounts]]:
        """
        Count the candidates of several searches by trade and status, in one query.

        Args:
            db: Active database session.
            searches: The searches to count.

        Returns:
            For each search id, one line per searched trade.
        """
        counted: dict[tuple[int, str, str], int] = {}
        if searches:
            rows = db.execute(
                select(
                    ProspectSearchCandidate.search_id,
                    ProspectSearchCandidate.trade,
                    ProspectSearchCandidate.status,
                    func.count(ProspectSearchCandidate.id),
                )
                .where(ProspectSearchCandidate.search_id.in_([search.id for search in searches]))
                .group_by(
                    ProspectSearchCandidate.search_id, ProspectSearchCandidate.trade, ProspectSearchCandidate.status
                )
            ).all()
            counted = {(search_id, trade, status): total for search_id, trade, status, total in rows}

        counts_by_search: dict[int, list[SearchTradeCounts]] = {}
        for search in searches:
            trade_progress = (search.progress or {}).get("trades", {})
            lines: list[SearchTradeCounts] = []
            for typed_trade in search.trades:
                profile = TradeCatalog.resolve(typed_trade)
                progress = trade_progress.get(profile.key, {})
                by_status = {
                    status: counted.get((search.id, profile.key, status.value), 0) for status in CandidateStatus
                }
                lines.append(
                    SearchTradeCounts(
                        trade=profile.key,
                        label=profile.label,
                        wanted=search.count_per_trade,
                        kept=by_status[CandidateStatus.KEPT],
                        set_aside=by_status[CandidateStatus.SET_ASIDE],
                        to_confirm=by_status[CandidateStatus.TO_CONFIRM],
                        waiting_browser=by_status[CandidateStatus.NEEDS_BROWSER],
                        rejected=by_status[CandidateStatus.REJECTED],
                        unverified=by_status[CandidateStatus.DISCOVERED],
                        towns=list(progress.get("towns", [])),
                        stop_reason=progress.get("stop_reason"),
                    )
                )
            counts_by_search[search.id] = lines
        return counts_by_search

    def cancel(self, db: Session, user_id: int, search_id: int) -> ProspectSearch | None:
        """Stop a search; what it found is kept. ``None`` when it is not the user's."""
        search = self.get_for_user(db, user_id, search_id)
        if search is None:
            return None
        if search.status in (*_ACTIVE_STATUSES, ProspectSearchStatus.WAITING_BROWSER.value):
            search.status = ProspectSearchStatus.CANCELLED.value
            search.completed_at = naive_utc_now()
            db.commit()
            db.refresh(search)
        return search

    def resume(self, db: Session, user_id: int, search_id: int) -> ProspectSearch | None:
        """
        Carry on a search that stopped short (cancelled, failed, or towns left to scan).

        A search that had ended gets the request budget and the town limit of one more run;
        one still running or waiting for a browser is only started again.

        Returns:
            The search, running again, or ``None`` when it is not the user's.
        """
        search = self.get_for_user(db, user_id, search_id)
        if search is None:
            return None
        if search.status not in _ACTIVE_STATUSES:
            if search.status != ProspectSearchStatus.WAITING_BROWSER.value:
                progress = dict(search.progress or {})
                progress["resume_count"] = int(progress.get("resume_count", 0)) + 1
                search.progress = progress
            search.status = ProspectSearchStatus.PENDING.value
            search.completed_at = None
            db.commit()
            db.refresh(search)
        self.start(search.id)
        return search

    def browser_tasks(self, db: Session, user_id: int, search_id: int) -> list[ProspectSearchCandidate] | None:
        """Candidates whose Facebook page a browser must read, or ``None`` when the search is not the user's."""
        search = self.get_for_user(db, user_id, search_id)
        if search is None:
            return None
        return list(
            db.execute(
                select(ProspectSearchCandidate)
                .where(
                    ProspectSearchCandidate.search_id == search.id,
                    ProspectSearchCandidate.status == CandidateStatus.NEEDS_BROWSER.value,
                    ProspectSearchCandidate.facebook_url.is_not(None),
                )
                .order_by(ProspectSearchCandidate.id)
            ).scalars()
        )

    async def record_facebook_contact(
        self, user_id: int, search_id: int, candidate_id: int, read: FacebookContactRead
    ) -> ProspectSearchCandidate | None:
        """
        Apply what a browser read on a candidate's Facebook page.

        Opens its own short database sessions: the read is followed by network checks,
        and a request-long session would hold a pooled connection across them.

        Args:
            user_id: Owner of the search.
            search_id: The search the candidate belongs to.
            candidate_id: The candidate whose page was read.
            read: What the browser found.

        Returns:
            The updated candidate, or ``None`` when it is not the user's.
        """
        with SessionLocal() as db:
            candidate = self._owned_candidate(db, user_id, search_id, candidate_id)
            if candidate is None:
                return None
        await facebook_contact_recorder.record(candidate_id, read)
        with SessionLocal() as db:
            candidate = db.get(ProspectSearchCandidate, candidate_id)
            self._carry_on_after_browser_round(db, search_id)
        return candidate

    async def keep_candidate(
        self, db: Session, user_id: int, search_id: int, candidate_id: int
    ) -> ProspectSearchCandidate | None:
        """
        Keep a candidate by hand and create its prospect.

        Raises:
            ProspectSearchError: The business is already one of the user's prospects (the candidate
                is then discarded as already known).
        """
        candidate = self._owned_candidate(db, user_id, search_id, candidate_id)
        if candidate is None:
            return None
        if candidate.reject_reason in _KNOWN_BUSINESS_REASONS:
            raise ProspectSearchError(_ALREADY_A_PROSPECT)
        facts = CandidateStore.facts_of(candidate)
        CandidateStore.write_back(candidate, facts, CandidateVerdict(CandidateStatus.KEPT, detail="Gardé à la main."))
        db.commit()
        prospect_id = await CandidateStore.promote(
            db,
            candidate,
            facts,
            TradeCatalog.resolve(candidate.trade),
            organization_id=organization_service.user_org_id(db, user_id),
        )
        db.refresh(candidate)
        self._carry_on_after_browser_round(db, search_id)
        if prospect_id is None:
            raise ProspectSearchError(_ALREADY_A_PROSPECT)
        return candidate

    def reject_candidate(
        self, db: Session, user_id: int, search_id: int, candidate_id: int
    ) -> ProspectSearchCandidate | None:
        """
        Discard a candidate by hand, so no later search proposes it again.

        Raises:
            ProspectSearchError: The candidate already became a prospect (delete the prospect instead).
        """
        candidate = self._owned_candidate(db, user_id, search_id, candidate_id)
        if candidate is None:
            return None
        if candidate.prospect_id is not None:
            raise ProspectSearchError("Ce candidat est déjà un prospect : supprimez-le depuis vos prospects.")
        facts = CandidateStore.facts_of(candidate)
        CandidateStore.write_back(
            candidate,
            facts,
            CandidateVerdict(CandidateStatus.REJECTED, CandidateRejectReason.MANUAL, "Écarté à la main."),
        )
        db.commit()
        db.refresh(candidate)
        self._carry_on_after_browser_round(db, search_id)
        return candidate

    def resume_interrupted(self) -> None:
        """Restart the searches a deployment or a crash stopped mid-run (called once at startup)."""
        with SessionLocal() as db:
            interrupted = list(
                db.execute(select(ProspectSearch.id).where(ProspectSearch.status.in_(_ACTIVE_STATUSES))).scalars()
            )
        for search_id in interrupted:
            logger.info("Prospect search %s was interrupted — resuming", search_id)
            self.start(search_id)

    def _carry_on_after_browser_round(self, db: Session, search_id: int) -> None:
        """
        Start a search waiting for a browser again once none of its candidates is left to read.

        The run then carries on (more towns if the count is not met) or ends.
        """
        search = db.get(ProspectSearch, search_id)
        if search is None or search.status != ProspectSearchStatus.WAITING_BROWSER.value:
            return
        waiting_candidate_count = db.execute(
            select(func.count(ProspectSearchCandidate.id)).where(
                ProspectSearchCandidate.search_id == search_id,
                ProspectSearchCandidate.status == CandidateStatus.NEEDS_BROWSER.value,
            )
        ).scalar()
        if not waiting_candidate_count:
            self.start(search_id)

    def _owned_candidate(
        self, db: Session, user_id: int, search_id: int, candidate_id: int
    ) -> ProspectSearchCandidate | None:
        """A candidate of the user's search, or ``None``."""
        candidate = db.get(ProspectSearchCandidate, candidate_id)
        if candidate is None or candidate.user_id != user_id or candidate.search_id != search_id:
            return None
        return candidate


prospect_search_service = ProspectSearchService()
