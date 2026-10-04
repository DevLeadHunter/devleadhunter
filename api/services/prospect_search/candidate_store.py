"""
Candidate store — reads a candidate row into facts, writes a verdict back, creates the prospect.
"""

from __future__ import annotations

import asyncio
import logging
from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from enums.prospect_search import CandidateRejectReason, CandidateStatus, EmailProofLevel
from enums.source import Source
from enums.website_status import WebsiteStatus
from models.prospect import ProspectCreate
from models.prospect_search_candidate import ProspectSearchCandidate
from services.enrichment_service import enrichment_service
from services.prospect_search.candidate_decision import CandidateVerdict
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.candidate_identity import CandidateIdentity, KnownBusinessIndex
from services.prospect_search.trade_catalog import TradeCatalog, TradeProfile
from services.prospect_service import prospect_service

logger = logging.getLogger(__name__)

_PROSPECT_STATUSES: tuple[CandidateStatus, ...] = (CandidateStatus.KEPT, CandidateStatus.SET_ASIDE)
# A business an earlier search discarded can still be kept by hand: only these reasons forbid a new prospect.
_EXISTING_PROSPECT_REASONS: tuple[CandidateRejectReason, ...] = (
    CandidateRejectReason.ALREADY_KNOWN,
    CandidateRejectReason.DO_NOT_CONTACT,
)
_REJECT_DETAIL_MAX_CHARS: int = 500


