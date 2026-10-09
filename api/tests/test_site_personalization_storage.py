"""
A personalisation is stored as the site's overrides and reaches the published content: any photo slot of the
template, the facts under the title, and never a photo the vision read as a flyer.
"""

from __future__ import annotations

from types import SimpleNamespace

from services.demo_site_service import DemoSiteService
from services.photo_labels import CRAFT_PHOTO_LABEL_VERSION, PHOTO_FAMILY_CRAFT
from services.site_personalization_service import SitePersonalization
from services.templates.site_content import apply_section_overrides, usable_site_photos


def _craft(kind: str) -> dict:
    return {"family": PHOTO_FAMILY_CRAFT, "kind": kind, "appeal": 4, "version": CRAFT_PHOTO_LABEL_VERSION}


def _personalization(**overrides: object) -> SitePersonalization:
    values: dict[str, object] = {
        "hero_sentence": "Paysagiste à Gland : taille de haies, pose de clôtures.",
        "about": "Nous entretenons les jardins de Gland.",
        "hero_badge": "Paysagiste à Gland",
        "hero_points": ["Gland et alentours"],
        "photo_order": ["b", "a"],
        "service_cards": [{"title": "Taille de haies", "description": "Des haies nettes.", "image": "a"}],
        "portfolio": [{"image": "b", "title": "Jardin", "category": "Création"}],
        "section_images": {"ctaBackground": "a"},
    }
    values.update(overrides)
    return SitePersonalization(**values)


def test_a_photo_the_vision_read_as_a_flyer_never_reaches_the_site() -> None:
    enrichment = {
        "photos": ["flyer", "garden", "unread", "dish"],
        "photo_labels": {
            "flyer": _craft("logo_or_flyer"),
            "garden": _craft("work"),
            "dish": {"kind": "dish", "appeal": 4, "version": 2},
        },
    }

    assert usable_site_photos(enrichment) == ["garden", "unread", "dish"]


def test_the_overrides_set_any_photo_slot_and_the_facts_under_the_title() -> None:
    content = {"images": {"ctaBackground": "stock.jpg"}, "heroPoints": ["Devis gratuit"]}

    result = apply_section_overrides(
        content, {"images": {"ctaBackground": "own.jpg", "heroSecondary": "own2.jpg"}, "heroPoints": [" Gland ", ""]}
    )

    assert result["images"] == {"ctaBackground": "own.jpg", "heroSecondary": "own2.jpg"}
    assert result["heroPoints"] == ["Gland"]


def test_a_personalisation_is_stored_as_the_site_overrides_and_photo_order() -> None:
    site = SimpleNamespace(section_overrides={"images": {"faq": "kept"}}, description=None, image_order=None)

    DemoSiteService._apply_personalization(site, _personalization(), ["a", "b"], replace_description=False)

    assert site.section_overrides["about"] == "Nous entretenons les jardins de Gland."
    assert site.section_overrides["services_source"] == "ai_auto"
    assert site.section_overrides["heroPoints"] == ["Gland et alentours"]
    assert site.section_overrides["images"] == {"faq": "kept", "ctaBackground": "a"}
    assert site.section_overrides["personalization"]["source"] == "auto"
    assert site.image_order == ["b", "a"]
    assert site.image_pool_snapshot == ["a", "b"]
    assert site.description == "Paysagiste à Gland : taille de haies, pose de clôtures."


def test_a_hero_sentence_typed_at_creation_is_kept_unless_the_personalisation_is_redone() -> None:
    site = SimpleNamespace(section_overrides=None, description="Ma phrase", image_order=None)

    DemoSiteService._apply_personalization(
        site, _personalization(photo_order=["a", "b"]), ["a", "b"], replace_description=False
    )
    assert site.description == "Ma phrase"
    assert site.image_order is None

    DemoSiteService._apply_personalization(site, _personalization(), ["a", "b"], replace_description=True)
    assert site.description == "Paysagiste à Gland : taille de haies, pose de clôtures."
