"""A demo gives up its Storyblok space for room and takes it back later, the site never moving (31 Oct 2026).

The photos of a demo live in its space's asset library: deleting the space by hand left a demo online with broken
pictures. The release copies them onto R2 first, deletes the space only when no Storyblok URL is left, and the
content stays in the database so a new space can be seeded from it.
"""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Iterator
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import api.v1.routes.demo_sites as demo_routes
import services.demo_site_service as demo_module
from api.v1.routes.demo_sites import router as demo_sites_router
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from services.auth_service import get_current_active_user
from services.demo_site_service import DemoSiteService, demo_site_service
from services.storyblok_service import StoryblokProvisionError, StoryblokProvisionResult, StoryblokService

_USER_ID = 1
_NOW = datetime.now(UTC)
_SPACE_ID = 4242
_STORYBLOK_HERO = f"https://a.storyblok.com/f/{_SPACE_ID}/hero.jpg"
_STORYBLOK_GALLERY = f"https://a.storyblok.com/f/{_SPACE_ID}/gallery-1.jpg"
_STORYBLOK_ABOUT = f"https://a.storyblok.com/f/{_SPACE_ID}/about.jpg"
_R2_PREFIX = "https://pub-test.r2.dev/images/prospects/7/"


def _content() -> dict[str, Any]:
    return {
        "businessName": "TP Motorsport",
        "heroImage": _STORYBLOK_HERO,
        "gallery": [{"url": _STORYBLOK_GALLERY, "alt": ""}],
        "logo": f"{_R2_PREFIX}logo.png",
    }


def _overrides() -> dict[str, Any]:
    return {"images": {"about": _STORYBLOK_ABOUT}}


def _row(db: Session, slug: str = "tp-motorsport", **overrides: object) -> DemoSite:
    """A demo that went out two days ago, whose video is made and whose space is still there."""
    fields: dict[str, Any] = {
        "user_id": _USER_ID,
        "prospect_id": 7,
        "slug": slug,
        "business_name": "TP Motorsport",
        "template_id": "mechanic-pitlane",
        "status": DemoSiteStatus.ACTIVE.value,
        "demo_url": f"https://demo.example.com/{slug}",
        "storyblok_space_id": _SPACE_ID,
        "storyblok_public_token": "public",
        "storyblok_preview_token": "preview",
        "storyblok_editor_url": f"https://app.storyblok.com/#/me/spaces/{_SPACE_ID}/dashboard",
        "storyblok_invite_sent": False,
        "storyblok_collaborator_status": None,
        "content_json": _content(),
        "section_overrides": _overrides(),
        "video_status": "ready",
        "video_generated_at": _NOW - timedelta(days=3),
        "demo_link_sent_at": _NOW - timedelta(days=2),
        "expires_at": _NOW + timedelta(days=19),
    }
    fields.update(overrides)
    site = DemoSite(**fields)
    db.add(site)
    db.commit()
    return site


class _Recorder:
    """What the release asked of Storyblok and of the photo copy."""

    def __init__(self) -> None:
        self.deleted_spaces: list[int] = []
        self.copies: int = 0
        self.fail_to_copy: set[str] = set()
        self.refuse_deletion: bool = False


@pytest.fixture
def recorder() -> Iterator[_Recorder]:
    """A photo copy that moves each Storyblok URL onto R2 (but the ones told to fail) and a Storyblok to ask.

    Patched with ``patch.object``, which leaves no attribute behind on the shared services: other tests patch
    them on the class, and a leftover on the instance would hide theirs.
    """
    seen = _Recorder()

    def to_r2(url: str) -> str:
        if url in seen.fail_to_copy or "storyblok.com" not in url:
            return url
        return f"{_R2_PREFIX}{url.rsplit('/', 1)[-1]}"

    def rewrite(node: Any) -> Any:
        if isinstance(node, str):
            return to_r2(node)
        if isinstance(node, dict):
            return {key: rewrite(value) for key, value in node.items()}
        if isinstance(node, list):
            return [rewrite(value) for value in node]
        return node

    async def copy_photos(demo_site: DemoSite) -> int:
        seen.copies += 1
        demo_site.content_json = rewrite(demo_site.content_json)
        demo_site.section_overrides = rewrite(demo_site.section_overrides)
        return 1

    async def delete_space(space_id: int) -> None:
        if seen.refuse_deletion:
            raise RuntimeError("Storyblok is down")
        seen.deleted_spaces.append(space_id)

    with ExitStack() as patches:
        patches.enter_context(patch.object(demo_site_service, "persist_content_images_to_r2", copy_photos))
        patches.enter_context(patch.object(demo_module.storyblok_service, "delete_space", delete_space))
        patches.enter_context(patch.object(demo_module.activity_log_service, "record", lambda **_kwargs: None))
        yield seen


@pytest.fixture(autouse=True)
def no_logo_download() -> Iterator[None]:
    """The site's own route reads the logo colour, a download this test does not make."""
    with patch.object(demo_routes.brand_color_service, "extract_brand_color", lambda _logo: None):
        yield


