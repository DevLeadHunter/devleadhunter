"""Shared types of the decision-maker resolution cascade."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


@dataclass
class NameCandidate:
    """One possible decision-maker name proposed by a strategy.

    ``confidence`` is 0..1 — the resolver only retains a candidate above the
    global threshold; anything below falls back to the neutral greeting.
    """

    first: Optional[str] = None
    last: Optional[str] = None
    gender: Optional[str] = None  # 'M' | 'F' | None
    source: str = ""
    confidence: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def has_name(self) -> bool:
        """True when the candidate carries at least a first or last name."""
        return bool(self.first or self.last)

    def identity_key(self) -> str:
        """Comparable key used to detect agreement between sources."""
        from services.decision_maker.normalize import fold

        return f"{fold(self.first or '')}|{fold(self.last or '')}"


@dataclass
class ResolutionContext:
    """Inputs shared with every strategy (source-agnostic).

    Built from the prospect row + its enrichment, so the cascade works the same
    whatever scraper originally discovered the prospect.
    """

    company_name: str
    city: Optional[str] = None
    postal_code: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    # Free text already scraped (reviews owner replies, description…) — fuels
    # the extraction strategies without any new network call.
    owner_responses: list[str] = field(default_factory=list)
    description: Optional[str] = None


@runtime_checkable
class NameStrategy(Protocol):
    """A pluggable source of decision-maker name candidates."""

    #: Short identifier stored in ``contact_name_source`` (e.g. 'registre_gouv').
    name: str

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Return candidates for this context (empty list when nothing found)."""
        ...  # pragma: no cover — protocol signature
