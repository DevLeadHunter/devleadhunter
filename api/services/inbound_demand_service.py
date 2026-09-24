"""
« Demande entrante » score of a prospect, for the Réceptionniste IA sourcing.

The receptionist sells to a business that receives more requests than it answers.
Nothing measures that directly, so the score adds up the proxies the sourcing uses:
a target trade that works on quotes, the volume of Google reviews (clients who
write in), opening hours past office hours, and no chat already answering on its
site. Each signal carries its points so the dashboard can show why a prospect
ranks high. Recent-review dates are not captured anywhere, so the review volume
stands in for them.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from enums.website_status import WebsiteStatus
from models.prospect import InboundDemand, InboundDemandSignal
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from services.sourcing_verticals import SourcingVerticalCatalog


@dataclass(frozen=True)
class InboundDemandInputs:
    """What the score reads about one prospect."""

    category: str | None
    reviews_count: int | None
    opening_hours: list[dict[str, str]] | None
    has_working_website: bool
    # None = the website was never scanned.
    chat_providers: list[str] | None


class InboundDemandScorer:
    """Scores the inbound demand of a prospect from 0 to 100, signal by signal."""

    TARGET_VERTICAL_POINTS = 35
    QUOTE_TRADE_POINTS = 20
    MAX_REVIEW_POINTS = 35
    # 17.5 × log10(1 + n): 5 reviews → 14, 20 → 23, 50 → 30, 100 and more → 35.
    REVIEW_POINTS_FACTOR = 17.5
    WEEKEND_DAY_POINTS = 5
    EXTENDED_HOURS_POINTS = 5
    NO_CHAT_POINTS = 15

    # Trades outside the target waves that still work on quotes (a request is worth money).
    # The trades set aside by the targeting (serruriers, déménageurs…) are left out on purpose.
    QUOTE_TRADE_STEMS: ClassVar[tuple[str, ...]] = (
        "plomb",
        "chauffag",
        "electric",
        "menuis",
        "paysag",
        "espaces verts",
        "macon",
        "peintre",
        "peinture",
        "carrel",
        "piscin",
        "cuisin",
        "isolation",
        "terrass",
        "elag",
        "garage",
        "mecani",
        "vitr",
        "photograph",
        "diagnost",
    )

    SATURDAY_NAMES: ClassVar[tuple[str, ...]] = ("samedi", "saturday", "zaterdag", "samstag")
    SUNDAY_NAMES: ClassVar[tuple[str, ...]] = ("dimanche", "sunday", "zondag", "sonntag")
    CLOSED_MARKERS: ClassVar[tuple[str, ...]] = ("ferme", "closed", "gesloten", "geschlossen")

    _TIME_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"\b(\d{1,2})\s*[:h]\s*(\d{2})?")
    # 19:00 or later, or before 05:00 (a closing time past midnight), counts as late.
    _LATE_FROM_MINUTES = 19 * 60
    _NIGHT_UNTIL_MINUTES = 5 * 60
    _EARLY_UNTIL_MINUTES = 7 * 60 + 30

    @classmethod
    def score(cls, inputs: InboundDemandInputs) -> InboundDemand:
        """
        Score one prospect.

        Args:
            inputs: What is known about the prospect.

        Returns:
            The 0-100 score and the signals that make it up.
        """
        signals = [
            *cls._trade_signals(inputs.category),
            *cls._review_signals(inputs.reviews_count),
            *cls._hours_signals(inputs.opening_hours),
            *cls._chat_signals(inputs.has_working_website, inputs.chat_providers),
        ]
        return InboundDemand(score=min(100, sum(signal.points for signal in signals)), signals=signals)

    @classmethod
    def _trade_signals(cls, category: str | None) -> list[InboundDemandSignal]:
        """A target vertical scores highest; another quote-based trade scores less."""
        vertical = SourcingVerticalCatalog.match(category)
        if vertical is not None:
            label = f"Métier cible, vague {vertical.wave} : {vertical.label.lower()}"
            return [InboundDemandSignal(label=label, points=cls.TARGET_VERTICAL_POINTS)]
        normalized = SourcingVerticalCatalog.normalize(category or "")
        if any(stem in normalized for stem in cls.QUOTE_TRADE_STEMS):
            return [InboundDemandSignal(label="Métier à devis", points=cls.QUOTE_TRADE_POINTS)]
        return []

    @classmethod
    def _review_signals(cls, reviews_count: int | None) -> list[InboundDemandSignal]:
        """Review volume on a log scale: the first reviews matter most."""
        if reviews_count is None:
            return [InboundDemandSignal(label="Nombre d'avis Google inconnu", points=0)]
        points = min(cls.MAX_REVIEW_POINTS, round(cls.REVIEW_POINTS_FACTOR * math.log10(1 + max(reviews_count, 0))))
        label = f"{reviews_count} avis Google" if reviews_count != 1 else "1 avis Google"
        return [InboundDemandSignal(label=label, points=points)]

    @classmethod
    def _hours_signals(cls, opening_hours: list[dict[str, str]] | None) -> list[InboundDemandSignal]:
        """Open on Saturday, on Sunday, and early or late in the day."""
        if not opening_hours:
            return []
        signals: list[InboundDemandSignal] = []
        if cls._is_open_on(opening_hours, cls.SATURDAY_NAMES):
            signals.append(InboundDemandSignal(label="Ouvert le samedi", points=cls.WEEKEND_DAY_POINTS))
        if cls._is_open_on(opening_hours, cls.SUNDAY_NAMES):
            signals.append(InboundDemandSignal(label="Ouvert le dimanche", points=cls.WEEKEND_DAY_POINTS))
        if cls._has_extended_hours(opening_hours):
            signals.append(InboundDemandSignal(label="Horaires tôt ou tard", points=cls.EXTENDED_HOURS_POINTS))
        return signals

    @classmethod
    def _chat_signals(cls, has_working_website: bool, chat_providers: list[str] | None) -> list[InboundDemandSignal]:
        """No chat in place leaves the requests unanswered; an existing one takes the gap."""
        if not has_working_website:
            return [InboundDemandSignal(label="Pas de site : aucun chat en place", points=cls.NO_CHAT_POINTS)]
        if chat_providers is None:
            return [InboundDemandSignal(label="Site pas encore analysé", points=0)]
        if chat_providers:
            return [InboundDemandSignal(label="Déjà équipé d'un chat", points=0)]
        return [InboundDemandSignal(label="Aucun chat sur son site", points=cls.NO_CHAT_POINTS)]

    @classmethod
    def _is_open_on(cls, opening_hours: list[dict[str, str]], day_names: tuple[str, ...]) -> bool:
        """Whether a row for one of these day names shows actual hours."""
        for row in opening_hours:
            if not isinstance(row, dict):
                continue
            day = SourcingVerticalCatalog.normalize(str(row.get("day") or ""))
            if not day.startswith(day_names):
                continue
            hours = SourcingVerticalCatalog.normalize(str(row.get("hours") or ""))
            if any(char.isdigit() for char in hours) and not any(marker in hours for marker in cls.CLOSED_MARKERS):
                return True
        return False

    @classmethod
    def _has_extended_hours(cls, opening_hours: list[dict[str, str]]) -> bool:
        """Whether any day opens by 07:30, closes at 19:00 or later, or runs 24 hours."""
        for row in opening_hours:
            if not isinstance(row, dict):
                continue
            hours = SourcingVerticalCatalog.normalize(str(row.get("hours") or ""))
            if "24h" in hours.replace(" ", "") or "24 heures" in hours:
                return True
            for match in cls._TIME_PATTERN.finditer(hours):
                minutes = int(match.group(1)) * 60 + int(match.group(2) or 0)
                if minutes >= cls._LATE_FROM_MINUTES or minutes < cls._NIGHT_UNTIL_MINUTES:
                    return True
                if minutes <= cls._EARLY_UNTIL_MINUTES:
                    return True
        return False


class InboundDemandService:
    """Scores a batch of prospects with their enrichment data, in one query."""

    _BROKEN_WEBSITE_STATUSES: ClassVar[frozenset[str]] = frozenset(
        {WebsiteStatus.DEAD.value, WebsiteStatus.PLACEHOLDER.value}
    )

    @classmethod
    def score_prospects(cls, db: Session, prospects: list[ProspectDB]) -> dict[int, InboundDemand]:
        """
        Score prospects, reading their enrichment (reviews, hours) when they have one.

        Enrichment figures win over the ones read at discovery: they are fresher.

        Args:
            db: Active database session.
            prospects: Rows to score.

        Returns:
            Each prospect id mapped to its score.
        """
        if not prospects:
            return {}
        rows = db.execute(
            select(
                ProspectEnrichment.prospect_id,
                ProspectEnrichment.reviews_count,
                ProspectEnrichment.opening_hours,
            ).where(ProspectEnrichment.prospect_id.in_([prospect.id for prospect in prospects]))
        ).all()
        enrichment_by_id = {row[0]: (row[1], row[2]) for row in rows}

        scores: dict[int, InboundDemand] = {}
        for prospect in prospects:
            enriched_reviews, opening_hours = enrichment_by_id.get(prospect.id, (None, None))
            equipment = prospect.website_equipment_json
            scores[prospect.id] = InboundDemandScorer.score(
                InboundDemandInputs(
                    category=prospect.category,
                    reviews_count=enriched_reviews if enriched_reviews is not None else prospect.google_reviews_count,
                    opening_hours=opening_hours if isinstance(opening_hours, list) else None,
                    has_working_website=bool(prospect.website and prospect.website.strip())
                    and prospect.website_status not in cls._BROKEN_WEBSITE_STATUSES,
                    chat_providers=list(equipment.get("chat_providers") or []) if isinstance(equipment, dict) else None,
                )
            )
        return scores
