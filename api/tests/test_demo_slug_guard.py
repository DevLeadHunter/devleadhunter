"""Two prospects never share a demo slug across the site and another module; one prospect's site and module demo
may."""

from datetime import UTC, datetime, timedelta
from typing import ClassVar

from sqlalchemy.orm import Session

from core.product_modules.contract import ProductModule
from core.product_modules.registry import product_module_registry
from models.demo_site import DemoSite
from services.demo_site_service import demo_site_service
from services.demo_slug_guard import DemoSlugGuard


class _AnotherModule(ProductModule):
    """A product module holding the « toitures-morel » demo of prospect 1."""

    key: ClassVar[str] = "another-module"
    label: ClassVar[str] = "Autre module"

    def is_demo_slug_taken(self, db: Session, slug: str, *, prospect_id: int | None) -> bool:
        """Whether the slug is « toitures-morel » and the new demo is not prospect 1's."""
        return slug == "toitures-morel" and prospect_id != 1


def _site(db: Session, *, slug: str, prospect_id: int | None) -> DemoSite:
    site = DemoSite(
        user_id=7,
        prospect_id=prospect_id,
        slug=slug,
        business_name="Garage Martin",
        status="active",
        expires_at=datetime.now(UTC) + timedelta(days=21),
    )
    db.add(site)
    db.commit()
    return site


def test_a_site_never_takes_another_prospects_module_demo_slug(db: Session) -> None:
    product_module_registry.use([_AnotherModule()])

    assert demo_site_service.unique_slug(db, "Toitures Morel", 1) == "toitures-morel"
    assert demo_site_service.unique_slug(db, "Toitures Morel", 2) == "toitures-morel-2"


def test_a_demo_without_prospect_holds_its_slug_against_every_prospect(db: Session) -> None:
    _site(db, slug="cabinet-meyer", prospect_id=None)

    assert DemoSlugGuard.is_used_by_another_prospect(db, "cabinet-meyer", 3)
    assert DemoSlugGuard.is_used_by_another_prospect(db, "cabinet-meyer", None)
    assert not DemoSlugGuard.is_used_by_another_prospect(db, "cabinet-meyer-2", 3)
