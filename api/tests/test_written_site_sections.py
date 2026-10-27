"""
The FAQ, the trust markers and the facts under the title written for a business are site overrides:
they survive regenerations, and an empty list goes back to the generated ones.
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
from services.templates.site_content import (
    MAX_TRUST_ITEMS,
    apply_section_overrides,
    clean_faq_items,
    clean_trust_items,
)

_USER_ID = 1

_FAQ = [
    {"question": "Faites-vous la carrosserie ?", "answer": "Non, nous travaillons avec des partenaires."},
    {"question": "Avez-vous une voiture de courtoisie ?", "answer": "Oui, pendant les travaux."},
]


def test_a_question_without_its_answer_is_dropped() -> None:
    cleaned = clean_faq_items(
        [
            {"question": "  Faites-vous   la carrosserie ? ", "answer": "Non."},
            {"question": "Et le week-end ?", "answer": "  "},
            "not a question",
        ]
    )

    assert cleaned == [{"question": "Faites-vous la carrosserie ?", "answer": "Non."}]


def test_trust_markers_need_a_value_or_a_label_and_stay_capped() -> None:
    markers = [{"value": "Sàrl", "label": "Inscrite au registre du commerce"}, {"value": " ", "label": ""}]
    markers += [{"value": f"{index}", "label": "Repère"} for index in range(MAX_TRUST_ITEMS + 2)]

    cleaned = clean_trust_items(markers)

    assert cleaned[0] == {"value": "Sàrl", "label": "Inscrite au registre du commerce"}
    assert len(cleaned) == MAX_TRUST_ITEMS


def test_the_written_sections_replace_the_generated_ones() -> None:
    content = {
        "heroPoints": ["Devis avant réparation"],
        "trustItems": [{"value": "Devis gratuit", "label": "Sans engagement"}],
        "faq": [{"question": "Le devis est-il gratuit ?", "answer": "Oui."}],
    }

    result = apply_section_overrides(
        content,
        {
            "heroPoints": ["Préparation aux expertises"],
            "trustItems": [{"value": "Sàrl", "label": "Inscrite au registre du commerce"}],
            "faq": _FAQ,
        },
    )

    assert result["heroPoints"] == ["Préparation aux expertises"]
    assert result["trustItems"] == [{"value": "Sàrl", "label": "Inscrite au registre du commerce"}]
    assert result["faq"] == _FAQ


def test_the_tax_credit_question_joins_a_written_faq() -> None:
    tax_credit = {
        "heading": "Votre entretien de jardin à moitié prix",
        "faqQuestion": "Puis-je bénéficier du crédit d'impôt de 50 % ?",
        "faqAnswer": "Oui, sur l'entretien courant du jardin.",
    }

    result = apply_section_overrides({"faq": []}, {"faq": _FAQ, "taxCredit": tax_credit})

    assert [item["question"] for item in result["faq"]] == [
        "Faites-vous la carrosserie ?",
        "Avez-vous une voiture de courtoisie ?",
        "Puis-je bénéficier du crédit d'impôt de 50 % ?",
    ]


def _client(db: Session) -> TestClient:
    application = FastAPI()
    application.include_router(demo_sites_router)
    signed_in_user = SimpleNamespace(id=_USER_ID, email="owner@example.com")
    application.dependency_overrides[get_current_active_user] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def _garage_site(db: Session) -> DemoSite:
    site = DemoSite(
        user_id=_USER_ID,
        slug="tp-motorsport",
        business_name="TP Motorsport Sàrl",
        template_id="mechanic-pitlane",
        status=DemoSiteStatus.ACTIVE.value,
        content_json={"businessName": "TP Motorsport Sàrl"},
        section_overrides={"about": "Garage de Savièse."},
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


def test_the_written_sections_are_saved_and_an_empty_list_removes_them(
    db: Session, site_rebuilt_without_cms: None
) -> None:
    site = _garage_site(db)
    client = _client(db)

    saved = client.patch(
        f"{demo_sites_router.prefix}/{site.id}",
        json={
            "hero_points": ["Préparation aux expertises", " "],
            "trust_items": [{"value": "Sàrl", "label": "Inscrite au registre du commerce"}],
            "faq": _FAQ,
        },
    )

    assert saved.status_code == 200
    db.refresh(site)
    assert site.section_overrides == {
        "about": "Garage de Savièse.",
        "heroPoints": ["Préparation aux expertises"],
        "trustItems": [{"value": "Sàrl", "label": "Inscrite au registre du commerce"}],
        "faq": _FAQ,
    }

    removed = client.patch(f"{demo_sites_router.prefix}/{site.id}", json={"faq": [], "hero_points": []})

    assert removed.status_code == 200
    db.refresh(site)
    assert site.section_overrides == {
        "about": "Garage de Savièse.",
        "trustItems": [{"value": "Sàrl", "label": "Inscrite au registre du commerce"}],
    }
