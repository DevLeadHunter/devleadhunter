"""The old link of a withdrawn demo serves the demo regenerated for the same prospect (26 Nov 2026).

Flo Jardinier answered « the site interests me » on the day his demo was withdrawn. The demo regenerated for him
got the slug ``flo-jardinier-2``, because the withdrawn row keeps ``flo-jardinier``: the link of his three mails
still showed « Ce lien n'est plus actif ».
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from services.demo_site_service import demo_site_service

_NOW = datetime.now(UTC)
_PROSPECT_ID = 441


def _demo(
    db: Session,
    slug: str,
    status: DemoSiteStatus,
    *,
    prospect_id: int | None = _PROSPECT_ID,
    is_past_its_date: bool = False,
) -> DemoSite:
    is_offline: bool = status in (DemoSiteStatus.DELETED, DemoSiteStatus.EXPIRED, DemoSiteStatus.DELIVERED)
    site = DemoSite(
        user_id=1,
        prospect_id=prospect_id,
        slug=slug,
        business_name="Flo Jardinier",
        template_id="landscaper-verdure",
        status=status.value,
        content_json=None if status is DemoSiteStatus.DELETED else {"businessName": slug},
        demo_link_sent_at=_NOW - timedelta(days=22) if is_offline or is_past_its_date else None,
        expires_at=_NOW - timedelta(days=1) if is_offline or is_past_its_date else _NOW + timedelta(days=21),
    )
    db.add(site)
    db.commit()
    return site


@pytest.mark.parametrize("withdrawn_status", [DemoSiteStatus.DELETED, DemoSiteStatus.EXPIRED])
def test_the_old_link_of_a_withdrawn_demo_serves_the_regenerated_one(
    db: Session, withdrawn_status: DemoSiteStatus
) -> None:
    _demo(db, "flo-jardinier", withdrawn_status)
    regenerated = _demo(db, "flo-jardinier-2", DemoSiteStatus.ACTIVE)

    served = demo_site_service.get_public_by_slug(db, "flo-jardinier")

    assert served is not None
    assert served.id == regenerated.id
    assert demo_site_service.get_public_by_slug(db, "flo-jardinier-2").id == regenerated.id


def test_the_newest_regenerated_demo_is_the_one_served(db: Session) -> None:
    _demo(db, "flo-jardinier", DemoSiteStatus.DELETED)
    _demo(db, "flo-jardinier-2", DemoSiteStatus.ACTIVE)
    newest = _demo(db, "flo-jardinier-3", DemoSiteStatus.ACTIVE)

    assert demo_site_service.get_public_by_slug(db, "flo-jardinier").id == newest.id


def test_the_old_link_stays_dead_when_nothing_was_regenerated(db: Session) -> None:
    _demo(db, "flo-jardinier", DemoSiteStatus.DELETED)

    assert demo_site_service.get_public_by_slug(db, "flo-jardinier") is None


def test_the_old_link_never_serves_the_demo_of_another_prospect(db: Session) -> None:
    _demo(db, "flo-jardinier", DemoSiteStatus.DELETED)
    _demo(db, "garage-bel-air", DemoSiteStatus.ACTIVE, prospect_id=387)
    _demo(db, "demo-sans-prospect", DemoSiteStatus.ACTIVE, prospect_id=None)

    assert demo_site_service.get_public_by_slug(db, "flo-jardinier") is None


def test_a_withdrawn_demo_without_prospect_serves_nothing(db: Session) -> None:
    _demo(db, "ancienne-demo", DemoSiteStatus.DELETED, prospect_id=None)
    _demo(db, "autre-demo", DemoSiteStatus.ACTIVE, prospect_id=None)

    assert demo_site_service.get_public_by_slug(db, "ancienne-demo") is None


def test_the_old_link_stays_dead_when_the_regenerated_demo_is_past_its_date(db: Session) -> None:
    _demo(db, "flo-jardinier", DemoSiteStatus.DELETED)
    _demo(db, "flo-jardinier-2", DemoSiteStatus.ACTIVE, is_past_its_date=True)

    assert demo_site_service.get_public_by_slug(db, "flo-jardinier") is None


def test_the_demo_link_of_a_sold_site_serves_no_other_demo(db: Session) -> None:
    _demo(db, "flo-jardinier", DemoSiteStatus.DELIVERED)
    _demo(db, "flo-jardinier-2", DemoSiteStatus.ACTIVE)

    assert demo_site_service.get_public_by_slug(db, "flo-jardinier") is None
