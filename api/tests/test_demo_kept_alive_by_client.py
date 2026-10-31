"""A demo whose client works in the CMS space is never retired by its date (31 Oct 2026).

The client of TP Motorsport joined his space on 28 Oct, his demo's 21 days end on 12 Nov: the expiry job would have
deleted the space he edits in and taken his site down. Like a sold site, a demo whose client joined stays until sold
or deleted by hand.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

import services.demo_site_service as demo_module
from api.v1.routes.admin_storage import _expiry_state
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from services.demo_site_service import DemoSiteService, demo_site_service

_NOW = datetime.now(UTC)


def _past_deadline_site(db: Session, slug: str, collaborator_status: str | None) -> DemoSite:
    site = DemoSite(
        user_id=1,
        slug=slug,
        business_name=slug.title(),
        template_id="mechanic-pitlane",
        status=DemoSiteStatus.ACTIVE.value,
        storyblok_space_id=4242,
        storyblok_public_token="public",
        storyblok_preview_token="preview",
        storyblok_editor_url="https://app.storyblok.com/#/me/spaces/4242/dashboard",
        storyblok_collaborator_status=collaborator_status,
        content_json={"businessName": slug},
        demo_link_sent_at=_NOW - timedelta(days=22),
        expires_at=_NOW - timedelta(days=1),
    )
    db.add(site)
    db.commit()
    return site


@pytest.mark.parametrize(
    ("collaborator_status", "kept_alive"),
    [("joined", True), ("pending", False), ("not_invited", False), ("unknown", False), (None, False)],
)
def test_only_a_client_who_joined_keeps_the_demo_alive(collaborator_status: str | None, kept_alive: bool) -> None:
    site = SimpleNamespace(storyblok_collaborator_status=collaborator_status)

    assert DemoSiteService.is_kept_alive_by_client(site) is kept_alive


def test_a_row_without_the_status_column_does_not_keep_a_demo_alive() -> None:
    assert DemoSiteService.is_kept_alive_by_client(SimpleNamespace()) is False


def test_the_expiry_job_leaves_a_demo_whose_client_joined_and_expires_the_others(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    freed_spaces: list[str] = []

    async def record_space_deleted(**kwargs: object) -> int:
        freed_spaces.append(str(kwargs["slug"]))
        return 1

    monkeypatch.setattr("services.demo_video_service.delete_files_for_slug", lambda _slug: None)
    editing = _past_deadline_site(db, "tp-motorsport", "joined")
    silent = _past_deadline_site(db, "garage-silencieux", None)

    # ``patch.object`` leaves nothing behind on the shared services, whose class-level patches other tests rely on.
    with (
        patch.object(demo_module.storyblok_service, "delete_demo_space", record_space_deleted),
        patch.object(demo_site_service, "_should_keep_dormant", lambda _db, _site: False),
    ):
        cleaned = asyncio.run(demo_site_service.expire_due_sites(db))

    db.refresh(editing)
    db.refresh(silent)
    assert cleaned == 1
    assert freed_spaces == ["garage-silencieux"]
    assert editing.status == DemoSiteStatus.ACTIVE.value
    assert editing.storyblok_space_id == 4242
    assert editing.storyblok_public_token == "public"
    assert editing.content_json == {"businessName": "tp-motorsport"}
    assert silent.status == DemoSiteStatus.DELETED.value
    assert silent.storyblok_space_id is None


def test_a_demo_whose_client_joined_is_still_served_past_its_date(db: Session) -> None:
    editing = _past_deadline_site(db, "tp-motorsport", "joined")
    silent = _past_deadline_site(db, "garage-silencieux", None)

    assert demo_site_service.get_public_by_slug(db, editing.slug) is not None
    assert demo_site_service.get_public_by_slug(db, silent.slug) is None


def test_a_demo_whose_client_joined_shows_no_deadline() -> None:
    editing = SimpleNamespace(
        demo_link_sent_at=_NOW - timedelta(days=22),
        expires_at=_NOW - timedelta(days=1),
        storyblok_collaborator_status="joined",
    )
    waiting = SimpleNamespace(
        demo_link_sent_at=_NOW - timedelta(days=2),
        expires_at=_NOW + timedelta(days=19),
        storyblok_collaborator_status=None,
    )

    assert DemoSiteService.expiry_date_label(editing) is None
    assert DemoSiteService.expiry_date_label(waiting) is not None


def test_the_storage_page_does_not_flag_the_files_of_a_demo_whose_client_joined() -> None:
    kwargs = {
        "status": DemoSiteStatus.ACTIVE.value,
        "demo_link_sent_at": _NOW - timedelta(days=22),
        "expires_at": _NOW - timedelta(days=1),
    }
    editing = SimpleNamespace(**kwargs, storyblok_collaborator_status="joined")
    silent = SimpleNamespace(**kwargs, storyblok_collaborator_status=None)

    assert _expiry_state(editing, _NOW) == (False, None, False)
    assert _expiry_state(silent, _NOW) == (True, None, False)
