"""
A template's one-off photos are their own Storyblok fields: one never takes the name of a content field,
or every push writes the photo over that field (the garage FAQ lost its questions this way).
"""

import pytest

from services.templates import registry
from services.templates import site_content as sc


@pytest.mark.parametrize("module", registry.TEMPLATE_MODULES, ids=lambda module: module.TEMPLATE_ID)
def test_no_photo_slot_takes_the_name_of_a_content_field(module: object) -> None:
    declared: dict[str, list[dict[str, str]]] = getattr(module, "EXTRA_SECTION_IMAGES", None) or {}
    slot_fields = [slot["field"] for slots in declared.values() for slot in slots]

    assert not set(slot_fields) & set(sc.FIELD_SCHEMAS)


def _garage_site() -> dict:
    return {
        "businessName": "TP Motorsport Sàrl",
        "faq": [{"question": "Faites-vous la carrosserie ?", "answer": "Non, nous travaillons avec des partenaires."}],
        "images": {"aboutSecondary": "https://img.example/atelier.jpg", "faqImage": "https://img.example/faq.jpg"},
    }


def test_the_garage_faq_keeps_its_questions_and_its_photo_through_the_editor() -> None:
    body = registry.to_storyblok_site_content("mechanic-pitlane", _garage_site())

    flat = sc.from_storyblok_site_content({"component": "page", "body": body})

    assert flat["faq"] == _garage_site()["faq"]
    assert flat["images"]["faqImage"] == "https://img.example/faq.jpg"
    assert flat["images"]["aboutSecondary"] == "https://img.example/atelier.jpg"


def test_the_garage_faq_section_offers_the_questions_and_the_photo_separately() -> None:
    by_name = {component["name"]: component for component in registry.content_schemas("mechanic-pitlane", "CH")}
    faq_fields = by_name["section_faq"]["schema"]

    assert faq_fields["faq"]["type"] == "bloks"
    assert faq_fields["faqImage"]["type"] == "asset"


def test_the_garage_image_slots_name_the_faq_photo() -> None:
    assert set(registry.section_image_slots("mechanic-pitlane")) == {"aboutSecondary", "faqImage"}
