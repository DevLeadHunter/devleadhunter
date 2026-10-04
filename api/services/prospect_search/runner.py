"""
Prospect search runner — walks a search from its objective to verified prospects.

For each trade: go town by town; in each town read the public registries that carry
an email, then Google's local results page by page, then the Facebook pages a search
engine knows. Every business seen becomes a candidate, is recognised if it is already
known, verified with one web search, completed with a contact, and placed: kept, set
aside, to confirm, waiting for a browser, or discarded with a reason.

The run stops when every trade has its count, when the towns or the request budget
run out, or when the user cancels. It never holds a database session across a
network call, and everything it knows is stored, so a search interrupted by a
deployment resumes where it stopped.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.config import settings
from core.database import SessionLocal
from enums.country import search_label
from enums.prospect_search import (
    CandidateOrigin,
    CandidateRejectReason,
    CandidateStatus,
    EmailProofLevel,
    ProspectSearchChannel,
    ProspectSearchStatus,
)
from models.prospect_search import ProspectSearch
from models.prospect_search_candidate import ProspectSearchCandidate
from scrappers.brightdata_client import BrightDataClient
from scrappers.facebook_enrichment_scraper import facebook_enrichment_scraper
from scrappers.google_local_results import GoogleLocalResultsParser, LocalListing
from services.decision_maker.normalize import fold
from services.organization_service import organization_service
from services.prospect_search.business_name import BusinessName
from services.prospect_search.candidate_decision import CandidateDecision, CandidateVerdict, SearchCriteria
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_identity import KnownBusinessIndex
from services.prospect_search.candidate_store import CandidateStore
from services.prospect_search.candidate_verifier import CandidateVerifier
from services.prospect_search.contact_finder import ContactFinder
from services.prospect_search.facebook_contact import FacebookContactRead, facebook_contact_recorder
from services.prospect_search.facebook_page_results import FacebookPageResults
from services.prospect_search.registry_sources import RegistryCompany, rbq_registry, rge_registry
from services.prospect_search.search_judge import search_judge
from services.prospect_search.search_zones import SearchZones
from services.prospect_search.trade_catalog import TradeCatalog, TradeProfile
from services.sms.phone_normalizer import format_phone_in_national_form

logger = logging.getLogger(__name__)

_CONCURRENT_CANDIDATES: int = 3
_LISTINGS_PER_PAGE: int = 20
_PAGES_FOR_MAIN_TERM: int = 3
_REGISTRY_COMPANIES_PER_TOWN: int = 30
_MAX_TOWNS_PER_TRADE: int = 12
_MAX_ROUNDS: int = 4
_JOURNAL_MAX_LINES: int = 150
_BASE_REQUEST_BUDGET: int = 60
_REQUEST_BUDGET_PER_PROSPECT: int = 45
# Past this share of the budget, a listing showing a website button is no longer worth a verification.
_WEBSITE_LISTING_BUDGET_SHARE: float = 0.7
# A candidate waiting for its Facebook page counts for half a prospect: about one page in two gives an email.
_WAITING_CANDIDATE_WEIGHT: float = 0.5


@dataclass
class _RunState:
    """What the runner reads once at start and keeps for the whole run."""

    user_id: int
    organization_id: int | None
    country: str
    trades: list[str]
    cities: list[str]
    count_per_trade: int
    criteria: SearchCriteria
    request_budget: int
    max_towns_per_trade: int
    spent_before: int
    judged_before: int
    scanned_before: dict[str, set[str]] = field(default_factory=dict)


class ProspectSearchRunner:
    """Runs one search to its end, or to the point where a browser must read Facebook pages."""

    def __init__(self, search_id: int) -> None:
        self._search_id = search_id
        self._client = BrightDataClient()
        self._verifier = CandidateVerifier(self._client, search_judge)
        self._contact_finder = ContactFinder(self._client, search_judge)
        self._gate = asyncio.Semaphore(_CONCURRENT_CANDIDATES)
        self._index = KnownBusinessIndex()
        self._seen_keys: set[str] = set()
        self._counts: dict[str, dict[str, int]] = {}
        self._progress: dict[str, Any] = {}
        self._new_journal_lines: list[dict[str, str]] = []
        self._unanswered_candidate_ids: list[int] = []
        self._retried_candidate_ids: set[int] = set()
        self._stored_request_count: int = 0
        self._stored_judge_call_count: int = 0

    async def run(self) -> None:
        """Run the search; an unexpected error ends it as failed, with what was found kept."""
        try:
            await self._run()
        except Exception as exc:
            logger.error("Prospect search %s failed: %s", self._search_id, exc, exc_info=True)
            self._log("La recherche s'est arrêtée sur une erreur. Ce qui a été trouvé est conservé.")
            self._flush(status=ProspectSearchStatus.FAILED, error_message=str(exc)[:500])

    async def _run(self) -> None:
        """The whole walk: trades, towns, pages, then the Facebook reads this process can do itself."""
        state = self._start()
        if state is None:
            return
        self._client.reload_credentials()
        if not self._client.is_configured:
            self._log("Bright Data n'est pas configuré : la recherche ne peut pas interroger Google.")
            self._flush(status=ProspectSearchStatus.FAILED, error_message="Bright Data non configuré")
            return

        profiles = [TradeCatalog.resolve(trade) for trade in state.trades]
        for _ in range(_MAX_ROUNDS):
            for profile in profiles:
                if self._is_cancelled():
                    break
                await self._fill_trade(state, profile)
            if self._is_cancelled():
                self._flush()
                return
            waiting_ids = self._waiting_candidate_ids()
            if not waiting_ids or not settings.prospect_search_local_browser:
                break
            if await self._read_facebook_pages(waiting_ids) == 0:
                break

        for profile in profiles:
            kept = self._count(profile.key, CandidateStatus.KEPT)
            self._log(f"{profile.label} : {kept} gardé(s) sur {state.count_per_trade} demandé(s).")
        is_waiting = bool(self._waiting_candidate_ids())
        if is_waiting:
            self._log("Des candidats attendent la lecture de leur page Facebook par l'application Windows.")
        self._flush(status=ProspectSearchStatus.WAITING_BROWSER if is_waiting else ProspectSearchStatus.COMPLETED)

    def _start(self) -> _RunState | None:
        """Load the search, mark it running and rebuild what an earlier run of it already knows."""
        with SessionLocal() as db:
            search = db.get(ProspectSearch, self._search_id)
            if search is None or search.status == ProspectSearchStatus.CANCELLED.value:
                return None
            search.status = ProspectSearchStatus.RUNNING.value
            search.started_at = search.started_at or naive_utc_now()
            search.error_message = None
            db.commit()

            organization_id = organization_service.user_org_id(db, search.user_id)
            self._progress = dict(search.progress or {})
            self._index = KnownBusinessIndex.load(
                db, user_id=search.user_id, organization_id=organization_id, search_id=search.id
            )
            scanned_before: dict[str, set[str]] = {}
            for row in db.execute(
                select(ProspectSearchCandidate).where(ProspectSearchCandidate.user_id == search.user_id)
            ).scalars():
                if row.search_id == search.id:
                    self._seen_keys.update(row.identity_keys or [])
                    self._add_count(row.trade, row.status, 1)
                elif row.searched_city:
                    scanned_before.setdefault(row.trade, set()).add(fold(row.searched_city))

            total_wanted = search.count_per_trade * max(len(search.trades), 1)
            # Each resume the user asks for grants the request budget and the town limit of one more run.
            granted_runs = 1 + int(self._progress.get("resume_count", 0))
            return _RunState(
                user_id=search.user_id,
                organization_id=organization_id,
                country=search.country,
                trades=list(search.trades),
                cities=list(search.cities or []),
                count_per_trade=search.count_per_trade,
                criteria=SearchCriteria(
                    channel=ProspectSearchChannel(search.channel),
                    only_without_website=search.only_without_website,
                    minimum_rating=search.minimum_rating,
                ),
                request_budget=(_BASE_REQUEST_BUDGET + _REQUEST_BUDGET_PER_PROSPECT * total_wanted) * granted_runs,
                max_towns_per_trade=_MAX_TOWNS_PER_TRADE * granted_runs,
                spent_before=search.request_count,
                judged_before=search.judge_call_count,
                scanned_before=scanned_before,
            )

    async def _fill_trade(self, state: _RunState, profile: TradeProfile) -> None:
        """Go through the towns until the trade has its count, the towns run out or the budget is spent."""
        trade_progress = self._progress.setdefault("trades", {}).setdefault(
            profile.key, {"towns": [], "stop_reason": None}
        )
        await self._verify_and_place_candidates(state, profile, self._discovered_candidate_ids(state, profile.key))

        towns = SearchZones.plan(
            country=state.country,
            asked_cities=state.cities,
            already_scanned=state.scanned_before.get(profile.key, set()),
            seed=self._search_id,
        )
        for town in towns:
            self._reload_counts()
            if self._is_filled(state, profile):
                trade_progress["stop_reason"] = None
                return
            if self._is_over_budget(state):
                trade_progress["stop_reason"] = "budget"
                return
            if self._is_cancelled():
                return
            if town in trade_progress["towns"]:
                continue
            if len(trade_progress["towns"]) >= state.max_towns_per_trade:
                break
            await self._scan_town(state, profile, town)
            trade_progress["towns"].append(town)
            self._flush()
        if not self._is_filled(state, profile):
            trade_progress["stop_reason"] = "towns"

    async def _scan_town(self, state: _RunState, profile: TradeProfile, town: str) -> None:
        """Read every source of one town for one trade, verifying candidates as they come."""
        self._log(f"{profile.label} · {town} : recherche en cours.")
        self._flush()
        companies = await self._registry_companies(state, profile, town)
        if companies:
            self._log(f"{profile.label} · {town} : {len(companies)} entreprise(s) avec email dans le registre public.")
            await self._verify_and_place_candidates(
                state, profile, self._store_registry_companies(state, profile, town, companies)
            )

        region = search_label(state.country)
        for term_position, term in enumerate(profile.terms_for(state.country)):
            page_count = _PAGES_FOR_MAIN_TERM if term_position == 0 else 1
            for page in range(page_count):
                if self._is_filled(state, profile) or self._is_over_budget(state) or self._is_cancelled():
                    return
                query = " ".join(part for part in (term, town, region) if part)
                listings = await self._local_listings(query, state.country, page)
                if not listings:
                    break
                candidate_ids = self._store_listings(state, profile, town, listings)
                without_site = sum(1 for listing in listings if listing.has_website_button is False)
                self._log(
                    f"{profile.label} · {town} : {len(listings)} fiches Google lues, "
                    f"{without_site} sans site déclaré, {len(candidate_ids)} à vérifier."
                )
                await self._verify_and_place_candidates(state, profile, candidate_ids)
                if len(listings) < _LISTINGS_PER_PAGE:
                    break

        if not (self._is_filled(state, profile) or self._is_over_budget(state) or self._is_cancelled()):
            candidate_ids = await self._store_facebook_pages(state, profile, town)
            if candidate_ids:
                self._log(f"{profile.label} · {town} : {len(candidate_ids)} page(s) Facebook à vérifier.")
                await self._verify_and_place_candidates(state, profile, candidate_ids)

    async def _local_listings(self, query: str, country: str, page: int) -> list[LocalListing]:
        """One page of Google local results: the HTML first, Bright Data's parsed JSON when it is not recognised."""
        start = page * _LISTINGS_PER_PAGE
        html = await self._client.google_local_html(query, country=country, start=start)
        listings = GoogleLocalResultsParser.parse_html(html, country=country) if html else []
        if listings:
            return listings
        parsed = await self._client.google_parsed(query, country=country, start=start, local=True)
        return GoogleLocalResultsParser.parse_snack_pack((parsed or {}).get("snack_pack") or [])

    async def _registry_companies(self, state: _RunState, profile: TradeProfile, town: str) -> list[RegistryCompany]:
        """Companies of the trade that a public registry lists with an email, for the search's country."""
        if state.country == "FR":
            return await rge_registry.companies_near(trade=profile, city=town, limit=_REGISTRY_COMPANIES_PER_TOWN)
        if state.country == "CA":
            return await rbq_registry.companies_in(trade=profile, city=town, limit=_REGISTRY_COMPANIES_PER_TOWN)
        return []

    def _store_registry_companies(
        self, state: _RunState, profile: TradeProfile, town: str, companies: list[RegistryCompany]
    ) -> list[int]:
        """Save registry companies as candidates; return the ones worth a verification."""
        to_verify: list[int] = []
        with SessionLocal() as db:
            for company in companies:
                facts = CandidateFacts(
                    name=company.name,
                    trade_key=profile.key,
                    country=state.country,
                    origin=company.origin.value,
                    city=company.city,
                    searched_city=town,
                    address=company.address,
                    phone=format_phone_in_national_form(company.phone, country=state.country) or company.phone,
                    owner_name=company.owner_name,
                    registry_number=company.registry_number,
                )
                facts.offer_email(
                    company.email, EmailProofLevel.PUBLISHED, source=company.source_label, url=company.source_url
                )
                candidate_id = self._store_candidate(db, state, facts, early_verdict=None)
                if candidate_id is not None:
                    to_verify.append(candidate_id)
            db.commit()
        return to_verify

    def _store_listings(
        self, state: _RunState, profile: TradeProfile, town: str, listings: list[LocalListing]
    ) -> list[int]:
        """
        Save a page of Google listings as candidates; return the ones worth a verification, best first.

        A listing left out because the budget runs low stays unverified: it is verified when the search is resumed.
        """
        leaves_website_listings_unverified = self._leaves_website_listings_unverified(state)
        to_verify: list[tuple[bool, int]] = []
        with SessionLocal() as db:
            for listing in listings:
                facts = CandidateFacts(
                    name=BusinessName.clean(listing.name),
                    trade_key=profile.key,
                    country=state.country,
                    origin=CandidateOrigin.GOOGLE_LOCAL.value,
                    city=listing.locality,
                    searched_city=town,
                    address=listing.address,
                    phone=listing.phone,
                    google_cid=listing.cid,
                    google_maps_url=listing.maps_url,
                    google_rating=listing.rating,
                    google_reviews_count=listing.reviews_count,
                    google_category=listing.category,
                    has_website_button=listing.has_website_button,
                    is_closed=listing.is_permanently_closed or listing.is_temporarily_closed,
                )
                early_verdict: CandidateVerdict | None = None
                if facts.is_closed or not profile.accepts_category(listing.category):
                    early_verdict = CandidateDecision.decide(facts, profile, state.criteria)
                candidate_id = self._store_candidate(db, state, facts, early_verdict=early_verdict)
                is_left_unverified = bool(listing.has_website_button) and leaves_website_listings_unverified
                if candidate_id is not None and not is_left_unverified:
                    to_verify.append((bool(listing.has_website_button), candidate_id))
            db.commit()
        return [candidate_id for _, candidate_id in sorted(to_verify)]

    async def _store_facebook_pages(self, state: _RunState, profile: TradeProfile, town: str) -> list[int]:
        """Save the business pages of the town that a search engine finds on Facebook."""
        term = profile.terms_for(state.country)[0]
        region = search_label(state.country)
        query = " ".join(part for part in (f'site:facebook.com "{term}" "{town}"', region) if part)
        page = await self._client.google_parsed(query, country=state.country)
        if page is None:
            return []
        to_verify: list[int] = []
        with SessionLocal() as db:
            for business_page in FacebookPageResults.business_pages(CandidateVerifier.result_lines(page), town=town):
                facts = CandidateFacts(
                    name=business_page.name,
                    trade_key=profile.key,
                    country=state.country,
                    origin=CandidateOrigin.FACEBOOK_SEARCH.value,
                    searched_city=town,
                    facebook_url=business_page.page_url,
                )
                facts.add_evidence(
                    "facebook", business_page.page_url, source="Recherche Facebook", url=business_page.result_link
                )
                candidate_id = self._store_candidate(db, state, facts, early_verdict=None)
                if candidate_id is not None:
                    to_verify.append(candidate_id)
            db.commit()
        return to_verify

    def _store_candidate(
        self, db: Session, state: _RunState, facts: CandidateFacts, *, early_verdict: CandidateVerdict | None
    ) -> int | None:
        """
        Save one candidate row.

        A business already seen by this search is skipped; one the user already knows, or
        one an early verdict discards, is saved as discarded without any paid request.

        Returns:
            The candidate id when it still has to be verified, else ``None``.
        """
        keys = CandidateStore.identity_keys(facts)
        if any(key in self._seen_keys for key in keys):
            return None
        self._seen_keys.update(keys)

        verdict = early_verdict
        known = self._index.match(keys)
        if known is not None:
            verdict = CandidateVerdict(CandidateStatus.REJECTED, known.reason, known.detail)

        row = ProspectSearchCandidate(
            search_id=self._search_id,
            user_id=state.user_id,
            trade=facts.trade_key,
            searched_city=facts.searched_city,
            origin=facts.origin,
            name=facts.name[:255],
            country=facts.country,
        )
        CandidateStore.write_back(row, facts, verdict or CandidateVerdict(CandidateStatus.DISCOVERED))
        row.prospect_id = known.prospect_id if known is not None else None
        db.add(row)
        db.flush()
        self._add_count(row.trade, row.status, 1)
        return row.id if verdict is None else None

    async def _verify_and_place_candidates(
        self, state: _RunState, profile: TradeProfile, candidate_ids: list[int]
    ) -> None:
        """
        Verify several candidates at once, then once more, one by one, those whose search did not answer.

        The ones not reached before the count is met stay for a later round.
        """
        if not candidate_ids:
            return
        await asyncio.gather(
            *(self._verify_and_place_candidate(state, profile, candidate_id) for candidate_id in candidate_ids)
        )
        unanswered, self._unanswered_candidate_ids = self._unanswered_candidate_ids, []
        for candidate_id in unanswered:
            self._retried_candidate_ids.add(candidate_id)
            await self._verify_and_place_candidate(state, profile, candidate_id)

    async def _verify_and_place_candidate(self, state: _RunState, profile: TradeProfile, candidate_id: int) -> None:
        """Verify one candidate, complete its contact and give it its place."""
        async with self._gate:
            if self._is_filled(state, profile) or self._is_over_budget(state) or self._is_cancelled():
                return
            with SessionLocal() as db:
                row = db.get(ProspectSearchCandidate, candidate_id)
                if row is None or row.status != CandidateStatus.DISCOVERED.value:
                    return
                facts = CandidateStore.facts_of(row)

            try:
                await self._verifier.verify(facts, profile)
                has_no_answer = not facts.is_verified and not facts.is_chain
                if has_no_answer and candidate_id not in self._retried_candidate_ids:
                    # Bright Data answers nothing now and then under load: one calmer retry settles it.
                    self._unanswered_candidate_ids.append(candidate_id)
                    return
                verdict = CandidateDecision.decide(facts, profile, state.criteria)
                is_final_rejection = (
                    verdict.status == CandidateStatus.REJECTED
                    and verdict.reject_reason != CandidateRejectReason.NO_CONTACT
                )
                if verdict.status == CandidateStatus.KEPT:
                    await self._contact_finder.drop_dead_email(facts)
                    verdict = CandidateDecision.decide(facts, profile, state.criteria)
                elif not is_final_rejection and facts.is_verified:
                    await self._contact_finder.find(facts, profile)
                    verdict = CandidateDecision.decide(facts, profile, state.criteria)
            except Exception as exc:
                logger.warning("Prospect search %s: candidate %s failed: %s", self._search_id, candidate_id, exc)
                verdict = CandidateVerdict(
                    CandidateStatus.TO_CONFIRM, detail="Une erreur a interrompu sa vérification : fiche non contrôlée."
                )
            # The verification reveals keys the listing did not carry (email, Facebook page, Google id):
            # a business already known under one of them must not become a second prospect.
            known = self._index.match(CandidateStore.identity_keys(facts))
            if known is not None and verdict.status != CandidateStatus.REJECTED:
                verdict = CandidateVerdict(CandidateStatus.REJECTED, known.reason, known.detail)
            await self._save(state, profile, candidate_id, facts, verdict)

    async def _save(
        self,
        state: _RunState,
        profile: TradeProfile,
        candidate_id: int,
        facts: CandidateFacts,
        verdict: CandidateVerdict,
    ) -> None:
        """
        Store a candidate's verdict and create its prospect when it is kept or set aside.

        The creation has the last word: a business that became a prospect meanwhile is discarded
        as already known, and a creation that fails leaves the candidate to the user.
        """
        with SessionLocal() as db:
            row = db.get(ProspectSearchCandidate, candidate_id)
            if row is None:
                return
            self._add_count(row.trade, row.status, -1)
            CandidateStore.write_back(row, facts, verdict)
            db.commit()
            await CandidateStore.promote_or_leave_to_confirm(
                db, row, facts, profile, organization_id=state.organization_id
            )
            if row.prospect_id is not None:
                self._index.remember_prospect(row.identity_keys or [], row.prospect_id)
            self._add_count(row.trade, row.status, 1)
            final_verdict = CandidateStore.verdict_of(row)
        self._log(self._journal_line(facts, final_verdict))
        # Written at once: the screen follows the search candidate by candidate, not town by town.
        self._flush()

    async def _read_facebook_pages(self, candidate_ids: list[int]) -> int:
        """
        Read the waiting Facebook pages with this process's own browser, one at a time.

        Returns:
            How many pages the browser read; a page it could not open leaves its candidate waiting.
        """
        self._log(f"Lecture de {len(candidate_ids)} page(s) Facebook sur ce poste.")
        self._flush()
        read_count = 0
        for candidate_id in candidate_ids:
            if self._is_cancelled():
                break
            with SessionLocal() as db:
                row = db.get(ProspectSearchCandidate, candidate_id)
                if row is None or not row.facebook_url:
                    continue
                name, facebook_url, country, trade_key = row.name, row.facebook_url, row.country, row.trade
            page = await facebook_enrichment_scraper.read_contact(
                business_name=name, facebook_url=facebook_url, country=country
            )
            if page is None:
                self._log(f"{name} : sa page Facebook n'a pas pu être lue sur ce poste, il reste en attente.")
                self._flush()
                continue
            read_count += 1
            verdict = await facebook_contact_recorder.record(
                candidate_id,
                FacebookContactRead(
                    is_readable=page.place_title is not None,
                    emails=list(page.emails),
                    phone=page.phone,
                    website=page.website,
                ),
            )
            if verdict is not None:
                self._add_count(trade_key, CandidateStatus.NEEDS_BROWSER.value, -1)
                self._add_count(trade_key, verdict.status.value, 1)
                self._log(f"{name} : page Facebook lue, {self._status_words(verdict.status)}.")
            self._flush()
        return read_count

    def _is_filled(self, state: _RunState, profile: TradeProfile) -> bool:
        """Whether the trade has its count, a waiting candidate counting for half a prospect."""
        kept = self._count(profile.key, CandidateStatus.KEPT)
        waiting = self._count(profile.key, CandidateStatus.NEEDS_BROWSER)
        return kept + waiting * _WAITING_CANDIDATE_WEIGHT >= state.count_per_trade

    def _spent(self, state: _RunState) -> int:
        """Paid requests spent by the search, earlier runs included."""
        return state.spent_before + self._client.request_count

    def _is_over_budget(self, state: _RunState) -> bool:
        """Whether the search has spent its request budget."""
        return self._spent(state) >= state.request_budget

    def _is_cancelled(self) -> bool:
        """Whether the user stopped the search."""
        with SessionLocal() as db:
            status = db.execute(select(ProspectSearch.status).where(ProspectSearch.id == self._search_id)).scalar()
        return status == ProspectSearchStatus.CANCELLED.value

    def _leaves_website_listings_unverified(self, state: _RunState) -> bool:
        """Whether the budget runs too low to verify the listings that show a website button."""
        is_budget_tight = self._spent(state) >= state.request_budget * _WEBSITE_LISTING_BUDGET_SHARE
        return state.criteria.only_without_website and is_budget_tight

    def _waiting_candidate_ids(self) -> list[int]:
        """Candidates of the search whose Facebook page is still to be read."""
        query = select(ProspectSearchCandidate.id).where(
            ProspectSearchCandidate.search_id == self._search_id,
            ProspectSearchCandidate.status == CandidateStatus.NEEDS_BROWSER.value,
        )
        with SessionLocal() as db:
            return list(db.execute(query.order_by(ProspectSearchCandidate.id)).scalars())

    def _discovered_candidate_ids(self, state: _RunState, trade_key: str) -> list[int]:
        """
        Candidates of a trade found earlier and not verified yet, the ones without a website button first.

        While the budget runs low, the ones showing a website button are left out.
        """
        query = select(ProspectSearchCandidate.id, ProspectSearchCandidate.has_website_button).where(
            ProspectSearchCandidate.search_id == self._search_id,
            ProspectSearchCandidate.status == CandidateStatus.DISCOVERED.value,
            ProspectSearchCandidate.trade == trade_key,
        )
        with SessionLocal() as db:
            discovered = [
                (bool(has_website_button), candidate_id) for candidate_id, has_website_button in db.execute(query).all()
            ]
        leaves_website_listings_unverified = self._leaves_website_listings_unverified(state)
        return [
            candidate_id
            for has_website_button, candidate_id in sorted(discovered)
            if not (has_website_button and leaves_website_listings_unverified)
        ]

    def _count(self, trade_key: str, status: CandidateStatus) -> int:
        """Candidates of a trade currently in a status."""
        return self._counts.get(trade_key, {}).get(status.value, 0)

    def _reload_counts(self) -> None:
        """
        Recount the search's candidates from the database.

        Between two towns no verification is in flight, and the counters may be stale: the
        desktop app hands over Facebook reads, and the user keeps or discards candidates by
        hand, while the run goes on.
        """
        with SessionLocal() as db:
            rows = db.execute(
                select(
                    ProspectSearchCandidate.trade,
                    ProspectSearchCandidate.status,
                    func.count(ProspectSearchCandidate.id),
                )
                .where(ProspectSearchCandidate.search_id == self._search_id)
                .group_by(ProspectSearchCandidate.trade, ProspectSearchCandidate.status)
            ).all()
        self._counts = {}
        for trade_key, status, total in rows:
            self._add_count(trade_key, status, total)

    def _add_count(self, trade_key: str, status: str, delta: int) -> None:
        """Move the in-memory counter of a trade and status."""
        by_status = self._counts.setdefault(trade_key, {})
        by_status[status] = by_status.get(status, 0) + delta

    def _log(self, message: str) -> None:
        """Queue a journal line, stamped with the naive UTC time (the screen shows it in the viewer's timezone)."""
        self._new_journal_lines.append({"at": naive_utc_now().isoformat(timespec="seconds"), "message": message})

    def _flush(self, *, status: ProspectSearchStatus | None = None, error_message: str | None = None) -> None:
        """Write the journal, the progress and the spending to the search row; optionally end the run."""
        with SessionLocal() as db:
            search = db.get(ProspectSearch, self._search_id)
            if search is None:
                return
            search.journal = [*(search.journal or []), *self._new_journal_lines][-_JOURNAL_MAX_LINES:]
            self._new_journal_lines = []
            search.progress = {**self._progress, "trades": {**self._progress.get("trades", {})}}
            judge_call_count = self._verifier.judge_call_count + self._contact_finder.judge_call_count
            search.request_count += self._client.request_count - self._stored_request_count
            search.judge_call_count += judge_call_count - self._stored_judge_call_count
            self._stored_request_count = self._client.request_count
            self._stored_judge_call_count = judge_call_count
            if status is not None and search.status != ProspectSearchStatus.CANCELLED.value:
                search.status = status.value
                search.error_message = error_message
                if status in (ProspectSearchStatus.COMPLETED, ProspectSearchStatus.FAILED):
                    search.completed_at = naive_utc_now()
            db.commit()

    @classmethod
    def _journal_line(cls, facts: CandidateFacts, verdict: CandidateVerdict) -> str:
        """One plain line saying what happened to a candidate."""
        if verdict.status == CandidateStatus.REJECTED:
            return f"{facts.name} : écarté. {verdict.detail or ''}".strip()
        if verdict.status == CandidateStatus.KEPT:
            return f"{facts.name} : gardé ({facts.email or facts.phone or 'contact trouvé'})."
        return f"{facts.name} : {cls._status_words(verdict.status)}. {verdict.detail or ''}".strip()

    @staticmethod
    def _status_words(status: CandidateStatus) -> str:
        """A candidate status in the user's words."""
        return {
            CandidateStatus.KEPT: "gardé",
            CandidateStatus.SET_ASIDE: "mis de côté",
            CandidateStatus.TO_CONFIRM: "à confirmer",
            CandidateStatus.NEEDS_BROWSER: "en attente de lecture Facebook",
            CandidateStatus.REJECTED: "écarté",
            CandidateStatus.DISCOVERED: "trouvé",
        }[status]
