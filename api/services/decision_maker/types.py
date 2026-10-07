"""Shared types of the decision-maker resolution cascade."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class NameCandidate:
    """One possible decision-maker name proposed by a strategy.

    ``confidence`` is 0..1. ``primary`` marks an authoritative identity source
    (official registries): only a primary AND geo-confirmed candidate may be
    used automatically — everything else is at best a human-reviewed proposal.
    """

    first: str | None = None
    last: str | None = None
    gender: str | None = None  # 'M' | 'F' | None
    source: str = ""
    confidence: float = 0.0
    #: Authoritative identity source (registre/Pappers) vs supporting signal.
    primary: bool = False
    #: The source's company was matched on the prospect's location too
    #: (commune or département) — required for automatic use of a primary.
    geo_confirmed: bool = False
    #: Underlying document family — two candidates extracted from the SAME
    #: text (e.g. owner replies read by both the regex and the LLM) are one
    #: observation, not two, and must never corroborate each other.
    evidence_group: str = ""
    #: Human-readable French justification shown next to the name in the drawer.
    provenance: str = ""
    raw: dict[str, Any] = field(default_factory=dict)
    #: Read from the very company the prospect search tied to the business by its number: no
    #: same-place homonym can rival it.
    anchored: bool = False

    @property
    def has_name(self) -> bool:
        """True when the candidate carries at least a first or last name."""
        return bool(self.first or self.last)

    def identity_key(self) -> str:
        """Comparable key used to detect agreement between sources."""
        from services.decision_maker.normalize import fold

        return f"{fold(self.first or '')}|{fold(self.last or '')}"

    def agrees_with(self, other: NameCandidate) -> bool:
        """True when both candidates plausibly name the SAME person.

        A first-name-only candidate confirms a full-name candidate sharing the
        same first name (« Léo » agrees with « Léo Guillaume »).
        """
        if self.identity_key() == other.identity_key():
            return True
        return bool(
            self.first
            and other.first
            and self.first.lower() == other.first.lower()
            and (not self.last or not other.last)
        )

    def to_persistable(self) -> dict[str, Any]:
        """Plain-JSON snapshot stored in ``name_candidates`` (debug/calibration)."""
        return {
            "first": self.first,
            "last": self.last,
            "source": self.source,
            "confidence": self.confidence,
            "primary": self.primary,
            "geo_confirmed": self.geo_confirmed,
            "provenance": self.provenance,
        }


@dataclass
class NameResolution:
    """Outcome of the cascade: what to do with the best candidate.

    - ``AUTO``: trusted — written to contact_* and used in emails immediately.
    - ``PROPOSED``: plausible but unproven — surfaced in the drawer for a human
      confirm/reject, NEVER used in an email until confirmed.
    - ``NONE``: nothing trustworthy — neutral « Bonjour » greeting.
    """

    AUTO = "auto"
    PROPOSED = "proposed"
    NONE = "none"

    status: str = NONE
    candidate: NameCandidate | None = None
    #: Every merged candidate (boost applied), kept for the drawer + calibration.
    candidates: list[NameCandidate] = field(default_factory=list)


@dataclass
class ResolutionContext:
    """Inputs shared with every strategy (source-agnostic).

    Built from the prospect row + its enrichment, so the cascade works the same
    whatever scraper originally discovered the prospect.
    """

    company_name: str
    city: str | None = None
    postal_code: str | None = None
    website: str | None = None
    phone: str | None = None
    # Free text already scraped (reviews owner replies, description…) — fuels
    # the extraction strategies without any new network call.
    owner_responses: list[str] = field(default_factory=list)
    description: str | None = None
    #: The company number the prospect search read for the business (SIRET from the RGE register…).
    registry_number: str | None = None


@runtime_checkable
class NameStrategy(Protocol):
    """A pluggable source of decision-maker name candidates."""

    #: Short identifier stored in ``contact_name_source`` (e.g. 'registre_gouv').
    name: str

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Return candidates for this context (empty list when nothing found)."""
        ...  # pragma: no cover — protocol signature
