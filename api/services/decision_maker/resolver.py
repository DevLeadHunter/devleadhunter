"""Multi-strategy decision-maker resolver (the cascade orchestrator)."""

from __future__ import annotations

import asyncio
import logging
import re

from enums.website_status import WebsiteStatus
from services.decision_maker.strategies import (
    LegalMentionsStrategy,
    LlmAggregateStrategy,
    OwnerResponseStrategy,
    PappersStrategy,
    RegistreGouvStrategy,
    WebRegistryStrategy,
)
from services.decision_maker.types import NameCandidate, NameResolution, NameStrategy, ResolutionContext

logger = logging.getLogger(__name__)

#: Automatic-use bar: below it a candidate is at best a human-reviewed proposal.
CONFIDENCE_THRESHOLD: float = 0.7

#: Proposal bar: below it a candidate is dropped entirely (neutral greeting).
PROPOSED_FLOOR: float = 0.55

#: Confidence boost when two INDEPENDENT sources agree on the same identity.
_AGREEMENT_BOOST: float = 0.15

#: A rival primary within this confidence margin of the best one is a real
#: ambiguity (two authoritative identities) — trust neither.
_PRIMARY_RIVAL_MARGIN: float = 0.1

_POSTAL_CODE_RE = re.compile(r"\b(\d{5})\b")


class DecisionMakerResolver:
    """Runs every strategy, merges candidates, applies the confidence rules."""

    def __init__(self, strategies: list[NameStrategy] | None = None) -> None:
        """Wire the default cascade (order is cosmetic — they run in parallel)."""
        self.strategies: list[NameStrategy] = strategies or [
            RegistreGouvStrategy(),
            PappersStrategy(),
            WebRegistryStrategy(),
            OwnerResponseStrategy(),
            LegalMentionsStrategy(),
            LlmAggregateStrategy(),
        ]

    async def resolve(self, context: ResolutionContext) -> NameResolution:
        """Run the cascade and classify the outcome (AUTO / PROPOSED / NONE)."""
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

    def pick_best(self, candidates: list[NameCandidate]) -> NameResolution:
        """Merge candidates and classify the best one (pure).

        Outcome rules (a wrong name is worse than no name):
          - AUTO requires a PRIMARY source (registre/Pappers) whose company was
            also matched geographically — supporting sources can never stack up
            to automatic use, whatever their combined confidence.
          - A rival primary that is NOT geo-confirmed while the best one is, is
            the expected homonym-from-elsewhere noise → ignored entirely.
          - Two geo-confirmed primaries naming different people → trust neither.
          - Any other disagreeing candidate above the proposal floor demotes an
            AUTO outcome to PROPOSED (human arbitration, never a sent email).
        """
        if not candidates:
            return NameResolution(status=NameResolution.NONE, candidate=None, candidates=[])

        boosted = self._apply_agreement_boost(candidates)
        best = max(boosted, key=self._selection_key)
        if best.confidence < PROPOSED_FLOOR:
            return NameResolution(status=NameResolution.NONE, candidate=None, candidates=boosted)

        rivals = [c for c in boosted if not c.agrees_with(best)]
        # Homonyms from another département: a name-only registry match cannot
        # rival a geo-confirmed one — the geography already disambiguated them.
        if best.primary and best.geo_confirmed:
            rivals = [r for r in rivals if not (r.primary and not r.geo_confirmed)]

        # Two comparable-authority identities too close to call → trust neither.
        # A supporting source tied with a primary is NOT a stalemate: the
        # primary keeps the lead and the disagreement demotes it below.
        primary_stalemate = any(
            r.primary and r.geo_confirmed and best.primary and r.confidence >= best.confidence - _PRIMARY_RIVAL_MARGIN
            for r in rivals
        )
        equal_stalemate = any(r.confidence == best.confidence and not (best.primary and not r.primary) for r in rivals)
        if primary_stalemate or equal_stalemate:
            return NameResolution(status=NameResolution.NONE, candidate=None, candidates=boosted)

        demoted = any(r.confidence >= PROPOSED_FLOOR for r in rivals)
        auto_eligible = best.primary and best.geo_confirmed and best.confidence >= CONFIDENCE_THRESHOLD and not demoted
        status = NameResolution.AUTO if auto_eligible else NameResolution.PROPOSED
        return NameResolution(status=status, candidate=best, candidates=boosted)

    @staticmethod
    def _selection_key(candidate: NameCandidate) -> tuple[float, bool, bool]:
        """Ranking key: confidence, with authoritative geo-anchored sources ahead.

        A geo-confirmed primary within a whisker of a supporting source must win
        the pick (the registry beats a legal-page regex naming the web agency) —
        the small bonus only orders the pick, it never touches stored confidence.
        """
        selection_score = candidate.confidence + (
            _PRIMARY_RIVAL_MARGIN if candidate.primary and candidate.geo_confirmed else 0.0
        )
        return (selection_score, candidate.primary, bool(candidate.first and candidate.last))

    @staticmethod
    def _apply_agreement_boost(candidates: list[NameCandidate]) -> list[NameCandidate]:
        """Boost identities confirmed by a source with a DIFFERENT evidence base.

        Two candidates extracted from the same underlying text (owner replies
        read by both the signature regex and the LLM) are one observation, not
        two — they never corroborate each other.
        """
        boosted: list[NameCandidate] = []
        for candidate in candidates:
            agreement = any(
                other.evidence_group != candidate.evidence_group and other.agrees_with(candidate)
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
                    primary=candidate.primary,
                    geo_confirmed=candidate.geo_confirmed,
                    evidence_group=candidate.evidence_group,
                    provenance=candidate.provenance,
                    raw=candidate.raw,
                )
            )
        return boosted


def context_from_prospect(prospect, enrichment=None) -> ResolutionContext:
    """Build the strategy input from a prospect row (+ optional enrichment).

    Source-agnostic on purpose: only persisted prospect/enrichment data is
    used, whatever scraper discovered the prospect. When the prospect address
    carries no postal code, the Maps place identity persisted at enrichment
    fills the geographic anchor — the place was itself validated against the
    prospect, so registry matches become geo-confirmable.
    """
    postal_match = _POSTAL_CODE_RE.search(prospect.address or "")
    postal_code = postal_match.group(1) if postal_match else None
    city = prospect.city
    website = prospect.website
    # A dead site only 404s; a directory mini-site names the DIRECTORY's
    # publisher in its legal mentions — the wrong person by construction.
    if prospect.website_status in (WebsiteStatus.DEAD.value, WebsiteStatus.PLACEHOLDER.value):
        website = None
    owner_responses: list[str] = []
    description: str | None = None
    if enrichment is not None:
        description = enrichment.description
        postal_code = postal_code or enrichment.place_postal_code
        city = city or enrichment.place_city
        for review in enrichment.reviews or []:
            if isinstance(review, dict):
                reply = review.get("owner_response") or review.get("ownerResponse")
                if reply:
                    owner_responses.append(str(reply))
    return ResolutionContext(
        company_name=prospect.name or "",
        city=city,
        postal_code=postal_code,
        website=website,
        phone=prospect.phone,
        owner_responses=owner_responses,
        description=description,
    )


decision_maker_resolver = DecisionMakerResolver()
