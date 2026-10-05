"""
Prospect search service — creates, starts, reads and corrects objective-driven searches.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import InstrumentedAttribute, Session, defer

from core.clock import naive_utc_now
from core.database import SessionLocal
from enums.prospect_search import CandidateRejectReason, CandidateStatus, ProspectSearchStatus
from models.prospect_search import ProspectSearch
from models.prospect_search_candidate import ProspectSearchCandidate
from schemas.prospect_search import (
    CandidateDecisions,
    CandidateDecisionsOutcome,
    ProspectSearchCreate,
    RefusedCandidateDecision,
    SearchTradeCounts,
)
from services.country_profiles import CountryProfiles
from services.organization_service import organization_service
from services.prospect_search.candidate_decision import CandidateDecision, CandidateVerdict, SearchCriteria
from services.prospect_search.candidate_store import CandidateStore
from services.prospect_search.facebook_contact import FacebookContactRead, facebook_contact_recorder
from services.prospect_search.runner import ProspectSearchRunner
from services.prospect_search.trade_catalog import TradeCatalog

logger = logging.getLogger(__name__)

_RECENT_SEARCHES_LIMIT: int = 30
_PENDING_CANDIDATES_LIMIT: int = 300
_MAXIMUM_QUEUED_SEARCHES: int = 5
_ACTIVE_STATUSES: tuple[str, ...] = (ProspectSearchStatus.PENDING.value, ProspectSearchStatus.RUNNING.value)
_UNFINISHED_STATUSES: tuple[str, ...] = (*_ACTIVE_STATUSES, ProspectSearchStatus.WAITING_BROWSER.value)
_CANCELLABLE_STATUSES: tuple[str, ...] = (*_UNFINISHED_STATUSES, ProspectSearchStatus.QUEUED.value)
# A queued search is touched once, as it enters the queue: its last update is the moment it got in line.
_QUEUE_ORDER: tuple[InstrumentedAttribute[Any], ...] = (ProspectSearch.updated_at, ProspectSearch.id)
_QUEUE_FULL: str = (
    f"La file d'attente est pleine : {_MAXIMUM_QUEUED_SEARCHES} recherches attendent déjà. "
    "Retirez-en une, ou attendez la fin de la recherche en cours."
)
_KNOWN_BUSINESS_REASONS: tuple[str, ...] = (
    CandidateRejectReason.ALREADY_KNOWN.value,
    CandidateRejectReason.DO_NOT_CONTACT.value,
)
_PLACES_AN_ACCEPTANCE_KEEPS: tuple[str, ...] = (CandidateStatus.KEPT.value, CandidateStatus.SET_ASIDE.value)
_ALREADY_A_PROSPECT: str = "Cette entreprise est déjà dans vos prospects."
_PROSPECT_NOT_CREATED: str = "Le prospect n'a pas pu être créé. Réessayez dans un instant."
_REFUSAL_NOT_SAVED: str = "Le refus n'a pas pu être enregistré. Réessayez dans un instant."
_CANDIDATE_NOT_FOUND: str = "Ce candidat est introuvable."
_NOT_REFUSED_BY_THE_USER: str = "Seuls les candidats que vous avez refusés peuvent être remis en attente."
_CANDIDATE_ALREADY_A_PROSPECT: str = "Ce candidat est déjà un prospect."


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
            The stored search, still pending (call :meth:`start_or_queue` to run it).

        Raises:
            ProspectSearchError: No usable trade, a country the prospection is not open to, or a full queue.
        """
        if self._has_search_at_work(db, user_id) and self._queued_count(db, user_id) >= _MAXIMUM_QUEUED_SEARCHES:
            raise ProspectSearchError(_QUEUE_FULL)
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
            validation_mode=payload.validation_mode.value,
            status=ProspectSearchStatus.PENDING.value,
            progress={},
            journal=[],
        )
        db.add(search)
        db.commit()
        db.refresh(search)
        return search

    def start_or_queue(self, db: Session, search: ProspectSearch) -> None:
        """
        Run a search now, or queue it behind the user's search at work.

        One search of a user works on the server at a time, the next ones wait their turn, oldest
        first: a search started after another one skips the towns that one scanned, so the two do
        not pay twice for the same pages, nor propose the same businesses.

        Args:
            db: Active database session.
            search: The search to run, pending, cancelled, failed or waiting for a browser.
        """
        has_search_at_work = self._has_search_at_work(db, search.user_id, other_than=search.id)
        if has_search_at_work or self._queued_count(db, search.user_id) > 0:
            search.status = ProspectSearchStatus.QUEUED.value
            search.completed_at = None
            db.commit()
            if not has_search_at_work:
                self.start_next_queued(search.user_id)
            db.refresh(search)
            return
        if search.status != ProspectSearchStatus.PENDING.value:
            search.status = ProspectSearchStatus.PENDING.value
            search.completed_at = None
            db.commit()
            db.refresh(search)
        self.start(search.id)

    def start(self, search_id: int) -> None:
        """Run a search in the background, then its user's next queued one; a search already running is left alone."""
        running = self._tasks.get(search_id)
        if running is not None and not running.done():
            return
        task = asyncio.create_task(self._run_then_start_the_next(search_id))
        self._tasks[search_id] = task
        task.add_done_callback(functools.partial(self._forget_finished_run, search_id))

    async def _run_then_start_the_next(self, search_id: int) -> None:
        """Run a search to its end, then hand the server over to the next search its user queued."""
        await ProspectSearchRunner(search_id).run()
        try:
            with SessionLocal() as db:
                user_id = db.execute(select(ProspectSearch.user_id).where(ProspectSearch.id == search_id)).scalar()
            if user_id is not None:
                self.start_next_queued(user_id)
        except Exception as exc:
            logger.error("Prospect search %s: starting the next queued search failed: %s", search_id, exc)

    def start_next_queued(self, user_id: int) -> None:
        """Start the search the user queued first, unless another search of the user is at work on the server."""
        with SessionLocal() as db:
            if self._has_search_at_work(db, user_id):
                return
            next_search = db.execute(
                select(ProspectSearch)
                .where(ProspectSearch.user_id == user_id, ProspectSearch.status == ProspectSearchStatus.QUEUED.value)
                .order_by(*_QUEUE_ORDER)
                .limit(1)
            ).scalar()
            if next_search is None:
                return
            next_search.status = ProspectSearchStatus.PENDING.value
            db.commit()
            next_search_id = next_search.id
        self.start(next_search_id)

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

    def pending_candidates(self, db: Session, user_id: int) -> list[ProspectSearchCandidate]:
        """The user's candidates waiting for a decision, every search together, newest first."""
        return list(
            db.execute(
                select(ProspectSearchCandidate)
                .where(ProspectSearchCandidate.user_id == user_id, ProspectSearchCandidate.is_pending)
                .order_by(ProspectSearchCandidate.id.desc())
                .limit(_PENDING_CANDIDATES_LIMIT)
            ).scalars()
        )

    def pending_candidate_count(self, db: Session, user_id: int) -> int:
        """How many of the user's candidates wait for a decision, every search together."""
        return (
            db.execute(
                select(func.count(ProspectSearchCandidate.id)).where(
                    ProspectSearchCandidate.user_id == user_id, ProspectSearchCandidate.is_pending
                )
            ).scalar()
            or 0
        )

    def active_search(self, db: Session, user_id: int) -> ProspectSearch | None:
        """
        The user's search at work: the one the server runs, else the latest one waiting for a browser.

        Read without its journal, which the activity does not show. A queued search is not at work yet.
        """
        for statuses in (_ACTIVE_STATUSES, (ProspectSearchStatus.WAITING_BROWSER.value,)):
            search = db.execute(
                select(ProspectSearch)
                .options(defer(ProspectSearch.journal))
                .where(ProspectSearch.user_id == user_id, ProspectSearch.status.in_(statuses))
                .order_by(ProspectSearch.id.desc())
                .limit(1)
            ).scalar()
            if search is not None:
                return search
        return None

    def queued_searches(self, db: Session, user_id: int) -> list[ProspectSearch]:
        """The user's searches waiting for their turn, in the order they will run, without their journal."""
        return list(
            db.execute(
                select(ProspectSearch)
                .options(defer(ProspectSearch.journal))
                .where(ProspectSearch.user_id == user_id, ProspectSearch.status == ProspectSearchStatus.QUEUED.value)
                .order_by(*_QUEUE_ORDER)
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
        """
        Stop a search, or take it out of the queue; what it found is kept. ``None`` when it is not the user's.

        The next queued search starts once the stopped run has ended.
        """
        search = self.get_for_user(db, user_id, search_id)
        if search is None:
            return None
        if search.status in _CANCELLABLE_STATUSES:
            search.status = ProspectSearchStatus.CANCELLED.value
            search.completed_at = naive_utc_now()
            db.commit()
            db.refresh(search)
        return search

    def resume(self, db: Session, user_id: int, search_id: int) -> ProspectSearch | None:
        """
        Carry on a search that stopped short (cancelled, failed, or towns left to scan).

        A search that had ended gets the request budget and the town limit of one more run;
        one waiting for a browser is only started again, and one still at work is left running.
        Behind another search at work, it waits its turn in the queue.

        Returns:
            The search, running again or queued, or ``None`` when it is not the user's.

        Raises:
            ProspectSearchError: It would have to wait in a queue that is full.
        """
        search = self.get_for_user(db, user_id, search_id)
        if search is None:
            return None
        if search.status in _ACTIVE_STATUSES:
            self.start(search.id)
            return search
        if search.status == ProspectSearchStatus.QUEUED.value:
            return search
        if (
            self._has_search_at_work(db, user_id, other_than=search.id)
            and self._queued_count(db, user_id) >= _MAXIMUM_QUEUED_SEARCHES
        ):
            raise ProspectSearchError(_QUEUE_FULL)
        if search.status != ProspectSearchStatus.WAITING_BROWSER.value:
            progress = dict(search.progress or {})
            progress["resume_count"] = int(progress.get("resume_count", 0)) + 1
            search.progress = progress
        self.start_or_queue(db, search)
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
        Accept a candidate: it becomes a prospect.

        A candidate the search kept or set aside keeps that place; any other is kept by hand.

        Raises:
            ProspectSearchError: The business is already one of the user's prospects (the candidate
                is then discarded as already known), or its prospect could not be created.
        """
        candidate = self._owned_candidate(db, user_id, search_id, candidate_id)
        if candidate is None:
            return None
        self._place_as_accepted(db, candidate)
        await CandidateStore.promote_accepted(
            db, [candidate], organization_id=organization_service.user_org_id(db, user_id)
        )
        db.refresh(candidate)
        self._carry_on_after_browser_round(db, search_id)
        refusal = self._acceptance_refusal(candidate)
        if refusal is not None:
            raise ProspectSearchError(refusal)
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
        self._discard_by_hand(db, candidate)
        db.refresh(candidate)
        self._carry_on_after_browser_round(db, search_id)
        return candidate

    def restore_candidate(
        self, db: Session, user_id: int, search_id: int, candidate_id: int
    ) -> ProspectSearchCandidate | None:
        """
        Undo the user's refusal of a candidate: it waits for a decision again, without becoming a prospect.

        A lead refused while it waited for that decision gets back the place it had, with its detail: a
        lead the search could not verify comes back to check, never complete. A candidate refused without
        a kept place (refused before it was placed, or before the place was kept) has its place decided
        again from what its search stored and with the search's criteria, its checks and its Facebook read
        taken as done; a place the rules discard then becomes « à confirmer ». No prospect is created, even
        in an automatic search.

        Raises:
            ProspectSearchError: The candidate was not refused by the user, or it is a prospect already.
        """
        candidate = self._owned_candidate(db, user_id, search_id, candidate_id)
        search = self.get_for_user(db, user_id, search_id)
        if candidate is None or search is None:
            return None
        is_refused_by_hand = (
            candidate.status == CandidateStatus.REJECTED.value
            and candidate.reject_reason == CandidateRejectReason.MANUAL.value
        )
        if not is_refused_by_hand:
            raise ProspectSearchError(_NOT_REFUSED_BY_THE_USER)
        if candidate.prospect_id is not None:
            raise ProspectSearchError(_CANDIDATE_ALREADY_A_PROSPECT)

        facts = CandidateStore.facts_of(candidate)
        if candidate.status_before_refusal is not None:
            verdict = CandidateVerdict(
                CandidateStatus(candidate.status_before_refusal), detail=candidate.detail_before_refusal
            )
        else:
            facts.is_verified = True
            facts.is_facebook_page_read = True
            verdict = CandidateDecision.decide(
                facts, TradeCatalog.resolve(candidate.trade), SearchCriteria.of_search(search)
            )
            if verdict.status == CandidateStatus.REJECTED:
                verdict = CandidateVerdict(CandidateStatus.TO_CONFIRM, detail="Remis à valider à la main.")
        CandidateStore.write_back(candidate, facts, verdict)
        candidate.status_before_refusal = None
        candidate.detail_before_refusal = None
        db.commit()
        db.refresh(candidate)
        self._carry_on_after_browser_round(db, search_id)
        return candidate

    async def decide_candidates(
        self, db: Session, user_id: int, decisions: CandidateDecisions
    ) -> CandidateDecisionsOutcome:
        """
        Apply several decisions of the user at once.

        Each one follows the rules of :meth:`keep_candidate` and :meth:`reject_candidate`. A decision
        that cannot be applied, for a rule or an unexpected failure, does not stop the others: it is
        rolled back and returned with its reason. The user's prospects are read once per search, not
        once per accepted candidate. The searches waiting for a browser that the decisions concern
        carry on whatever happens.

        Args:
            db: Active database session.
            user_id: The user deciding; candidates of another user are reported as not found.
            decisions: The candidates to accept and the ones to refuse, from any of the user's searches.

        Returns:
            How many candidates became prospects, how many were discarded, and the decisions not applied.
        """
        ids_to_accept = list(dict.fromkeys(decisions.accept))
        ids_to_reject = list(dict.fromkeys(decisions.reject))
        candidate_by_id = {
            candidate.id: candidate
            for candidate in db.execute(
                select(ProspectSearchCandidate).where(
                    ProspectSearchCandidate.user_id == user_id,
                    ProspectSearchCandidate.id.in_([*ids_to_accept, *ids_to_reject]),
                )
            ).scalars()
        }
        search_id_by_candidate_id = {
            candidate_id: candidate.search_id for candidate_id, candidate in candidate_by_id.items()
        }
        organization_id = organization_service.user_org_id(db, user_id)
        outcome = CandidateDecisionsOutcome(accepted=0, rejected=0)

        def report_not_applied(candidate_id: int, detail: str) -> None:
            outcome.refused.append(RefusedCandidateDecision(candidate_id=candidate_id, detail=detail))

        try:
            for candidate_id in ids_to_reject:
                candidate = candidate_by_id.get(candidate_id)
                if candidate is None:
                    report_not_applied(candidate_id, _CANDIDATE_NOT_FOUND)
                    continue
                try:
                    self._discard_by_hand(db, candidate)
                except ProspectSearchError as exc:
                    report_not_applied(candidate_id, str(exc))
                except Exception as exc:
                    db.rollback()
                    logger.error("Prospect search: refusing candidate %s failed: %s", candidate_id, exc, exc_info=True)
                    report_not_applied(candidate_id, _REFUSAL_NOT_SAVED)
                else:
                    outcome.rejected += 1

            accepted_ids_by_search: dict[int, list[int]] = {}
            for candidate_id in ids_to_accept:
                candidate = candidate_by_id.get(candidate_id)
                if candidate is None:
                    report_not_applied(candidate_id, _CANDIDATE_NOT_FOUND)
                    continue
                try:
                    self._place_as_accepted(db, candidate)
                except ProspectSearchError as exc:
                    report_not_applied(candidate_id, str(exc))
                except Exception as exc:
                    db.rollback()
                    logger.error("Prospect search: accepting candidate %s failed: %s", candidate_id, exc, exc_info=True)
                    report_not_applied(candidate_id, _PROSPECT_NOT_CREATED)
                else:
                    accepted_ids_by_search.setdefault(search_id_by_candidate_id[candidate_id], []).append(candidate_id)

            for candidate_ids in accepted_ids_by_search.values():
                refusal_by_candidate_id = await self._promote_accepted_together(
                    db, {candidate_id: candidate_by_id[candidate_id] for candidate_id in candidate_ids}, organization_id
                )
                for candidate_id, refusal in refusal_by_candidate_id.items():
                    if refusal is None:
                        outcome.accepted += 1
                    else:
                        report_not_applied(candidate_id, refusal)
        finally:
            for search_id in set(search_id_by_candidate_id.values()):
                try:
                    self._carry_on_after_browser_round(db, search_id)
                except Exception as exc:
                    db.rollback()
                    logger.error("Prospect search %s: carrying on after the decisions failed: %s", search_id, exc)
        return outcome

    def resume_interrupted(self) -> None:
        """Restart the searches a deployment or a crash stopped mid-run, then the queues left without a run (startup)."""
        with SessionLocal() as db:
            interrupted = list(
                db.execute(select(ProspectSearch.id).where(ProspectSearch.status.in_(_ACTIVE_STATUSES))).scalars()
            )
            users_with_a_queue = list(
                db.execute(
                    select(ProspectSearch.user_id)
                    .where(ProspectSearch.status == ProspectSearchStatus.QUEUED.value)
                    .distinct()
                ).scalars()
            )
        for search_id in interrupted:
            logger.info("Prospect search %s was interrupted — resuming", search_id)
            self.start(search_id)
        for user_id in users_with_a_queue:
            self.start_next_queued(user_id)

    async def _promote_accepted_together(
        self, db: Session, candidate_by_id: dict[int, ProspectSearchCandidate], organization_id: int | None
    ) -> dict[int, str | None]:
        """
        Create the prospects of accepted candidates of one search, whatever fails on the way.

        Args:
            db: Active database session.
            candidate_by_id: The accepted candidates of the search, placed already.
            organization_id: The user's organization, the prospects are shared with it.

        Returns:
            For each candidate id, why it is not a prospect in the user's words, ``None`` when it is one.
        """
        try:
            await CandidateStore.promote_accepted(db, list(candidate_by_id.values()), organization_id=organization_id)
        except Exception as exc:
            db.rollback()
            logger.error(
                "Prospect search: accepting candidates %s failed: %s", list(candidate_by_id), exc, exc_info=True
            )
        refusal_by_candidate_id: dict[int, str | None] = {}
        for candidate_id, candidate in candidate_by_id.items():
            try:
                refusal_by_candidate_id[candidate_id] = self._acceptance_refusal(candidate)
            except Exception as exc:
                db.rollback()
                logger.error("Prospect search: accepted candidate %s could not be read again: %s", candidate_id, exc)
                refusal_by_candidate_id[candidate_id] = _PROSPECT_NOT_CREATED
        return refusal_by_candidate_id

    def _place_as_accepted(self, db: Session, candidate: ProspectSearchCandidate) -> None:
        """
        Give an accepted candidate the place its prospect is created from.

        Raises:
            ProspectSearchError: The search discarded it because its business is a prospect already.
        """
        if candidate.reject_reason in _KNOWN_BUSINESS_REASONS:
            raise ProspectSearchError(_ALREADY_A_PROSPECT)
        if candidate.status in _PLACES_AN_ACCEPTANCE_KEEPS:
            return
        CandidateStore.write_back(
            candidate,
            CandidateStore.facts_of(candidate),
            CandidateVerdict(CandidateStatus.KEPT, detail="Gardé à la main."),
        )
        db.commit()

    @staticmethod
    def _acceptance_refusal(candidate: ProspectSearchCandidate) -> str | None:
        """Why an accepted candidate did not become a prospect, in the user's words; ``None`` when it did."""
        if candidate.status == CandidateStatus.REJECTED.value:
            return _ALREADY_A_PROSPECT
        if candidate.prospect_id is None:
            return _PROSPECT_NOT_CREATED
        return None

    def _discard_by_hand(self, db: Session, candidate: ProspectSearchCandidate) -> None:
        """
        Discard a candidate on the user's decision.

        A lead waiting for that decision keeps its place aside, for :meth:`restore_candidate`; a lead
        refused again keeps the place it had before the first refusal.

        Raises:
            ProspectSearchError: The candidate already became a prospect.
        """
        if candidate.prospect_id is not None:
            raise ProspectSearchError("Ce candidat est déjà un prospect : supprimez-le depuis vos prospects.")
        place_before_refusal = (
            (candidate.status, candidate.reject_detail)
            if candidate.is_pending
            else (candidate.status_before_refusal, candidate.detail_before_refusal)
        )
        CandidateStore.write_back(
            candidate,
            CandidateStore.facts_of(candidate),
            CandidateVerdict(CandidateStatus.REJECTED, CandidateRejectReason.MANUAL, "Écarté à la main."),
        )
        candidate.status_before_refusal, candidate.detail_before_refusal = place_before_refusal
        db.commit()

    def _carry_on_after_browser_round(self, db: Session, search_id: int) -> None:
        """
        Start a search waiting for a browser again once none of its candidates is left to read.

        The run then carries on (more towns if the count is not met) or ends; behind another search
        of the user at work, it waits its turn in the queue.
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
            self.start_or_queue(db, search)

    @staticmethod
    def _has_search_at_work(db: Session, user_id: int, *, other_than: int | None = None) -> bool:
        """Whether the server runs a search of the user, or is about to, other than the one given."""
        query = select(func.count(ProspectSearch.id)).where(
            ProspectSearch.user_id == user_id, ProspectSearch.status.in_(_ACTIVE_STATUSES)
        )
        if other_than is not None:
            query = query.where(ProspectSearch.id != other_than)
        return bool(db.execute(query).scalar())

    @staticmethod
    def _queued_count(db: Session, user_id: int) -> int:
        """How many searches of the user wait their turn."""
        return (
            db.execute(
                select(func.count(ProspectSearch.id)).where(
                    ProspectSearch.user_id == user_id, ProspectSearch.status == ProspectSearchStatus.QUEUED.value
                )
            ).scalar()
            or 0
        )

    def _owned_candidate(
        self, db: Session, user_id: int, search_id: int, candidate_id: int
    ) -> ProspectSearchCandidate | None:
        """A candidate of the user's search, or ``None``."""
        candidate = db.get(ProspectSearchCandidate, candidate_id)
        if candidate is None or candidate.user_id != user_id or candidate.search_id != search_id:
            return None
        return candidate


prospect_search_service = ProspectSearchService()
