"""
An operator can take off a site the « reviews » that are none and every photo of the prospect, for good: both survive
regenerations and the client's publications. A service card never gets a template's picture in gallery order: one
left without a photo of the business keeps its photo empty, for its template to choose one that fits its title.
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
from services.demo_site_service import DemoSiteService, demo_site_service
from services.storyblok_service import storyblok_service
from services.templates import registry
from services.templates.default_images import DEFAULT_IMAGES
from services.templates.site_content import (
    MAX_HIDDEN_REVIEWS,
    apply_section_overrides,
    clean_hidden_reviews,
    fill_missing_card_images,
    from_storyblok_site_content,
    is_stock_photo,
    overrides_from_published_story,
    storyblok_asset_key,
)

_USER_ID = 1
_OWNER_REPLY = "Je vous remercie Mme clercent"
_PAGE_NOTICE = "Alexandre Nouhaud a limité qui peut commenter cette publication."
_REAL_REVIEW = "Très bon professionnel, à l'écoute et rigoureux. Il a su respecter les délais."
_PROSPECT_PHOTOS = [f"https://cdn.example.fr/chantier-{index}.jpg" for index in range(4)]
_ENRICHMENT: dict[str, Any] = {
    "photos": _PROSPECT_PHOTOS,
    "reviews": [
        {"author": "Annie-Claude", "text": _REAL_REVIEW, "rating": 5},
        {"author": "Carole Clercent", "text": _OWNER_REPLY, "rating": 5},
        {"author": "Alexandre Nouhaud", "text": _PAGE_NOTICE, "rating": 5},
    ],
}
_UNSPLASH_PHOTO = "https://images.unsplash.com/photo-1732194044246-9c5f6bc6582c?auto=format&fit=crop&w=900&q=80"


def _client(db: Session) -> TestClient:
    application = FastAPI()
    application.include_router(demo_sites_router)
    signed_in_user = SimpleNamespace(id=_USER_ID, email="owner@example.com")
    application.dependency_overrides[get_current_active_user] = lambda: signed_in_user
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def _electrician_site(db: Session, section_overrides: dict[str, Any] | None = None) -> DemoSite:
    site = DemoSite(
        user_id=_USER_ID,
        slug="j-b-elec",
        business_name="J.B Elec",
        template_id="electrician-eclat",
        city="Le Robert",
        email="contact@jb-elec.example",
        status=DemoSiteStatus.ACTIVE.value,
        content_json={"businessName": "J.B Elec"},
        section_overrides=section_overrides,
        expires_at=datetime.now(UTC) + timedelta(days=10),
    )
    db.add(site)
    db.commit()
    return site


@pytest.fixture
def site_built_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """A regeneration builds the real content from a fixed enrichment, checks no address and writes no activity."""

    async def live(database: Session, demo_site: DemoSite) -> SimpleNamespace:
        return SimpleNamespace(
            public_api_ok=True, demo_url_live=True, local_demo_url=None, local_demo_url_live=False, message="OK"
        )

    monkeypatch.setattr(DemoSiteService, "_enrichment_dict_for_site", lambda _self, _db, _site: dict(_ENRICHMENT))
    monkeypatch.setattr(demo_site_module.demo_site_verification_service, "verify", live)
    monkeypatch.setattr(demo_site_module.activity_log_service, "record", lambda **entry: None)


def _review_texts(content: dict[str, Any]) -> list[str]:
    return [review["text"] for review in content.get("reviews") or []]


def _every_image(content: dict[str, Any]) -> set[str]:
    images: set[str] = {content.get("heroImage") or "", content.get("aboutImage") or ""}
    images |= {photo["url"] for photo in content.get("gallery") or []}
    images |= {card.get("image") or "" for card in content.get("services") or []}
    images |= {item.get("image") or "" for item in content.get("portfolio") or []}
    images |= set((content.get("images") or {}).values())
    return images - {""}


def test_hidden_reviews_are_tidied_like_a_displayed_review() -> None:
    texts: list[Any] = [f"  {_OWNER_REPLY}\n", _OWNER_REPLY.upper(), "Avis tronqué … Plus", " ", 12, "x" * 2001]
    texts += [f"Avis {index}" for index in range(MAX_HIDDEN_REVIEWS + 3)]

    cleaned = clean_hidden_reviews(texts)

    assert cleaned[:2] == [_OWNER_REPLY, "Avis tronqué"]
    assert len(cleaned) == MAX_HIDDEN_REVIEWS
    assert clean_hidden_reviews("not a list") == []


def test_a_hidden_review_leaves_the_site_whatever_its_case_and_spacing() -> None:
    content = {"reviews": [dict(review) for review in _ENRICHMENT["reviews"]]}

    result = apply_section_overrides(content, {"hiddenReviews": [_OWNER_REPLY.lower(), f" {_PAGE_NOTICE}  "]})

    assert _review_texts(result) == [_REAL_REVIEW]


def test_the_patch_hides_reviews_and_photos_and_an_empty_value_shows_them_again(
    db: Session, site_built_offline: None
) -> None:
    site = _electrician_site(db, section_overrides={"heroTitle": "Raccordements électriques au Robert"})
    client = _client(db)

    saved = client.patch(
        f"{demo_sites_router.prefix}/{site.id}",
        json={"hidden_reviews": [_OWNER_REPLY, _PAGE_NOTICE], "hide_prospect_photos": True},
    )

    assert saved.status_code == 200
    assert saved.json()["hidden_reviews"] == [_OWNER_REPLY, _PAGE_NOTICE]
    assert saved.json()["hide_prospect_photos"] is True
    db.refresh(site)
    assert site.section_overrides == {
        "heroTitle": "Raccordements électriques au Robert",
        "hiddenReviews": [_OWNER_REPLY, _PAGE_NOTICE],
        "hideProspectPhotos": True,
    }

    shown = client.patch(
        f"{demo_sites_router.prefix}/{site.id}", json={"hidden_reviews": [], "hide_prospect_photos": False}
    )

    assert shown.status_code == 200
    assert shown.json()["hidden_reviews"] == []
    assert shown.json()["hide_prospect_photos"] is False
    db.refresh(site)
    assert site.section_overrides == {"heroTitle": "Raccordements électriques au Robert"}


def test_hidden_reviews_and_photos_stay_off_the_site_after_a_regeneration(
    db: Session, site_built_offline: None
) -> None:
    site = _electrician_site(
        db,
        section_overrides={
            "services": [
                {"title": "Raccordements électriques", "description": "", "image": _PROSPECT_PHOTOS[3]},
                {"title": "Bandeaux LED", "description": "", "image": ""},
            ],
            "images": {"heroSecondary": _PROSPECT_PHOTOS[2], "ctaBackground": _PROSPECT_PHOTOS[3]},
        },
    )
    client = _client(db)

    saved = client.patch(
        f"{demo_sites_router.prefix}/{site.id}", json={"hidden_reviews": [_OWNER_REPLY], "hide_prospect_photos": True}
    )
    regenerated = client.post(f"{demo_sites_router.prefix}/{site.id}/regenerate")

    assert saved.status_code == 200
    assert regenerated.status_code == 200
    db.refresh(site)
    public = demo_site_service.content_json_for_public(db, site)
    for content in (site.content_json, public):
        assert _review_texts(content) == [_REAL_REVIEW, _PAGE_NOTICE]
        assert _every_image(content).isdisjoint(_PROSPECT_PHOTOS)
        assert content["heroImage"] == DEFAULT_IMAGES["electrician-eclat"]["heroImage"]
        assert [card["image"] for card in content["services"]] == ["", ""]


def test_the_prospect_photos_come_back_when_the_operator_shows_them_again(
    db: Session, site_built_offline: None
) -> None:
    site = _electrician_site(db, section_overrides={"hideProspectPhotos": True})
    client = _client(db)

    shown = client.patch(f"{demo_sites_router.prefix}/{site.id}", json={"hide_prospect_photos": False})

    assert shown.status_code == 200
    db.refresh(site)
    assert site.content_json["heroImage"] == _PROSPECT_PHOTOS[0]
    assert site.content_json["aboutImage"] == _PROSPECT_PHOTOS[1]


def test_a_client_publish_keeps_the_hidden_reviews_and_photos() -> None:
    overrides: dict[str, Any] = {
        "hiddenReviews": [_OWNER_REPLY],
        "hideProspectPhotos": True,
        "heroTitle": "Raccordements électriques au Robert",
        "ctaLead": "Appelez-moi ou décrivez votre projet avec le formulaire.",
    }
    site = {"businessName": "J.B Elec", "heroTitle": overrides["heroTitle"], "ctaLead": overrides["ctaLead"]}
    story = {"component": "page", "body": registry.to_storyblok_site_content("electrician-eclat", site)}

    refreshed = overrides_from_published_story(overrides, story, from_storyblok_site_content(story))

    assert refreshed == overrides


def test_a_card_never_gets_a_template_picture_in_gallery_order() -> None:
    site = storyblok_service.build_content_json(
        business_name="Electro-Contrôle",
        phone="022 785 20 54",
        email=None,
        city="Meyrin",
        description=None,
        template_id="electrician-eclat",
    )
    assert site["gallery"]

    result = apply_section_overrides(
        site, {"services": [{"title": "Contrôle final"}, {"title": "Contrôle périodique"}]}
    )

    assert [card["image"] for card in result["services"]] == ["", ""]


def test_a_card_still_gets_the_best_unused_photo_of_the_business() -> None:
    site = {
        "heroImage": _PROSPECT_PHOTOS[0],
        "aboutImage": _UNSPLASH_PHOTO,
        "gallery": [{"url": _UNSPLASH_PHOTO}, {"url": _PROSPECT_PHOTOS[2]}],
        "services": [{"title": "Dépannage", "image": ""}, {"title": "Tableau", "image": ""}, {"title": "Éclairage"}],
    }

    fill_missing_card_images(site, None)

    assert [card.get("image", "") for card in site["services"]] == [_PROSPECT_PHOTOS[2], "", ""]


def test_a_template_picture_is_recognised_at_its_own_address_and_in_the_cms() -> None:
    verdure_hero = DEFAULT_IMAGES["landscaper-verdure"]["heroImage"]
    cms_copy = f"https://a.storyblok.com/f/123/1400x900/abc/{storyblok_asset_key(verdure_hero)}.jpg"

    assert is_stock_photo(_UNSPLASH_PHOTO)
    assert is_stock_photo(verdure_hero)
    assert is_stock_photo(cms_copy)
    assert not is_stock_photo(_PROSPECT_PHOTOS[0])
    assert not is_stock_photo("https://a.storyblok.com/f/123/800x600/abc/photo-du-client.jpg")
