"""The public demo payload tells the prospect the owner's price and the withdrawal day, as his emails do."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy.orm import Session

from api.v1.routes.demo_sites import get_public_demo_site, get_public_demo_site_by_domain
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from models.user import User
from services.demo_site_service import _PENDING_TTL_EXPIRES, demo_site_service
from services.templates.default_images import DEFAULT_IMAGES

_UNSENT_EXPIRES_AT: datetime = _PENDING_TTL_EXPIRES.replace(tzinfo=None)
_STILL_ONLINE_SENT_AT: datetime = datetime(2098, 10, 12, 9, 0)
_STILL_ONLINE_EXPIRES_AT: datetime = datetime(2098, 11, 2, 9, 0)


def _owner(db: Session, *, sale_price_cents: int = 50000) -> User:
    owner = User(
        name="Camille Durand",
        email="camille@example.com",
        hashed_password="x",
        site_sale_price_cents=sale_price_cents,
        company_website_url="https://camille-durand.fr",
    )
    db.add(owner)
    db.commit()
    return owner


def _prospect(db: Session, owner: User, country: str) -> ProspectDB:
    prospect = ProspectDB(
        name="Menuiserie Lefort", category="Menuisier", source="google", confidence=2, user_id=owner.id, country=country
    )
    db.add(prospect)
    db.commit()
    return prospect


def _demo(db: Session, owner: User, prospect: ProspectDB | None, **fields: Any) -> DemoSite:
    values: dict[str, Any] = {
        "user_id": owner.id,
        "prospect_id": prospect.id if prospect is not None else None,
        "slug": "menuiserie-lefort",
        "template_id": "artisan-edito",
        "business_name": "Menuiserie Lefort",
        "status": DemoSiteStatus.ACTIVE.value,
        "content_json": {"businessName": "Menuiserie Lefort"},
        "expires_at": _UNSENT_EXPIRES_AT,
    }
    values.update(fields)
    site = DemoSite(**values)
    db.add(site)
    db.commit()
    return site


@pytest.mark.parametrize(
    ("country", "sale_price_cents", "label"),
    [("FR", 50000, "500 €"), ("CH", 50000, "470 CHF"), ("BE", 39000, "390 €")],
)
def test_the_price_is_the_owner_sale_price_in_the_prospect_currency(
    db: Session, country: str, sale_price_cents: int, label: str
) -> None:
    owner = _owner(db, sale_price_cents=sale_price_cents)
    site = _demo(db, owner, _prospect(db, owner, country))

    assert demo_site_service.sale_price_label(db, site) == label


def test_a_demo_without_a_prospect_reads_the_price_in_euros(db: Session) -> None:
    owner = _owner(db)
    site = _demo(db, owner, None)

    assert demo_site_service.sale_price_label(db, site) == "500 €"


def test_the_withdrawal_day_is_the_expiry_once_the_link_was_sent(db: Session) -> None:
    owner = _owner(db)
    sent = _demo(
        db, owner, None, demo_link_sent_at=datetime(2026, 10, 12, 9, 0), expires_at=datetime(2026, 11, 2, 9, 0)
    )
    unsent = _demo(db, owner, None, slug="garage-martin")

    assert demo_site_service.expiry_date_label(sent) == "2 novembre"
    assert demo_site_service.expiry_date_label(unsent) is None


def test_the_public_demo_carries_the_price_and_the_withdrawal_day(db: Session) -> None:
    owner = _owner(db)
    switzerland = _prospect(db, owner, "CH")
    _demo(db, owner, switzerland, demo_link_sent_at=_STILL_ONLINE_SENT_AT, expires_at=_STILL_ONLINE_EXPIRES_AT)
    _demo(db, owner, None, slug="garage-martin")

    sent = asyncio.run(get_public_demo_site("menuiserie-lefort", db))
    unsent = asyncio.run(get_public_demo_site("garage-martin", db))

    assert (sent.sale_price_label, sent.expiry_date_label) == ("470 CHF", "2 novembre")
    assert (unsent.sale_price_label, unsent.expiry_date_label) == ("500 €", None)
    assert (sent.owner_name, sent.owner_company_website_url) == ("Camille Durand", "https://camille-durand.fr")


def test_the_public_site_names_the_business_trade_only_when_its_listing_has_one(db: Session) -> None:
    owner = _owner(db)
    _demo(db, owner, _prospect(db, owner, "FR"))
    _demo(db, owner, None, slug="garage-martin")
    _demo(
        db,
        owner,
        _prospect(db, owner, "FR"),
        slug="menuiserie-lefort-2",
        status=DemoSiteStatus.DELIVERED.value,
        custom_domain="menuiserie-lefort.fr",
    )

    with_listing = asyncio.run(get_public_demo_site("menuiserie-lefort", db))
    without_prospect = asyncio.run(get_public_demo_site("garage-martin", db))
    sold = asyncio.run(get_public_demo_site_by_domain("menuiserie-lefort.fr", db))

    assert (with_listing.business_category, without_prospect.business_category) == ("Menuisier", None)
    assert sold.business_category == "Menuisier"


_STOCK_HERO: str = DEFAULT_IMAGES["landscaper-verdure"]["heroImage"]


@pytest.mark.parametrize(
    ("hero_image", "business_photo_url"),
    [
        ("https://pub-1.r2.dev/prospects/12/photo-1.jpg", "https://pub-1.r2.dev/prospects/12/photo-1.jpg"),
        (
            "https://a.storyblok.com/f/42/1600x900/ab12/real-photo.jpg",
            "https://a.storyblok.com/f/42/1600x900/ab12/real-photo.jpg",
        ),
        (_STOCK_HERO, None),
        (f"https://a.storyblok.com/f/42/1600x900/ab12/{hashlib.sha1(_STOCK_HERO.encode()).hexdigest()[:20]}.jpg", None),
        ("https://images.unsplash.com/photo-1600488999585?auto=format&w=1600", None),
        ("", None),
    ],
)
def test_the_header_photo_is_named_only_when_it_shows_the_business(
    db: Session, hero_image: str, business_photo_url: str | None
) -> None:
    owner = _owner(db)
    _demo(db, owner, None, content_json={"businessName": "Menuiserie Lefort", "heroImage": hero_image})

    site = asyncio.run(get_public_demo_site("menuiserie-lefort", db))

    assert site.business_photo_url == business_photo_url


def test_a_sold_site_on_its_own_domain_carries_no_offer(db: Session) -> None:
    owner = _owner(db)
    _demo(
        db,
        owner,
        _prospect(db, owner, "FR"),
        status=DemoSiteStatus.DELIVERED.value,
        custom_domain="menuiserie-lefort.fr",
        demo_link_sent_at=datetime(2026, 9, 1, 9, 0),
    )

    sold = asyncio.run(get_public_demo_site_by_domain("menuiserie-lefort.fr", db))

    assert (sold.sale_price_label, sold.expiry_date_label) == (None, None)