class CandidateStore:
    """Moves a candidate between its database row and the facts the search works on."""

    _prospect_creation_lock_by_user: ClassVar[dict[int, asyncio.Lock]] = {}

    @staticmethod
    def facts_of(row: ProspectSearchCandidate) -> CandidateFacts:
        """
        Read a candidate row into working facts.

        Args:
            row: The stored candidate.

        Returns:
            Its facts, with the proofs gathered so far.
        """
        return CandidateFacts(
            name=row.name,
            trade_key=row.trade,
            country=row.country,
            origin=row.origin,
            city=row.city,
            searched_city=row.searched_city,
            address=row.address,
            phone=row.phone,
            email=row.email,
            email_proof_level=row.email_proof_level,
            website=row.website,
            website_status=row.website_status,
            google_cid=row.google_cid,
            google_maps_url=row.google_maps_url,
            facebook_url=row.facebook_url,
            google_rating=row.google_rating,
            google_reviews_count=row.google_reviews_count,
            google_category=row.google_category,
            owner_name=row.owner_name,
            registry_number=row.registry_number,
            has_website_button=row.has_website_button,
            evidence=list(row.evidence or []),
        )

    @staticmethod
    def verdict_of(row: ProspectSearchCandidate) -> CandidateVerdict:
        """The verdict a candidate row carries now."""
        return CandidateVerdict(
            CandidateStatus(row.status),
            CandidateRejectReason(row.reject_reason) if row.reject_reason else None,
            row.reject_detail,
        )

    @staticmethod
    def identity_keys(facts: CandidateFacts) -> list[str]:
        """Identity keys of the business the facts describe."""
        return CandidateIdentity.keys(
            name=facts.name,
            city=facts.town,
            country=facts.country,
            phone=facts.phone,
            google_cid=facts.google_cid,
            facebook_url=facts.facebook_url,
            email=facts.email,
        )

    @classmethod
    def write_back(cls, row: ProspectSearchCandidate, facts: CandidateFacts, verdict: CandidateVerdict) -> None:
        """
        Copy the facts and the verdict onto the candidate row (the caller commits).

        Args:
            row: The stored candidate.
            facts: What the search read about it.
            verdict: Where it goes.
        """
        row.name = facts.name[:255]
        row.city = (facts.city or None) and facts.city[:120]
        row.address = (facts.address or None) and facts.address[:255]
        row.phone = (facts.phone or None) and facts.phone[:50]
        row.phone_is_mobile = facts.has_mobile_phone
        row.email = facts.email
        row.email_proof_level = facts.email_proof_level
        row.website = (facts.website or None) and facts.website[:500]
        row.website_status = facts.website_status
        row.google_cid = facts.google_cid
        row.google_maps_url = facts.google_maps_url
        row.facebook_url = (facts.facebook_url or None) and facts.facebook_url[:500]
        row.google_rating = facts.google_rating
        row.google_reviews_count = facts.google_reviews_count
        row.google_category = (facts.google_category or None) and facts.google_category[:160]
        row.owner_name = (facts.owner_name or None) and facts.owner_name[:160]
        row.registry_number = (facts.registry_number or None) and facts.registry_number[:40]
        row.has_website_button = facts.has_website_button
        row.evidence = list(facts.evidence)
        row.identity_keys = cls.identity_keys(facts)
        row.status = verdict.status.value
        row.reject_reason = verdict.reject_reason.value if verdict.reject_reason else None
        row.reject_detail = (verdict.detail or None) and verdict.detail[:_REJECT_DETAIL_MAX_CHARS]
        row.updated_at = naive_utc_now()

    @classmethod
    async def promote(
        cls,
        db: Session,
        row: ProspectSearchCandidate,
        facts: CandidateFacts,
        trade: TradeProfile,
        *,
        organization_id: int | None,
    ) -> int | None:
        """
        Create the prospect of a kept or set-aside candidate, once.

        The user's prospects are read again just before the creation, one candidate at a time
        for a user: another search running at the same moment, or a prospect added since the
        run started, must not give the same business a second prospect. A business found
        there is discarded as already known instead. As in :meth:`promote_accepted`, the
        candidate is read again once the lock is held, in a new transaction.

        Args:
            db: Active database session, with nothing left to commit.
            row: The stored candidate (its ``prospect_id`` is filled).
            facts: What the search read about it.
            trade: Profile of the searched trade, naming the prospect's category.
            organization_id: The owner's organization, the prospect is shared with it.

        Returns:
            The prospect id, or ``None`` when the candidate is not one that becomes a prospect
            or its business turned out to be a prospect already.
        """
        if not cls._is_awaiting_its_prospect(row):
            return row.prospect_id

        async with cls._prospect_creation_lock_by_user.setdefault(row.user_id, asyncio.Lock()):
            # Under REPEATABLE READ, a transaction begun before the lock would miss what the previous holder created.
            db.commit()
            db.refresh(row)
            if not cls._is_awaiting_its_prospect(row):
                return row.prospect_id
            known_businesses = KnownBusinessIndex.load(
                db, user_id=row.user_id, organization_id=organization_id, search_id=row.search_id
            )
            return await cls._create_prospect_unless_known(
                db, row, facts, trade, known_businesses, organization_id=organization_id
            )

    @classmethod
    async def promote_accepted(
        cls, db: Session, rows: list[ProspectSearchCandidate], *, organization_id: int | None
    ) -> None:
        """
        Create the prospects of candidates of one search that their owner accepted together.

        The owner's prospects are read once for all of them, under the same lock as
        :meth:`promote`, and each prospect created is remembered for the next candidates.
        Afterwards each row carries its prospect, or is discarded as already known, or is
        left as it was when its creation failed or could not be read (the owner can accept it again).

        Once the lock is held, the transaction the candidates were read in is ended and they are
        read again: under REPEATABLE READ, production's isolation, that transaction keeps reading
        the database as it was, and a second acceptance of the same candidate, waiting for the lock
        while the first one created its prospect, would create another one.

        Args:
            db: Active database session, with nothing left to commit.
            rows: Candidates of a single search; only the kept and set-aside ones without a prospect are handled.
            organization_id: The owner's organization, the prospects are shared with it.
        """
        if not rows:
            return
        owner_id, search_id = rows[0].user_id, rows[0].search_id
        candidate_ids = [row.id for row in rows]
        async with cls._prospect_creation_lock_by_user.setdefault(owner_id, asyncio.Lock()):
            try:
                db.commit()
                row_by_id = cls._rows_awaiting_their_prospect(db, owner_id, candidate_ids)
                if not row_by_id:
                    return
                known_businesses = KnownBusinessIndex.load(
                    db, user_id=owner_id, organization_id=organization_id, search_id=search_id
                )
            except Exception as exc:
                db.rollback()
                logger.error(
                    "Prospect search: candidates %s could not be read for their prospects: %s", candidate_ids, exc
                )
                return
            for candidate_id, row in row_by_id.items():
                try:
                    facts = cls.facts_of(row)
                    prospect_id = await cls._create_prospect_unless_known(
                        db,
                        row,
                        facts,
                        TradeCatalog.resolve(row.trade),
                        known_businesses,
                        organization_id=organization_id,
                    )
                except Exception as exc:
                    db.rollback()
                    logger.error("Prospect search: prospect creation failed for candidate %s: %s", candidate_id, exc)
                    continue
                if prospect_id is not None:
                    known_businesses.remember_prospect(cls.identity_keys(facts), prospect_id)

    @staticmethod
    def _is_awaiting_its_prospect(row: ProspectSearchCandidate) -> bool:
        """Whether the candidate is kept or set aside and has no prospect yet."""
        return row.prospect_id is None and CandidateStatus(row.status) in _PROSPECT_STATUSES

    @staticmethod
    def _rows_awaiting_their_prospect(
        db: Session, owner_id: int, candidate_ids: list[int]
    ) -> dict[int, ProspectSearchCandidate]:
        """
        Read again the owner's candidates among ``candidate_ids`` that still await their prospect.

        Returns:
            Those candidates by id, in the order of ``candidate_ids``.
        """
        fresh_row_by_id = {
            row.id: row
            for row in db.execute(
                select(ProspectSearchCandidate)
                .where(
                    ProspectSearchCandidate.user_id == owner_id,
                    ProspectSearchCandidate.id.in_(candidate_ids),
                    ProspectSearchCandidate.prospect_id.is_(None),
                    ProspectSearchCandidate.status.in_([status.value for status in _PROSPECT_STATUSES]),
                )
                .execution_options(populate_existing=True)
            ).scalars()
        }
        return {
            candidate_id: fresh_row_by_id[candidate_id]
            for candidate_id in candidate_ids
            if candidate_id in fresh_row_by_id
        }

    @classmethod
    async def _create_prospect_unless_known(
        cls,
        db: Session,
        row: ProspectSearchCandidate,
        facts: CandidateFacts,
        trade: TradeProfile,
        known_businesses: KnownBusinessIndex,
        *,
        organization_id: int | None,
    ) -> int | None:
        """
        Create the candidate's prospect, or discard the candidate when its business is a prospect already.

        The caller holds the owner's creation lock and read ``known_businesses`` under it.

        Returns:
            The prospect id, or ``None`` when the candidate was discarded as already known.
        """
        known = known_businesses.match(cls.identity_keys(facts))
        if known is not None and known.reason in _EXISTING_PROSPECT_REASONS:
            cls.write_back(row, facts, CandidateVerdict(CandidateStatus.REJECTED, known.reason, known.detail))
            row.prospect_id = known.prospect_id
            db.commit()
            return None

        is_website_working = facts.website_status == WebsiteStatus.LIVE.value
        confidence_by_proof = {EmailProofLevel.PUBLISHED.value: 4, EmailProofLevel.DIRECTORY.value: 3}
        has_checked_website = bool(facts.website and facts.website_status)
        created = await prospect_service.create_prospect(
            db=db,
            prospect=ProspectCreate(
                name=facts.name,
                address=facts.address,
                city=facts.town or None,
                country=facts.country,
                phone=facts.phone,
                email=facts.email,
                website=facts.website,
                website_status=WebsiteStatus(facts.website_status) if has_checked_website else None,
                google_maps_url=facts.google_maps_url,
                facebook_url=facts.facebook_url,
                google_rating=facts.google_rating,
                google_reviews_count=facts.google_reviews_count,
                category=trade.prospect_category,
                source=Source.SEARCH,
                confidence=confidence_by_proof.get(facts.email_proof_level or "", 3 if is_website_working else 2),
            ),
            user_id=row.user_id,
            organization_id=organization_id,
        )
        row.prospect_id = created.id
        db.commit()
        enrichment_service.schedule_contact_resolution([created.id])
        return created.id

    @classmethod
    async def promote_or_leave_to_confirm(
        cls,
        db: Session,
        row: ProspectSearchCandidate,
        facts: CandidateFacts,
        trade: TradeProfile,
        *,
        organization_id: int | None,
    ) -> int | None:
        """
        Create the candidate's prospect; when the creation fails, hand the candidate to the user.

        Args:
            db: Active database session.
            row: The stored candidate.
            facts: What the search read about it.
            trade: Profile of the searched trade.
            organization_id: The owner's organization.

        Returns:
            The prospect id, or ``None`` when no prospect was created.
        """
        candidate_id = row.id
        try:
            return await cls.promote(db, row, facts, trade, organization_id=organization_id)
        except Exception as exc:
            # A failed write leaves the session unusable until it is rolled back.
            db.rollback()
            logger.error("Prospect search: prospect creation failed for candidate %s: %s", candidate_id, exc)
            row.status = CandidateStatus.TO_CONFIRM.value
            row.reject_reason = None
            row.reject_detail = "Le prospect n'a pas pu être créé : à reprendre à la main."
            db.commit()
            return None
