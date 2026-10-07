"""Dormant-demo lifecycle: keep an SMS-reachable demo dormant, delete the rest, revive on relance.

Covers the risky expiry rewrite (runs hourly in prod): a prospect who can still be SMS-reached
keeps a dormant (EXPIRED) demo with its content, everyone else is hard-deleted, the Storyblok
space is always freed, and a relance revives the demo with a fresh TTL.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

import services.demo_site_service as demo_module
from core.config import settings
from enums.demo_site_status import DemoSiteStatus
from services.demo_site_service import DemoSiteService, demo_site_service


class _CommitDB:
    """Session stand-in that only records commit/refresh."""

    def commit(self) -> None:
        return None

    def refresh(self, _row: object) -> None:
        return None


class _OrderedFirstDB:
    """Session stand-in returning canned ``.first()`` results in call order."""

    def __init__(self, firsts: list[object | None]) -> None:
        self._firsts = list(firsts)

    def query(self, *_entities: object) -> "_OrderedFirstDB":
        return self

    def filter(self, *_conditions: object) -> "_OrderedFirstDB":
        return self

    def first(self) -> object | None:
        return self._firsts.pop(0) if self._firsts else None


class _BatchAllDB:
    """Session stand-in serving successive ``.all()`` batches (due sites, then stale dormant)."""

    def __init__(self, batches: list[list[object]]) -> None:
        self._batches = list(batches)
        self.committed = False

    def query(self, *_entities: object) -> "_BatchAllDB":
        return self

    def filter(self, *_conditions: object) -> "_BatchAllDB":
        return self

    def all(self) -> list[object]:
        return self._batches.pop(0) if self._batches else []

    def commit(self) -> None:
        self.committed = True


def _due_site(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "status": DemoSiteStatus.ACTIVE.value,
        "slug": "garage-central",
        "business_name": "Garage Central",
        "user_id": 1,
        "prospect_id": 7,
        "content_json": {"business": {"name": "Garage Central"}},
        "storyblok_space_id": 4242,
        "storyblok_public_token": "pub",
        "storyblok_preview_token": "prev",
        "storyblok_editor_url": "https://app.storyblok.com/x",
        "deleted_at": None,
        "expires_at": datetime.now(UTC) - timedelta(days=1),
        "video_status": "ready",
        "video_error": None,
        "video_generated_at": datetime.now(UTC),
        "keep_dormant": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _stub_expiry_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _no_space(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(demo_module.storyblok_service, "delete_demo_space", _no_space)
    monkeypatch.setattr("services.demo_video_service.delete_files_for_slug", lambda _slug: None)


class TestRestartDemoTtl:
    def test_resets_to_a_fresh_window(self) -> None:
        sent_at = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
        site = SimpleNamespace(status=DemoSiteStatus.ACTIVE.value, slug="x", demo_link_sent_at=None, expires_at=None)
        demo_site_service.restart_demo_ttl(_CommitDB(), site, sent_at)
        assert site.demo_link_sent_at is not None
        assert (site.expires_at - site.demo_link_sent_at) == timedelta(days=settings.demo_site_ttl_days)

    def test_never_touches_a_delivered_site(self) -> None:
        site = SimpleNamespace(status=DemoSiteStatus.DELIVERED.value, slug="x", demo_link_sent_at=None, expires_at=None)
        demo_site_service.restart_demo_ttl(_CommitDB(), site, datetime(2026, 9, 3, 12, 0, tzinfo=UTC))
        assert site.demo_link_sent_at is None


class TestReviveDemoSite:
    def test_wakes_an_expired_site_and_rebuilds_missing_content(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            DemoSiteService, "_build_content_for_site", lambda self, db, site: {"business": {"name": "Garage"}}
        )
        site = _due_site(
            status=DemoSiteStatus.EXPIRED.value,
            content_json=None,
            demo_url=None,
            vercel_deployment_url=None,
            error_message="old error",
            demo_url_live=False,
        )
        result = asyncio.run(demo_site_service.revive_demo_site(_CommitDB(), site))
        assert result.status == DemoSiteStatus.ACTIVE.value
        assert result.content_json == {"business": {"name": "Garage"}}
        assert result.demo_url_live is True
        assert result.error_message is None

    def test_leaves_a_non_dormant_site_untouched(self) -> None:
        site = _due_site(status=DemoSiteStatus.ACTIVE.value)
        result = asyncio.run(demo_site_service.revive_demo_site(_CommitDB(), site))
        assert result.status == DemoSiteStatus.ACTIVE.value


def _reachable_prospect(**overrides: object) -> SimpleNamespace:
    """An SMS-reachable prospect (French mobile, not marked « ne plus contacter »)."""
    base: dict[str, object] = {"phone": "06 12 34 56 78", "do_not_contact": False, "is_dismissed": False}
    base.update(overrides)
    return SimpleNamespace(**base)


class TestShouldKeepDormant:
    def test_kept_for_a_reachable_mobile(self) -> None:
        db = _OrderedFirstDB([_reachable_prospect(), None, None])  # prospect, not suppressed, not texted
        site = SimpleNamespace(prospect_id=7, user_id=1)
        assert demo_site_service._should_keep_dormant(db, site) is True

    def test_deleted_without_a_prospect(self) -> None:
        site = SimpleNamespace(prospect_id=None, user_id=1)
        assert demo_site_service._should_keep_dormant(_OrderedFirstDB([]), site) is False

    def test_deleted_for_a_landline(self) -> None:
        db = _OrderedFirstDB([_reachable_prospect(phone="01 42 68 53 00")])
        site = SimpleNamespace(prospect_id=7, user_id=1)
        assert demo_site_service._should_keep_dormant(db, site) is False

    def test_deleted_when_marked_do_not_contact(self) -> None:
        db = _OrderedFirstDB([_reachable_prospect(do_not_contact=True)])
        site = SimpleNamespace(prospect_id=7, user_id=1)
        assert demo_site_service._should_keep_dormant(db, site) is False

    def test_deleted_when_opted_out(self) -> None:
        db = _OrderedFirstDB([_reachable_prospect(), SimpleNamespace(id=1)])  # suppressed
        site = SimpleNamespace(prospect_id=7, user_id=1)
        assert demo_site_service._should_keep_dormant(db, site) is False

    def test_deleted_when_already_texted(self) -> None:
        db = _OrderedFirstDB([_reachable_prospect(), None, SimpleNamespace(id=99)])  # texted
        site = SimpleNamespace(prospect_id=7, user_id=1)
        assert demo_site_service._should_keep_dormant(db, site) is False


class TestExpireDueSites:
    def test_keeps_reachable_dormant_and_deletes_the_rest(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _stub_expiry_side_effects(monkeypatch)
        monkeypatch.setattr(DemoSiteService, "_should_keep_dormant", lambda self, db, site: site.keep_dormant)

        dormant = _due_site(slug="reachable", keep_dormant=True)
        dead = _due_site(slug="deadend", keep_dormant=False)
        db = _BatchAllDB([[dormant, dead], []])  # due sites, then no stale dormant

        cleaned = asyncio.run(demo_site_service.expire_due_sites(db))

        assert cleaned == 2
        # Reachable prospect → dormant: content kept, Storyblok freed, video purged.
        assert dormant.status == DemoSiteStatus.EXPIRED.value
        assert dormant.content_json is not None
        assert dormant.storyblok_space_id is None
        assert dormant.video_status is None
        # Dead-end → hard-deleted: content wiped.
        assert dead.status == DemoSiteStatus.DELETED.value
        assert dead.content_json is None
        assert dead.deleted_at is not None

    def test_second_stage_purges_stale_dormant(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _stub_expiry_side_effects(monkeypatch)
        monkeypatch.setattr(DemoSiteService, "_should_keep_dormant", lambda self, db, site: False)

        stale = _due_site(status=DemoSiteStatus.EXPIRED.value, slug="stale", content_json={"x": 1})
        db = _BatchAllDB([[], [stale]])  # no fresh due sites, one stale dormant

        cleaned = asyncio.run(demo_site_service.expire_due_sites(db))

        assert cleaned == 1
        assert stale.status == DemoSiteStatus.DELETED.value
        assert stale.content_json is None
        assert stale.deleted_at is not None