def _client(db: Session) -> TestClient:
    application = FastAPI()
    application.include_router(demo_sites_router)
    application.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=_USER_ID, email="o@x.com")
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"storyblok_space_id": None}, "Ce site n'a pas d'espace Storyblok."),
        ({"status": DemoSiteStatus.EXPIRED.value}, "Seule une démo en ligne peut libérer son espace."),
        ({"storyblok_collaborator_status": "joined"}, "Le client a rejoint l'espace : on le garde."),
        ({"storyblok_collaborator_status": "pending"}, "Le client a été invité dans l'espace : on le garde."),
        ({"storyblok_invite_sent": True}, "Le client a été invité dans l'espace : on le garde."),
        ({"demo_link_sent_at": None}, "Le lien de la démo n'a pas encore été envoyé : on garde l'espace."),
        ({"video_status": None}, "La vidéo n'est pas encore générée : l'espace sert à la filmer."),
        ({"video_status": "failed"}, "La vidéo n'est pas encore générée : l'espace sert à la filmer."),
        (
            {"video_desktop_requested_at": _NOW},
            "Une vidéo est en cours de demande ou de montage : l'espace sert à la filmer.",
        ),
        ({"content_json": None}, "Ce site n'a pas de contenu enregistré : on ne pourrait pas lui recréer son espace."),
    ],
)
def test_a_space_that_is_still_needed_is_not_released(
    db: Session, recorder: _Recorder, overrides: dict[str, Any], reason: str
) -> None:
    site = _row(db, **overrides)
    kept = copy.deepcopy((site.storyblok_space_id, site.content_json))

    assert DemoSiteService.storyblok_release_blocker(site) == reason
    with pytest.raises(ValueError, match=reason):
        asyncio.run(demo_site_service.release_storyblok_space(db, site))

    assert recorder.deleted_spaces == []
    assert recorder.copies == 0
    assert (site.storyblok_space_id, site.content_json) == kept


def test_a_demo_that_went_out_with_its_video_made_can_release_its_space(db: Session) -> None:
    assert DemoSiteService.storyblok_release_blocker(_row(db)) is None


def test_the_release_copies_the_photos_then_deletes_the_space_and_the_demo_stays_as_it_was(
    db: Session, recorder: _Recorder
) -> None:
    site = _row(db)
    before = copy.deepcopy(site.content_json)

    released = asyncio.run(demo_site_service.release_storyblok_space(db, site))

    assert recorder.copies == 1
    assert recorder.deleted_spaces == [_SPACE_ID]
    assert released.storyblok_space_id is None
    assert released.storyblok_public_token is None
    assert released.storyblok_preview_token is None
    assert released.storyblok_editor_url is None
    assert demo_site_service.storyblok_asset_urls(released) == []
    assert released.content_json == {
        "businessName": before["businessName"],
        "heroImage": f"{_R2_PREFIX}hero.jpg",
        "gallery": [{"url": f"{_R2_PREFIX}gallery-1.jpg", "alt": ""}],
        "logo": before["logo"],
    }
    assert released.section_overrides == {"images": {"about": f"{_R2_PREFIX}about.jpg"}}
    assert released.status == DemoSiteStatus.ACTIVE.value
    assert released.demo_link_sent_at is not None
    assert released.video_status == "ready"
    assert released.expires_at == site.expires_at


def test_a_photo_that_cannot_be_copied_keeps_the_space(db: Session, recorder: _Recorder) -> None:
    recorder.fail_to_copy = {_STORYBLOK_GALLERY}
    site = _row(db)

    with pytest.raises(ValueError, match=r"1 photo\(s\) n'ont pas pu être copiées"):
        asyncio.run(demo_site_service.release_storyblok_space(db, site))

    assert recorder.deleted_spaces == []
    assert site.storyblok_space_id == _SPACE_ID
    assert site.storyblok_editor_url is not None
    assert demo_site_service.storyblok_asset_urls(site) == [_STORYBLOK_GALLERY]


def test_a_failed_photo_copy_keeps_the_space(db: Session, recorder: _Recorder) -> None:
    async def fail(demo_site: DemoSite) -> int:
        raise RuntimeError("R2 is down")

    site = _row(db)

    with patch.object(demo_site_service, "persist_content_images_to_r2", fail):
        with pytest.raises(ValueError, match="Les photos n'ont pas pu être copiées chez nous"):
            asyncio.run(demo_site_service.release_storyblok_space(db, site))

    assert recorder.deleted_spaces == []
    assert site.storyblok_space_id == _SPACE_ID


def test_a_space_storyblok_refuses_to_delete_stays_on_the_site(db: Session, recorder: _Recorder) -> None:
    recorder.refuse_deletion = True
    site = _row(db)

    with pytest.raises(ValueError, match="Storyblok n'a pas supprimé l'espace"):
        asyncio.run(demo_site_service.release_storyblok_space(db, site))

    assert site.storyblok_space_id == _SPACE_ID
    assert site.storyblok_public_token == "public"


