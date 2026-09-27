"""One tracking key per prospect across the two modules' demo pages.

The demo host tracks both modules' pages (a site, a receptionist and their videos) by slug, and the
API reads a prospect's behaviour back by that slug. Each module keeps its slugs unique on its own
table, so without this guard a new receptionist could take the slug of another prospect's site
(and the reverse) and mix their visits.
"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.ai_assistant import AiAssistant
from models.demo_site import DemoSite


class DemoSlugGuard:
    """Keeps a new demo slug away from the demos of other prospects, whatever their module."""

    @staticmethod
    def is_used_by_another_prospect(db: Session, slug: str, prospect_id: int | None) -> bool:
        """
        Whether a site or a receptionist of another prospect already holds this slug.

        A site and a receptionist of the same prospect may share it: their visits are that prospect's either way.

        Args:
            db: Active database session.
            slug: The candidate slug.
            prospect_id: The prospect the new demo is for; without one, any holder counts as another prospect.

        Returns:
            True when a demo of another prospect, or of no prospect, holds the slug.
        """
        for model in (DemoSite, AiAssistant):
            holders = db.query(model.id).filter(model.slug == slug)
            if prospect_id is not None:
                holders = holders.filter(or_(model.prospect_id.is_(None), model.prospect_id != prospect_id))
            if holders.first() is not None:
                return True
        return False
