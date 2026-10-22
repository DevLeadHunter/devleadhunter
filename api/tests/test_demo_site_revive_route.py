"""A demo past its deadline goes back online for a full new window when a prospect comes back; a live one is refused."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.v1.routes.demo_sites import router as demo_sites_router
from core.config import settings
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from services.auth_service import get_current_active_user
from services.demo_site_service import demo_site_service

_USER_ID = 1


def _client(db: Session) -> TestClient:
    application = FastAPI()
    application.include_router(demo_sites_router)
    signed_in_user = SimpleNamespace(id=_USER_ID, email="owner@example.com")
    application.dependency_overrides[get_current_active_user] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def _site(db: Session, status: str) -> DemoSite:
    site = DemoSite(
        user_id=_USER_ID,
        slug="tp-motorsport",
        business_name="TP Motorsport",
        template_id="mechanic-pitlane",
        status=status,
        demo_url="https://demo.example.com/tp-motorsport",
        content_json={"businessName": "TP Motorsport"},
        expires_at=datetime.now(UTC) - timedelta(days=8),
    )
    db.add(site)
    db.commit()
    return site


@pytest.fixture
def images_kept_where_they_are(monkeypatch: pytest.MonkeyPatch) -> None:
    async def keep(_site: DemoSite) -> None:
        return None

    monkeypatch.setattr(demo_site_service, "persist_content_images_to_r2", keep)


def test_an_expired_demo_goes_back_online_for_a_full_window(db: Session, images_kept_where_they_are: None) -> None:
    site = _site(db, DemoSiteStatus.EXPIRED.value)

    response = _client(db).post(f"{demo_sites_router.prefix}/{site.id}/revive")

    assert response.status_code == 200
    db.refresh(site)
    assert site.status == DemoSiteStatus.ACTIVE.value
    remaining = site.expires_at.replace(tzinfo=UTC) - datetime.now(UTC)
    assert timedelta(days=settings.demo_site_ttl_days - 1) < remaining <= timedelta(days=settings.demo_site_ttl_days)


def test_a_demo_still_online_is_not_revived(db: Session, images_kept_where_they_are: None) -> None:
    site = _site(db, DemoSiteStatus.ACTIVE.value)

    response = _client(db).post(f"{demo_sites_router.prefix}/{site.id}/revive")

    assert response.status_code == 409
    assert response.json()["detail"] == "Cette démo n'est pas retirée."
