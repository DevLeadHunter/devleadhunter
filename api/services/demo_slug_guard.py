"""One tracking key per prospect across the demo pages of every module.

The demo host tracks every module's pages (a site and its video, a receptionist…) by slug, and the API reads a
prospect's behaviour back by that slug. Each module keeps its slugs unique on its own table, so without this guard a
new module demo could take the slug of another prospect's site (and the reverse) and mix their visits.
"""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.product_modules.registry import product_module_registry
from models.demo_site import DemoSite


class DemoSlugGuard:
    """Keeps a new demo slug away from the demos of other prospects, whatever their module."""

    @staticmethod
    def is_used_by_another_prospect(db: Session, slug: str, prospect_id: int | None) -> bool:
        """
        Whether a site or a product-module demo of another prospect already holds this slug.

        A site and a module demo of the same prospect may share it: their visits are that prospect's either way.

        Args:
            db: Active database session.
            slug: The candidate slug.
            prospect_id: The prospect the new demo is for; without one, any holder counts as another prospect.

        Returns:
            True when a demo of another prospect, or of no prospect, holds the slug.
        """
        holders = db.query(DemoSite.id).filter(DemoSite.slug == slug)
        if prospect_id is not None:
            holders = holders.filter(or_(DemoSite.prospect_id.is_(None), DemoSite.prospect_id != prospect_id))
        if holders.first() is not None:
            return True
        return any(
            module.is_demo_slug_taken(db, slug, prospect_id=prospect_id)
            for module in product_module_registry.installed()
        )
