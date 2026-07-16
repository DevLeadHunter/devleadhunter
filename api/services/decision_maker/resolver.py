"""Multi-strategy decision-maker resolver (the cascade orchestrator)."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional

from services.decision_maker.strategies import (
    LegalMentionsStrategy,
    LlmAggregateStrategy,
    OwnerResponseStrategy,
    PappersStrategy,
    RegistreGouvStrategy,
)
from services.decision_maker.types import NameCandidate, NameStrategy, ResolutionContext

logger = logging.getLogger(__name__)

#: Below this confidence, no personalisation at all (« Bonjour , » is banned;
#: a wrong name is worse than no name).
CONFIDENCE_THRESHOLD: float = 0.7

#: Confidence boost when two INDEPENDENT sources agree on the same identity.
_AGREEMENT_BOOST: float = 0.15

_POSTAL_CODE_RE = re.compile(r"\b(\d{5})\b")


class DecisionMakerResolver:
    """Runs every strategy, merges candidates, applies the confidence rules."""

    def __init__(self, strategies: Optional[list[NameStrategy]] = None) -> None:
        """Wire the default cascade (order is cosmetic — they run in parallel)."""
        self.strategies: list[NameStrategy] = strategies or [
            RegistreGouvStrategy(),
            PappersStrategy(),
            OwnerResponseStrategy(),
            LegalMentionsStrategy(),
            LlmAggregateStrategy(),
        ]

    async def resolve(self, context: ResolutionContext) -> Optional[NameCandidate]:
        """Return the best trusted candidate, or None (→ neutral greeting)."""
        results = await asyncio.gather(
            *(strategy.resolve(context) for strategy in self.strategies),
            return_exceptions=True,
        )
        candidates: list[NameCandidate] = []
        for strategy, result in zip(self.strategies, results):
            if isinstance(result, BaseException):
                logger.warning("decision-maker strategy %s raised: %s", strategy.name, result)
                continue
            candidates.extend(c for c in result if c.has_name)
        return self.pick_best(candidates)

    def pick_best(self, candidates: list[NameCandidate]) -> Optional[NameCandidate]:
        """Merge candidates and apply agreement boost + threshold (pure)."""
        if not candidates:
            return None

        # Cross-check: identical identity confirmed by another SOURCE → boost.
        # A first-name-only candidate also confirms a full-name candidate that
        # shares the same first name (e.g. owner-response « Léo » + registry
        # « Léo Guillaume »).
        boosted: list[NameCandidate] = []
        for candidate in candidates:
            agreement = any(
                other.source != candidate.source
                and (
                    other.identity_key() == candidate.identity_key()
                    or (
                        candidate.first
                        and other.first
                        and other.first.lower() == candidate.first.lower()
                        and (not other.last or not candidate.last)
                    )
                )
                for other in candidates
            )
            confidence = min(1.0, candidate.confidence + (_AGREEMENT_BOOST if agreement else 0.0))
            boosted.append(
                NameCandidate(
                    first=candidate.first,
                    last=candidate.last,
                    gender=candidate.gender,
                    source=candidate.source,
                    confidence=round(confidence, 2),
                    raw=candidate.raw,
                )
            )

        best = max(boosted, key=lambda c: (c.confidence, bool(c.first and c.last)))
        if best.confidence < CONFIDENCE_THRESHOLD:
            return None

        # Unresolvable disagreement at the top: two different identities with
        # the same winning confidence → trust neither (golden rule).
        rivals = [
            c
            for c in boosted
            if c.confidence == best.confidence and c.identity_key() != best.identity_key()
        ]
        if rivals:
            return None
        return best


def context_from_prospect(prospect, enrichment=None) -> ResolutionContext:  # noqa: ANN001
    """Build the strategy input from a prospect row (+ optional enrichment).

    Source-agnostic on purpose: only persisted prospect/enrichment data is
    used, whatever scraper discovered the prospect.
    """
    postal_match = _POSTAL_CODE_RE.search(prospect.address or "")
    owner_responses: list[str] = []
    description: Optional[str] = None
    if enrichment is not None:
        description = enrichment.description
        for review in enrichment.reviews or []:
            if isinstance(review, dict):
                reply = review.get("owner_response") or review.get("ownerResponse")
                if reply:
                    owner_responses.append(str(reply))
    return ResolutionContext(
        company_name=prospect.name or "",
        city=prospect.city,
        postal_code=postal_match.group(1) if postal_match else None,
        website=prospect.website,
        phone=prospect.phone,
        owner_responses=owner_responses,
        description=description,
    )


decision_maker_resolver = DecisionMakerResolver()
