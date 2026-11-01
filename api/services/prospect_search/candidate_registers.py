"""
Candidate registers — what the company registers say of a candidate about to be proposed.

Read once a candidate would be proposed, whether the search placed it or its Facebook page was read on the desktop
afterwards: the closing of its firm (Swiss and French registers), and the firm its email names when the Swiss
register seats it elsewhere.
"""

from __future__ import annotations

from enums.prospect_search import CandidateStatus
from services.prospect_search.candidate_decision import CandidateVerdict
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.french_registry import french_registry
from services.prospect_search.swiss_registry import swiss_registry

_PROPOSED_STATUSES: tuple[CandidateStatus, ...] = (
    CandidateStatus.KEPT,
    CandidateStatus.SET_ASIDE,
    CandidateStatus.TO_CONFIRM,
)


class CandidateRegisters:
    """Reads the company registers for a candidate about to be proposed."""

    @staticmethod
    async def read_if_proposed(facts: CandidateFacts, verdict: CandidateVerdict) -> bool:
        """
        Read the registers when a verdict proposes the candidate: its firm's closing, the firm its email names.

        Args:
            facts: The candidate, completed in place.
            verdict: Where the candidate goes without them.

        Returns:
            Whether the registers were read, the verdict then to take again.
        """
        if verdict.status not in _PROPOSED_STATUSES:
            return False
        await swiss_registry.read_closing(facts)
        await swiss_registry.note_email_firm_elsewhere(facts)
        await french_registry.read_closing(facts)
        return True
