"""
The title, the sentence under it, the quote button, the section titles and leads, the contact banner and the « Notre
méthode » steps written for a business are site overrides: they win over the template's texts, survive regenerations,
follow the client's CMS edits, and an empty value goes back to the generated ones.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import services.demo_site_service as demo_site_module
from api.v1.routes.demo_sites import router as demo_sites_router
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from services.auth_service import get_current_active_user
from services.demo_site_service import demo_site_service
from services.storyblok_service import storyblok_service
from services.templates import registry
from services.templates.site_content import (
    MAX_STEPS,
    apply_section_overrides,
    clean_step_items,
    from_storyblok_site_content,
    overrides_from_published_story,
)

_USER_ID = 1
_FENCE_TITLE = "Clôtures, portails et soubassements posés avec soin"
_STEPS = [
    {"title": "Visite du terrain", "description": "Nous mesurons le linéaire et regardons la nature du sol."},
    {"title": "Pose", "description": ""},
]
_WRITTEN_TEXTS: dict[str, Any] = {
    "heroTitle": _FENCE_TITLE,
    "subtitle": "Poseur de clôtures à Bavilliers : grillage rigide, panneaux occultants et portails.",
    "ctaQuoteLabel": "Demander un devis",
    "servicesHeading": "Vos clôtures, de la vente à la pose",
    "servicesLead": "De la clôture de jardin au portail, un seul poseur du devis à la dernière vis.",
    "aboutHeading": "Un poseur de clôtures à Bavilliers",
    "ctaTitle": "Un projet de clôture ?",
    "ctaLead": "Décrivez votre terrain, nous revenons vers vous avec un devis gratuit.",
    "contactHeading": "Votre clôture, parlons-en",
    "contactLead": "Appelez-nous ou laissez vos coordonnées : nous vous rappelons pour en parler.",
    "steps": _STEPS,
}


def test_a_step_needs_a_title_and_the_steps_stay_capped() -> None:
    steps: list[Any] = [
        {"title": "  Visite   du terrain ", "description": " Nous mesurons le linéaire. "},
        {"title": " ", "description": "Sans titre."},
        "not a step",
    ]
    steps += [{"title": f"Étape {index}"} for index in range(MAX_STEPS + 2)]

    cleaned = clean_step_items(steps)

    assert cleaned[:2] == [
        {"title": "Visite du terrain", "description": "Nous mesurons le linéaire."},
        {"title": "Étape 0", "description": ""},
    ]
    assert len(cleaned) == MAX_STEPS


@pytest.mark.parametrize("template_id", ["mechanic-pitlane", "landscaper-verdure", "electrician-eclat"])
def test_the_written_texts_replace_the_generated_ones_whatever_the_template(template_id: str) -> None:
    generated = storyblok_service.build_content_json(
        business_name="BS Grillages",
        phone="06 12 34 56 78",
        email=None,
        city="Bavilliers",
        description=None,
        template_id=template_id,
    )

    result = apply_section_overrides(generated, _WRITTEN_TEXTS)

    assert {key: result.get(key) for key in _WRITTEN_TEXTS} == _WRITTEN_TEXTS


def test_a_written_title_wins_over_the_title_a_template_words_from_the_city() -> None:
    generated = storyblok_service.build_content_json(
        business_name="Élec Sarthe",
        phone=None,
        email=None,
        city="Le Mans",
        description=None,
        template_id="electrician-eclat",
    )
    assert generated["heroTitle"] == "Votre électricien au Mans"

    result = apply_section_overrides(generated, {"heroTitle": " Électricien au Mans depuis 1998 "})

    assert result["heroTitle"] == "Électricien au Mans depuis 1998"


def _client(db: Session) -> TestClient:
    application = FastAPI()
    application.include_router(demo_sites_router)
    signed_in_user = SimpleNamespace(id=_USER_ID, email="owner@example.com")
    application.dependency_overrides[get_current_active_user] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def _fence_site(db: Session) -> DemoSite:
    site = DemoSite(
        user_id=_USER_ID,
        slug="bs-grillages",
        business_name="BS Grillages",
        template_id="landscaper-verdure",
        city="Bavilliers",
        status=DemoSiteStatus.ACTIVE.value,
        content_json={"businessName": "BS Grillages"},
        section_overrides={"about": "Poseur de clôtures à Bavilliers."},
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


@pytest.fixture
def site_verified_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """A regeneration builds the real content, but checks no address and writes no activity."""

    async def live(database: Session, demo_site: DemoSite) -> SimpleNamespace:
        return SimpleNamespace(
            public_api_ok=True, demo_url_live=True, local_demo_url=None, local_demo_url_live=False, message="OK"
        )

    monkeypatch.setattr(demo_site_module.demo_site_verification_service, "verify", live)
    monkeypatch.setattr(demo_site_module.activity_log_service, "record", lambda **entry: None)


def test_the_written_texts_are_saved_and_an_empty_value_removes_them(
    db: Session, site_rebuilt_without_cms: None
) -> None:
    site = _fence_site(db)
    client = _client(db)

    saved = client.patch(
        f"{demo_sites_router.prefix}/{site.id}",
        json={
            "hero_title": f"  {_FENCE_TITLE} ",
            "hero_subtitle": _WRITTEN_TEXTS["subtitle"],
            "cta_quote_label": _WRITTEN_TEXTS["ctaQuoteLabel"],
            "services_heading": _WRITTEN_TEXTS["servicesHeading"],
            "services_lead": _WRITTEN_TEXTS["servicesLead"],
            "about_heading": _WRITTEN_TEXTS["aboutHeading"],
            "steps": [*_STEPS, {"title": " ", "description": "Sans titre."}],
            "cta_title": _WRITTEN_TEXTS["ctaTitle"],
            "cta_lead": _WRITTEN_TEXTS["ctaLead"],
            "contact_heading": _WRITTEN_TEXTS["contactHeading"],
            "contact_lead": f" {_WRITTEN_TEXTS['contactLead']} ",
        },
    )

    assert saved.status_code == 200
    db.refresh(site)
    assert site.section_overrides == {"about": "Poseur de clôtures à Bavilliers.", **_WRITTEN_TEXTS}

    removed = client.patch(
        f"{demo_sites_router.prefix}/{site.id}",
        json={
            "hero_title": "",
            "cta_quote_label": "",
            "about_heading": " ",
            "cta_lead": " ",
            "contact_heading": "",
            "steps": [],
        },
    )

    assert removed.status_code == 200
    db.refresh(site)
    assert site.section_overrides == {
        "about": "Poseur de clôtures à Bavilliers.",
        "subtitle": _WRITTEN_TEXTS["subtitle"],
        "servicesHeading": _WRITTEN_TEXTS["servicesHeading"],
        "servicesLead": _WRITTEN_TEXTS["servicesLead"],
        "ctaTitle": _WRITTEN_TEXTS["ctaTitle"],
        "contactLead": _WRITTEN_TEXTS["contactLead"],
    }


def test_a_text_or_a_list_of_steps_over_its_limit_is_refused(db: Session, site_rebuilt_without_cms: None) -> None:
    site = _fence_site(db)
    client = _client(db)

    too_long_title = client.patch(f"{demo_sites_router.prefix}/{site.id}", json={"hero_title": "x" * 91})
    too_long_button = client.patch(f"{demo_sites_router.prefix}/{site.id}", json={"cta_quote_label": "x" * 61})
    too_many_steps = client.patch(
        f"{demo_sites_router.prefix}/{site.id}", json={"steps": [{"title": f"Étape {index}"} for index in range(7)]}
    )

    assert too_long_title.status_code == 422
    assert too_long_button.status_code == 422
    assert too_many_steps.status_code == 422
    db.refresh(site)
    assert site.section_overrides == {"about": "Poseur de clôtures à Bavilliers."}


def test_a_written_title_reaches_the_public_content_and_survives_a_regeneration(
    db: Session, site_verified_offline: None
) -> None:
    site = _fence_site(db)
    client = _client(db)

    saved = client.patch(f"{demo_sites_router.prefix}/{site.id}", json={"hero_title": _FENCE_TITLE})
    regenerated = client.post(f"{demo_sites_router.prefix}/{site.id}/regenerate")

    assert saved.status_code == 200
    assert regenerated.status_code == 200
    db.refresh(site)
    assert site.content_json["heroTitle"] == _FENCE_TITLE
    assert site.content_json["ctaTitle"] == "Parlons de votre jardin"
    assert demo_site_service.content_json_for_public(db, site)["heroTitle"] == _FENCE_TITLE


def test_a_client_publish_keeps_the_written_texts_and_takes_the_client_edits() -> None:
    def fence_story(**client_edits: Any) -> dict[str, Any]:
        site = {"businessName": "BS Grillages", **_WRITTEN_TEXTS, **client_edits}
        return {"component": "page", "body": registry.to_storyblok_site_content("landscaper-verdure", site)}

    untouched_story = fence_story()
    edited_story = fence_story(heroTitle="Clôtures et portails à Bavilliers", steps=[])

    untouched = overrides_from_published_story(
        _WRITTEN_TEXTS, untouched_story, from_storyblok_site_content(untouched_story)
    )
    edited = overrides_from_published_story(_WRITTEN_TEXTS, edited_story, from_storyblok_site_content(edited_story))

    assert untouched == _WRITTEN_TEXTS
    assert edited is not None
    assert edited["heroTitle"] == "Clôtures et portails à Bavilliers"
    assert edited["ctaLead"] == _WRITTEN_TEXTS["ctaLead"]
    assert "steps" not in edited


def test_a_publication_of_a_garage_site_keeps_the_texts_written_for_it() -> None:
    garage_texts: dict[str, Any] = {
        "heroTitle": "Votre garage au Locle",
        "subtitle": "Garage au Locle : entretien, réparations et montage de pneus.",
        "servicesLead": "Entretien, réparations et pneus, rue de France.",
        "ctaTitle": "Prendre rendez-vous",
        "ctaLead": "Appelez le 076 290 34 24 ou écrivez avec le formulaire.",
        "steps": _STEPS,
    }
    site = {"businessName": "Garage Roland SNC", "city": "Le Locle", **garage_texts}
    story = {"component": "page", "body": registry.to_storyblok_site_content("mechanic-pitlane", site)}

    refreshed = overrides_from_published_story(garage_texts, story, from_storyblok_site_content(story))

    assert refreshed == garage_texts


def test_the_garage_editor_names_the_appointment_heading_after_the_form() -> None:
    fields_by_section = {
        component["name"]: component["schema"] for component in registry.content_schemas("mechanic-pitlane", "CH")
    }

    assert "heroTitle" in fields_by_section["section_hero"]
    assert "servicesLead" in fields_by_section["section_services"]
    assert fields_by_section["section_contact"]["ctaTitle"]["display_name"] == "Titre du formulaire de rendez-vous"
    assert fields_by_section["section_contact"]["ctaLead"]["display_name"] == "Texte du formulaire de rendez-vous"
