"""
The old link of a demo taken offline at its deadline lets its prospect bring it back online himself; any
other dead link (deleted demo, prospect who asked to be left alone, live demo) offers nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.v1.routes.demo_sites import router as demo_sites_router
from core.config import settings
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from services.demo_site_service import demo_site_service

_USER_ID = 1


def _client(db: Session) -> TestClient:
    application = FastAPI()
    application.include_router(demo_sites_router)
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def _site(db: Session, status: str, *, do_not_contact: bool = False) -> DemoSite:
    prospect = ProspectDB(
        user_id=_USER_ID,
        name="TP Motorsport",
        category="garage",
        source="google_maps",
        do_not_contact=do_not_contact,
    )
    db.add(prospect)
    db.flush()
    site = DemoSite(
        user_id=_USER_ID,
        prospect_id=prospect.id,
        slug="tp-motorsport",
        business_name="TP Motorsport",
        template_id="mechanic-pitlane",
        status=status,
        demo_url="https://demo.example.com/tp-motorsport",
        content_json={"businessName": "TP Motorsport"},
        demo_link_sent_at=datetime(2026, 10, 1, 9, 0),
        expires_at=datetime(2026, 10, 22, 9, 0),
    )
    db.add(site)
    db.commit()
    return site


@pytest.fixture
def images_kept_where_they_are(monkeypatch: pytest.MonkeyPatch) -> None:
    async def keep(_site: DemoSite) -> None:
        return None

    monkeypatch.setattr(demo_site_service, "persist_content_images_to_r2", keep)


def test_an_expired_demo_link_offers_to_bring_it_back(db: Session) -> None:
    _site(db, DemoSiteStatus.EXPIRED.value)

    response = _client(db).get(f"{demo_sites_router.prefix}/public/tp-motorsport/withdrawn")

    assert response.status_code == 200
    payload = response.json()
    assert payload["business_name"] == "TP Motorsport"
    assert payload["withdrawn_on_label"] == "22 octobre"
    assert payload["revived_until_label"] == demo_site_service.revived_expiry_date_label()


def test_the_prospect_brings_the_demo_back_online_for_a_full_window(
    db: Session, images_kept_where_they_are: None
) -> None:
    site = _site(db, DemoSiteStatus.EXPIRED.value)

    response = _client(db).post(f"{demo_sites_router.prefix}/public/tp-motorsport/revive")

    assert response.status_code == 204
    db.refresh(site)
    assert site.status == DemoSiteStatus.ACTIVE.value
    remaining = site.expires_at.replace(tzinfo=UTC) - datetime.now(UTC)
    assert timedelta(days=settings.demo_site_ttl_days - 1) < remaining <= timedelta(days=settings.demo_site_ttl_days)


@pytest.mark.parametrize("status", [DemoSiteStatus.DELETED.value, DemoSiteStatus.ACTIVE.value])
def test_a_deleted_or_live_demo_link_offers_nothing(db: Session, status: str) -> None:
    _site(db, status)

    response = _client(db).get(f"{demo_sites_router.prefix}/public/tp-motorsport/withdrawn")

    assert response.status_code == 404


def test_a_prospect_who_asked_to_be_left_alone_keeps_a_dead_link(db: Session, images_kept_where_they_are: None) -> None:
    site = _site(db, DemoSiteStatus.EXPIRED.value, do_not_contact=True)
    client = _client(db)

    assert client.get(f"{demo_sites_router.prefix}/public/tp-motorsport/withdrawn").status_code == 404
    assert client.post(f"{demo_sites_router.prefix}/public/tp-motorsport/revive").status_code == 404
    db.refresh(site)
    assert site.status == DemoSiteStatus.EXPIRED.value
