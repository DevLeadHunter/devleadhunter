"""The « personalise again » route answers with the site as the dashboard reads it, its video compared with the clip."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.v1.routes.demo_sites import router as demo_sites_router
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


def _site(db: Session) -> DemoSite:
    site = DemoSite(
        user_id=_USER_ID,
        slug="plomberie-du-canal",
        business_name="Plomberie du Canal",
        template_id="artisan-edito",
        status=DemoSiteStatus.ACTIVE.value,
        demo_url="https://demo.example.com/plomberie-du-canal",
        expires_at=datetime.now(UTC) + timedelta(days=21),
    )
    db.add(site)
    db.commit()
    return site


def test_the_personalised_site_comes_back_as_the_dashboard_reads_it(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = _site(db)

    async def personalise_again(_db: Session, demo_site: DemoSite) -> DemoSite:
        demo_site.description = "Plombier du quartier depuis vingt ans."
        return demo_site

    monkeypatch.setattr(demo_site_service, "repersonalize_demo_site", personalise_again)

    response = _client(db).post(f"{demo_sites_router.prefix}/{site.id}/personalize")

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Plombier du quartier depuis vingt ans."
    assert body["is_video_made_with_older_clip"] is False


def test_a_site_that_cannot_be_personalised_is_refused(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    site = _site(db)

    async def refuse(_db: Session, _demo_site: DemoSite) -> DemoSite:
        raise ValueError("Ce site ne peut pas être personnalisé automatiquement pour le moment.")

    monkeypatch.setattr(demo_site_service, "repersonalize_demo_site", refuse)

    response = _client(db).post(f"{demo_sites_router.prefix}/{site.id}/personalize")

    assert response.status_code == 400
    assert response.json()["detail"] == "Ce site ne peut pas être personnalisé automatiquement pour le moment."
