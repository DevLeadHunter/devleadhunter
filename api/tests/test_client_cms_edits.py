"""
A client's edits published from the CMS win over the sections written for the business: they show on the
site and survive the next regeneration.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session

from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from services.demo_site_service import demo_site_service
from services.storyblok_service import storyblok_service
from services.templates import registry
from services.templates import site_content as sc
from services.templates.site_content import overrides_from_published_story, storyblok_asset_key

_SERVICES = [
    {
        "title": "Mécanique générale",
        "description": "Toute la mécanique auto et moto.",
        "image": "https://img.example/meca.jpg",
    }
]
_FAQ = [{"question": "Faites-vous la carrosserie ?", "answer": "Non, nous travaillons avec des partenaires."}]
_STRENGTHS = [{"title": "Expérience et savoir-faire", "description": "Toute la mécanique auto et moto."}]
_IMAGES = {"faqImage": "https://img.example/faq.jpg", "aboutSecondary": "https://img.example/atelier.jpg"}
_OVERRIDES: dict[str, Any] = {
    "services": _SERVICES,
    "services_source": "manual",
    "faq": _FAQ,
    "strengths": _STRENGTHS,
    "images": _IMAGES,
}


def _garage_story(**changes: Any) -> dict[str, Any]:
    """The story a garage site publishes, built from the stored sections with the client's changes."""
    site: dict[str, Any] = {
        "businessName": "TP Motorsport Sàrl",
        "services": _SERVICES,
        "faq": _FAQ,
        "strengths": _STRENGTHS,
        "images": _IMAGES,
    }
    site.update(changes)
    return {"component": "page", "body": registry.to_storyblok_site_content("mechanic-pitlane", site)}


def _cms_copy(url: str) -> str:
    """The address a push gives a photo's copy in the space library."""
    return f"https://a.storyblok.com/f/296169916056514/cdf44b5d09/{storyblok_asset_key(url)}.jpg"


def _refresh(story: dict[str, Any], overrides: Any = None) -> dict[str, Any] | None:
    published = sc.from_storyblok_site_content(story)
    assert published is not None
    return overrides_from_published_story(_OVERRIDES if overrides is None else overrides, story, published)


def test_a_publish_of_the_stored_sections_keeps_them_as_they_are() -> None:
    assert _refresh(_garage_story()) == _OVERRIDES


def test_the_cms_copies_of_the_stored_photos_keep_their_stored_address() -> None:
    story = _garage_story(
        services=[{**_SERVICES[0], "image": _cms_copy(_SERVICES[0]["image"])}],
        images={slot: _cms_copy(url) for slot, url in _IMAGES.items()},
    )

    assert _refresh(story) == _OVERRIDES


def test_the_client_edit_of_a_written_section_replaces_it() -> None:
    edited_faq = [
        {"question": "Faites-vous la carrosserie ?", "answer": "Non, mais nous avons des partenaires à Sion."}
    ]
    edited_services = [{**_SERVICES[0], "title": "Mécanique toutes marques"}]

    refreshed = _refresh(_garage_story(faq=edited_faq, services=edited_services))

    assert refreshed is not None
    assert refreshed["faq"] == edited_faq
    assert refreshed["services"][0]["title"] == "Mécanique toutes marques"
    assert refreshed["services_source"] == "manual"


def test_a_section_the_story_does_not_carry_keeps_its_stored_version() -> None:
    story = {"component": "page", "body": sc.to_storyblok_site_content({"faq": _FAQ}, ["hero", "faq"])}

    refreshed = _refresh(story)

    assert refreshed is not None
    assert refreshed["strengths"] == _STRENGTHS
    assert refreshed["services"] == _SERVICES


def test_a_section_the_client_emptied_goes_back_to_the_generated_one() -> None:
    refreshed = _refresh(_garage_story(faq=[]))

    assert refreshed is not None
    assert "faq" not in refreshed


def test_a_photo_the_client_replaced_is_kept() -> None:
    refreshed = _refresh(_garage_story(images={**_IMAGES, "faqImage": "https://a.storyblok.com/f/1/new-faq.jpg"}))

    assert refreshed is not None
    assert refreshed["images"] == {**_IMAGES, "faqImage": "https://a.storyblok.com/f/1/new-faq.jpg"}


def test_the_tax_credit_section_follows_the_client_and_keeps_its_question() -> None:
    tax_credit = {
        "heading": "Votre jardin à moitié prix",
        "lead": "50 % de la facture remboursés.",
        "points": ["Même sans impôt à payer"],
        "note": "",
        "faqQuestion": "Puis-je bénéficier du crédit d'impôt ?",
        "faqAnswer": "Oui, sur l'entretien courant du jardin.",
    }
    story = {
        "component": "page",
        "body": sc.to_storyblok_site_content(
            {
                "taxCreditHeading": "Votre entretien à moitié prix",
                "taxCreditLead": "50 % de la facture remboursés.",
                "taxCreditPoints": ["Même sans impôt à payer"],
            },
            ["taxCredit"],
        ),
    }

    refreshed = _refresh(story, {"taxCredit": tax_credit})

    assert refreshed is not None
    assert refreshed["taxCredit"]["heading"] == "Votre entretien à moitié prix"
    assert refreshed["taxCredit"]["faqQuestion"] == "Puis-je bénéficier du crédit d'impôt ?"


def test_a_site_without_written_sections_has_none() -> None:
    assert _refresh(_garage_story(), {}) is None


@pytest.mark.asyncio
async def test_a_client_publish_shows_on_the_site_and_becomes_the_stored_section(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = DemoSite(
        user_id=1,
        slug="tp-motorsport",
        business_name="TP Motorsport Sàrl",
        template_id="mechanic-pitlane",
        status=DemoSiteStatus.ACTIVE.value,
        content_json={"businessName": "TP Motorsport Sàrl", "faq": _FAQ},
        section_overrides=dict(_OVERRIDES),
        storyblok_public_token="public-token",
        expires_at=datetime.now(UTC) + timedelta(days=10),
    )
    db.add(site)
    db.commit()
    edited_faq = [{"question": "Où êtes-vous ?", "answer": "Route de Redin 60, à Savièse."}]

    async def published_story(token: str) -> dict[str, Any]:
        return _garage_story(faq=edited_faq)

    monkeypatch.setattr(storyblok_service, "fetch_published_home_content", published_story)

    assert await demo_site_service.sync_content_json_from_storyblok_published(db, site)

    db.refresh(site)
    assert site.content_json["faq"] == edited_faq
    assert site.section_overrides["faq"] == edited_faq
    assert site.section_overrides["strengths"] == _STRENGTHS
