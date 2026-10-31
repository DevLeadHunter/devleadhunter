"""
Candidate duplicates — two listings of one search that turn out to be one business.

Google often lists a business twice (a garage and its body shop, an old listing beside a new one).
The verification reveals keys the listings did not carry, an email, a Facebook page, a registry
number, and two candidates of a search sharing one are the same business: only the better-informed
listing is proposed, and a website, a network or a refusal of advertising found on one listing
rules out the whole business.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from enums.prospect_search import CandidateRejectReason, CandidateStatus
from models.prospect_search_candidate import ProspectSearchCandidate

_PROPOSED_STATUSES: tuple[str, ...] = (
    CandidateStatus.KEPT.value,
    CandidateStatus.SET_ASIDE.value,
    CandidateStatus.TO_CONFIRM.value,
    CandidateStatus.NEEDS_BROWSER.value,
)
# What one listing proves about the whole business, whatever the other listing showed.
_BUSINESS_WIDE_REJECT_REASONS: tuple[str, ...] = (
    CandidateRejectReason.HAS_WEBSITE.value,
    CandidateRejectReason.CHAIN.value,
    CandidateRejectReason.NO_ADVERTISING.value,
)
# A listing discarded for one of these reasons discards the other listings of its business found later.
_LASTING_REJECT_REASONS: tuple[str, ...] = (
    *_BUSINESS_WIDE_REJECT_REASONS,
    CandidateRejectReason.CLOSED.value,
    CandidateRejectReason.HOMONYM.value,
    CandidateRejectReason.MANUAL.value,
)
_STATUS_RANKS: dict[str, int] = {
    CandidateStatus.KEPT.value: 3,
    CandidateStatus.SET_ASIDE.value: 2,
    CandidateStatus.TO_CONFIRM.value: 1,
    CandidateStatus.NEEDS_BROWSER.value: 0,
}
_EMAIL_PROOF_RANKS: dict[str, int] = {"a": 3, "b": 2, "c": 1}
_REJECT_DETAIL_MAX_CHARS: int = 500


class CandidateDuplicates:
    """Leaves a single listing of each business among the candidates of a search."""

    @classmethod
    def settle(cls, db: Session, row: ProspectSearchCandidate) -> list[tuple[ProspectSearchCandidate, str]]:
        """
        Compare a candidate just placed with the other listings of its business in its search (the caller commits).

        A listing discarded for a website, a network or a refusal of advertising discards the waiting listings of
        its business; one discarded for good otherwise (closed, a namesake, by hand) discards a listing placed
        after it. Among the listings still proposed, the better-informed one stays: the better place, then a
        mobile, then the more Google reviews, then the better-proven email, the first found when all is equal.
        A listing that already became a prospect makes the others known businesses.

        Args:
            db: Active database session.
            row: The candidate just placed, its keys and status written.

        Returns:
            Every candidate whose place changed, the given one included, with its status before.
        """
        siblings = cls._siblings(db, row)
        if not siblings:
            return []
        if row.status == CandidateStatus.REJECTED.value:
            if row.reject_reason not in _BUSINESS_WIDE_REJECT_REASONS:
                return []
            moved = [(sibling, sibling.status) for sibling in siblings if cls._is_waiting(sibling)]
            for sibling, _ in moved:
                cls._discard_as_same_business(sibling, row)
            return moved
        if not cls._is_waiting(row):
            return []
        previous_status = row.status
        discarded_for_good = sorted(
            (
                sibling
                for sibling in siblings
                if sibling.status == CandidateStatus.REJECTED.value and sibling.reject_reason in _LASTING_REJECT_REASONS
            ),
            key=lambda sibling: sibling.reject_reason not in _BUSINESS_WIDE_REJECT_REASONS,
        )
        if discarded_for_good:
            cls._discard_after(row, discarded_for_good[0])
            return [(row, previous_status)]
        prospect_sibling = next((sibling for sibling in siblings if sibling.prospect_id is not None), None)
        if prospect_sibling is not None:
            cls._discard_as_known(row, prospect_sibling)
            return [(row, previous_status)]
        listings = sorted(
            [row, *(sibling for sibling in siblings if cls._is_waiting(sibling))], key=lambda listing: listing.id
        )
        best = max(listings, key=cls._rank)
        moved = [(listing, listing.status) for listing in listings if listing is not best]
        for listing, _ in moved:
            cls._discard(
                listing,
                CandidateRejectReason.AWAITING_DECISION,
                f"Même entreprise que « {best.name} », une fiche mieux renseignée de cette recherche.",
            )
        return moved

    @staticmethod
    def _siblings(db: Session, row: ProspectSearchCandidate) -> list[ProspectSearchCandidate]:
        """The other candidates of the search placed so far that share a key with *row*, its name in its town aside."""
        keys = {key for key in row.identity_keys or [] if not key.startswith("name:")}
        if not keys:
            return []
        placed = db.execute(
            select(ProspectSearchCandidate).where(
                ProspectSearchCandidate.search_id == row.search_id,
                ProspectSearchCandidate.id != row.id,
                ProspectSearchCandidate.status != CandidateStatus.DISCOVERED.value,
            )
        ).scalars()
        return [candidate for candidate in placed if keys & set(candidate.identity_keys or [])]

    @staticmethod
    def _is_waiting(candidate: ProspectSearchCandidate) -> bool:
        """Whether a candidate is proposed and still waits for the user or its prospect: its place can change."""
        return candidate.prospect_id is None and candidate.status in _PROPOSED_STATUSES

    @staticmethod
    def _rank(candidate: ProspectSearchCandidate) -> tuple[int, int, int, int]:
        """How well a listing is informed: its place, a mobile, its Google reviews, its email's proof."""
        return (
            _STATUS_RANKS.get(candidate.status, -1),
            int(bool(candidate.phone_is_mobile)),
            candidate.google_reviews_count or 0,
            _EMAIL_PROOF_RANKS.get(candidate.email_proof_level or "", 0),
        )

    @classmethod
    def _discard_as_same_business(cls, candidate: ProspectSearchCandidate, discarded: ProspectSearchCandidate) -> None:
        """Discard a listing for what another listing of its business proved (a website, a network…)."""
        cls._discard(
            candidate,
            CandidateRejectReason(discarded.reject_reason),
            f"Même entreprise que « {discarded.name} » : {discarded.reject_detail or ''}",
        )

    @classmethod
    def _discard_after(cls, candidate: ProspectSearchCandidate, discarded: ProspectSearchCandidate) -> None:
        """Discard a listing found after another listing of its business was discarded for good."""
        if discarded.reject_reason in _BUSINESS_WIDE_REJECT_REASONS:
            cls._discard_as_same_business(candidate, discarded)
            return
        cls._discard(
            candidate,
            CandidateRejectReason.PREVIOUSLY_REJECTED,
            "Déjà écarté par cette recherche sous une autre fiche.",
        )

    @classmethod
    def _discard_as_known(cls, candidate: ProspectSearchCandidate, prospect_listing: ProspectSearchCandidate) -> None:
        """Discard a listing whose business is already a prospect through another listing of the search."""
        if prospect_listing.reject_reason == CandidateRejectReason.DO_NOT_CONTACT.value:
            cls._discard(candidate, CandidateRejectReason.DO_NOT_CONTACT, prospect_listing.reject_detail or "")
        else:
            cls._discard(
                candidate,
                CandidateRejectReason.ALREADY_KNOWN,
                f"Déjà dans vos prospects sous la fiche « {prospect_listing.name} ».",
            )
        candidate.prospect_id = prospect_listing.prospect_id

    @staticmethod
    def _discard(candidate: ProspectSearchCandidate, reason: CandidateRejectReason, detail: str) -> None:
        """Write a discarded place on a candidate row."""
        candidate.status = CandidateStatus.REJECTED.value
        candidate.reject_reason = reason.value
        candidate.reject_detail = detail.strip()[:_REJECT_DETAIL_MAX_CHARS]
        candidate.updated_at = naive_utc_now()