@pytest.fixture
def provisions() -> Iterator[list[dict[str, Any]]]:
    """The spaces asked of a configured Storyblok, answered with space 99 and the content as it was given."""
    calls: list[dict[str, Any]] = []

    async def fake_provision(**kwargs: Any) -> StoryblokProvisionResult:
        calls.append(kwargs)
        return StoryblokProvisionResult(
            space_id=99,
            public_token="new-public",
            preview_token="new-preview",
            editor_url="https://app.storyblok.com/#/me/spaces/99/dashboard",
            login_email="contact@exemple.ch",
            login_password=None,
            invite_sent=False,
            content_json=kwargs["content_json"],
            mock_mode=False,
        )

    with ExitStack() as patches:
        patches.enter_context(
            patch.object(demo_module.storyblok_service, "provision_space_with_content", fake_provision)
        )
        patches.enter_context(patch.object(StoryblokService, "is_configured", property(lambda self: True)))
        patches.enter_context(patch.object(demo_site_service, "_prospect_country_for_site", lambda _db, _site: "FR"))
        yield calls


def test_a_released_site_gets_a_new_space_seeded_from_the_content_it_kept(
    db: Session, recorder: _Recorder, provisions: list[dict[str, Any]]
) -> None:
    site = _row(db)
    asyncio.run(demo_site_service.release_storyblok_space(db, site))
    content_after_release = copy.deepcopy(site.content_json)
    overrides_after_release = copy.deepcopy(site.section_overrides)

    back = asyncio.run(demo_site_service.provision_missing_storyblok_space(db, site))

    assert back.storyblok_space_id == 99
    assert back.storyblok_public_token == "new-public"
    assert back.storyblok_editor_url == "https://app.storyblok.com/#/me/spaces/99/dashboard"
    assert provisions[0]["content_json"] == content_after_release
    assert provisions[0]["rehost_all_assets"] is True
    assert provisions[0]["invite_client"] is False
    assert provisions[0]["sync_seed_publication"] is False
    assert back.content_json == content_after_release
    assert back.section_overrides == overrides_after_release
    assert back.status == DemoSiteStatus.ACTIVE.value
    assert back.video_status == "ready"
    assert back.expires_at == site.expires_at


def test_a_space_left_half_built_by_a_failed_seeding_is_deleted(db: Session, recorder: _Recorder) -> None:
    async def fail_after_creating_the_space(**kwargs: Any) -> StoryblokProvisionResult:
        raise StoryblokProvisionError("publish refused", space_id=77, editor_url=None, content_json=None)

    site = _row(db, storyblok_space_id=None, storyblok_public_token=None, storyblok_editor_url=None)

    with ExitStack() as patches:
        patches.enter_context(
            patch.object(demo_module.storyblok_service, "provision_space_with_content", fail_after_creating_the_space)
        )
        patches.enter_context(patch.object(StoryblokService, "is_configured", property(lambda self: True)))
        patches.enter_context(patch.object(demo_site_service, "_prospect_country_for_site", lambda _db, _site: "FR"))
        with pytest.raises(StoryblokProvisionError):
            asyncio.run(demo_site_service.provision_missing_storyblok_space(db, site))

    assert recorder.deleted_spaces == [77]
    assert site.storyblok_space_id is None


def test_the_dashboard_is_told_when_a_space_can_go_and_why_not(db: Session) -> None:
    ready = _row(db, slug="pret")
    waiting = _row(db, slug="en-attente", video_status=None)
    bare = _row(db, slug="sans-espace", storyblok_space_id=None, storyblok_editor_url=None)

    answers = {
        slug: _client(db).get(f"{demo_sites_router.prefix}/{site.id}").json()
        for slug, site in (("ready", ready), ("waiting", waiting), ("bare", bare))
    }

    assert answers["ready"]["can_release_storyblok_space"] is True
    assert answers["ready"]["storyblok_release_blocker"] is None
    assert answers["waiting"]["can_release_storyblok_space"] is False
    assert answers["waiting"]["storyblok_release_blocker"].startswith("La vidéo n'est pas encore générée")
    assert answers["bare"]["can_release_storyblok_space"] is False
    assert answers["bare"]["storyblok_release_blocker"] is None


def test_the_route_releases_the_space_and_answers_with_the_site_without_it(db: Session, recorder: _Recorder) -> None:
    site = _row(db)

    response = _client(db).delete(f"{demo_sites_router.prefix}/{site.id}/storyblok-space")

    assert response.status_code == 200
    body = response.json()
    assert body["storyblok_space_id"] is None
    assert body["storyblok_editor_url"] is None
    assert body["can_release_storyblok_space"] is False
    assert body["status"] == DemoSiteStatus.ACTIVE.value
    assert recorder.deleted_spaces == [_SPACE_ID]


def test_the_route_refuses_with_the_reason_when_the_video_is_not_made(db: Session, recorder: _Recorder) -> None:
    site = _row(db, video_status=None)

    response = _client(db).delete(f"{demo_sites_router.prefix}/{site.id}/storyblok-space")

    assert response.status_code == 409
    assert response.json()["detail"] == "La vidéo n'est pas encore générée : l'espace sert à la filmer."
    assert recorder.deleted_spaces == []
