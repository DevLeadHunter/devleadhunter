"""
The garage template's second « à propos » photo and its FAQ photo are photos the site shows: its saved order when there
is one, else the order of the header and the gallery; never a flyer the vision set aside nor a photo taken out.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from services.demo_site_service import DemoSiteService
from services.photo_labels import CRAFT_PHOTO_LABEL_VERSION, PHOTO_FAMILY_CRAFT
from services.templates import registry

_SHOPFRONT = "https://cdn.example/devanture.jpg"
_WORKSHOP = "https://cdn.example/atelier.jpg"
_OIL_CHANGE_FLYER = "https://cdn.example/flyer-vidange-59-euros.jpg"
_TYRES_FLYER = "https://cdn.example/flyer-pneus.jpg"
_CAR_LIFT = "https://cdn.example/pont-elevateur.jpg"
_ENGINE = "https://cdn.example/moteur.jpg"
_LOGO = "https://cdn.example/logo.png"


def _flyer_label() -> dict[str, Any]:
    return {"family": PHOTO_FAMILY_CRAFT, "kind": "flyer", "appeal": 4, "version": CRAFT_PHOTO_LABEL_VERSION}


def _garage_site(enrichment: dict[str, Any]) -> dict[str, Any]:
    return registry.build_site_content(
        template_id="mechanic-pitlane",
        business_name="Leon Motors",
        phone=None,
        email=None,
        city="Thuré",
        area="Thuré",
        subtitle="",
        palette={"primary": "#E11D2E", "secondary": "#0C0C0D", "accent": "#F4F4F5"},
        enrichment=enrichment,
    )


def _displayed_photos(site: dict[str, Any]) -> list[str]:
    return [site["heroImage"], site["aboutImage"], *(photo["url"] for photo in site["gallery"])]


def test_a_flyer_the_vision_set_aside_never_becomes_the_about_or_the_faq_photo() -> None:
    site = _garage_site(
        {
            "photos": [_SHOPFRONT, _WORKSHOP, _OIL_CHANGE_FLYER, _TYRES_FLYER, _CAR_LIFT, _ENGINE],
            "photo_labels": {_OIL_CHANGE_FLYER: _flyer_label(), _TYRES_FLYER: _flyer_label()},
        }
    )

    assert _displayed_photos(site) == [_SHOPFRONT, _WORKSHOP, _CAR_LIFT, _ENGINE]
    assert site["images"] == {"aboutSecondary": _ENGINE, "faqImage": _CAR_LIFT}


def test_the_logo_and_a_repeated_photo_are_left_out_as_on_the_rest_of_the_site() -> None:
    site = _garage_site({"logo_url": _LOGO, "photos": [_SHOPFRONT, _WORKSHOP, _WORKSHOP, _LOGO, _CAR_LIFT]})

    assert site["images"] == {"aboutSecondary": _CAR_LIFT, "faqImage": _CAR_LIFT}


def test_without_a_third_displayed_photo_both_slots_keep_the_template_photos() -> None:
    site = _garage_site(
        {"photos": [_SHOPFRONT, _WORKSHOP, _OIL_CHANGE_FLYER], "photo_labels": {_OIL_CHANGE_FLYER: _flyer_label()}}
    )

    assert _displayed_photos(site) == [_SHOPFRONT, _WORKSHOP]
    assert all(url.startswith("https://images.unsplash.com/") for url in site["images"].values())


def test_with_a_saved_order_both_photos_come_from_it_and_never_from_a_photo_taken_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = [_SHOPFRONT, _WORKSHOP, _OIL_CHANGE_FLYER, _TYRES_FLYER, _CAR_LIFT, _ENGINE]
    site = SimpleNamespace(
        template_id="mechanic-pitlane",
        business_name="Leon Motors",
        phone=None,
        email=None,
        city="Thuré",
        description=None,
        content_json=None,
        use_brand_color=None,
        section_overrides=None,
        image_order=[_CAR_LIFT, _SHOPFRONT, _WORKSHOP, _ENGINE],
        image_pool_snapshot=list(pool),
    )
    monkeypatch.setattr(DemoSiteService, "_enrichment_dict_for_site", lambda _self, _db, _site: {"photos": pool})
    monkeypatch.setattr(DemoSiteService, "_prospect_country_for_site", lambda _self, _db, _site: "FR")

    content = DemoSiteService()._build_content_for_site_with_theme(None, site)

    assert _displayed_photos(content) == [_CAR_LIFT, _SHOPFRONT, _WORKSHOP, _ENGINE]
    assert content["images"] == {"aboutSecondary": _ENGINE, "faqImage": _WORKSHOP}
