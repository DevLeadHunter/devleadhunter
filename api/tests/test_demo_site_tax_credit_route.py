"""
The dashboard reads a site's « crédit d'impôt » section from the site's own response, saves it through the
same PATCH as the other edits, and learns from the template catalogue which templates render the section.
"""

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

_STORED_SECTION = {
    "heading": "Votre entretien de jardin à moitié prix",
    "lead": "La moitié de la facture vous revient.",
    "points": ["50 % remboursés", "Attestation fournie"],
    "note": "Plafond de 5 000 € par an.",
    "faqQuestion": "Puis-je bénéficier du crédit d'impôt de 50 % ?",
    "faqAnswer": "Oui, sur l'entretien courant du jardin.",
}


def _client(db: Session) -> TestClient:
    application = FastAPI()
    application.include_router(demo_sites_router)
    signed_in_user = SimpleNamespace(id=_USER_ID, email="owner@example.com")
    application.dependency_overrides[get_current_active_user] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def _landscaper_site(db: Session, section_overrides: dict | None) -> DemoSite:
    site = DemoSite(
        user_id=_USER_ID,
        slug="bearn-services-exterieurs",
        business_name="Béarn Services Extérieurs",
        template_id="landscaper-verdure",
        status=DemoSiteStatus.ACTIVE.value,
        content_json={"businessName": "Béarn Services Extérieurs"},
        section_overrides=section_overrides,
        expires_at=datetime.now(UTC) + timedelta(days=10),
    )
    db.add(site)
    db.commit()
    return site


@pytest.fixture
def site_rebuilt_without_cms(monkeypatch: pytest.MonkeyPatch) -> None:
    """A save keeps the overrides and skips the Storyblok sync and the URL check."""

    async def rebuild(database: Session, demo_site: DemoSite) -> DemoSite:
        database.commit()
        database.refresh(demo_site)
        return demo_site

    monkeypatch.setattr(demo_site_service, "regenerate_demo_site", rebuild)


def test_the_site_response_carries_its_tax_credit_section(db: Session) -> None:
    site = _landscaper_site(db, {"taxCredit": _STORED_SECTION, "heroBadge": "Paysagiste"})

    response = _client(db).get(f"{demo_sites_router.prefix}/{site.id}")

    assert response.status_code == 200
    assert response.json()["tax_credit"] == {
        "heading": "Votre entretien de jardin à moitié prix",
        "lead": "La moitié de la facture vous revient.",
        "points": ["50 % remboursés", "Attestation fournie"],
        "note": "Plafond de 5 000 € par an.",
        "faq_question": "Puis-je bénéficier du crédit d'impôt de 50 % ?",
        "faq_answer": "Oui, sur l'entretien courant du jardin.",
    }


def test_a_site_without_the_section_says_so(db: Session) -> None:
    site = _landscaper_site(db, {"heroBadge": "Paysagiste"})

    response = _client(db).get(f"{demo_sites_router.prefix}/{site.id}")

    assert response.status_code == 200
    assert response.json()["tax_credit"] is None


def test_a_saved_section_reads_back_and_an_empty_heading_removes_it(
    db: Session, site_rebuilt_without_cms: None
) -> None:
    site = _landscaper_site(db, None)
    client = _client(db)

    saved = client.patch(
        f"{demo_sites_router.prefix}/{site.id}",
        json={
            "tax_credit": {
                "heading": " Votre entretien de jardin à moitié prix ",
                "points": ["50 % remboursés", ""],
                "faq_question": "Puis-je bénéficier du crédit d'impôt de 50 % ?",
                "faq_answer": "Oui, sur l'entretien courant du jardin.",
            }
        },
    )

    assert saved.status_code == 200
    assert saved.json()["tax_credit"] == {
        "heading": "Votre entretien de jardin à moitié prix",
        "lead": "",
        "points": ["50 % remboursés"],
        "note": "",
        "faq_question": "Puis-je bénéficier du crédit d'impôt de 50 % ?",
        "faq_answer": "Oui, sur l'entretien courant du jardin.",
    }

    removed = client.patch(f"{demo_sites_router.prefix}/{site.id}", json={"tax_credit": {"heading": ""}})

    assert removed.status_code == 200
    assert removed.json()["tax_credit"] is None
    db.refresh(site)
    assert site.section_overrides is None


def test_the_catalogue_tells_which_templates_render_the_section(db: Session) -> None:
    response = _client(db).get(f"{demo_sites_router.prefix}/templates")

    assert response.status_code == 200
    renders_by_id = {template["id"]: template["renders_tax_credit_section"] for template in response.json()}
    assert renders_by_id["landscaper-verdure"] is True
    assert renders_by_id["plumber-signature"] is False
    assert renders_by_id["artisan-edito"] is False
