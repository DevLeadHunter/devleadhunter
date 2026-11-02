"""
The showroom demos dibodev.fr embeds exist once per template, belong to no prospect, and nothing that
ends a prospect's demo (expiry pass, withdrawn page, TTL start, CMS space swap, home counters) touches them.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import services.demo_site_service as demo_module
import services.showcase_demo_service as showcase_module
from api.v1.routes.dashboard import dashboard_stats
from api.v1.routes.demo_sites import router as demo_sites_router
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from models.user import User
from services.demo_site_service import demo_site_service
from services.showcase_demo_service import (
    SHOWCASE_DEMO_SITES,
    SHOWCASE_EXPIRES_AT,
    ShowcaseSlugTakenError,
    showcase_demo_service,
)
from services.storyblok_preswap_service import StoryblokPreswapService


def _owner(db: Session) -> User:
    owner = User(name="Léo Guillaume", email="leo@example.com", hashed_password="x")
    db.add(owner)
    db.commit()
    return owner


@pytest.fixture(autouse=True)
def activity_feed_silent(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    """The activity feed opens its own session on the real database: it is kept in memory here."""
    logged: list[dict[str, object]] = []
    monkeypatch.setattr(showcase_module.activity_log_service, "record", lambda **kwargs: logged.append(kwargs))
    return logged


@pytest.fixture
def expiry_side_effects_stubbed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_space(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(demo_module.storyblok_service, "delete_demo_space", no_space)
    monkeypatch.setattr("services.demo_video_service.delete_files_for_slug", lambda _slug: None)


def _prospect_demo(db: Session, owner: User, *, slug: str = "garage-central", **fields: object) -> DemoSite:
    prospect = ProspectDB(user_id=owner.id, name="Garage Central", category="garage", source="google_maps")
    db.add(prospect)
    db.flush()
    values: dict[str, object] = {
        "user_id": owner.id,
        "prospect_id": prospect.id,
        "slug": slug,
        "business_name": "Garage Central",
        "template_id": "mechanic-pitlane",
        "status": DemoSiteStatus.ACTIVE.value,
        "content_json": {"businessName": "Garage Central"},
        "demo_link_sent_at": datetime(2026, 10, 1, 9, 0),
        "expires_at": datetime(2026, 10, 22, 9, 0),
    }
    values.update(fields)
    site = DemoSite(**values)
    db.add(site)
    db.commit()
    return site


def _client(db: Session) -> TestClient:
    application = FastAPI()
    application.include_router(demo_sites_router)
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


class TestCatalogue:
    def test_one_showroom_demo_per_template_with_the_slugs_dibodev_fr_frames(self) -> None:
        slugs = [showcase.slug for showcase in SHOWCASE_DEMO_SITES]
        assert slugs == [
            "exemple-plombier-signature",
            "exemple-plombier-atelier",
            "exemple-plombier-cuivre",
            "exemple-electricien-eclat",
            "exemple-electricien-lumen",
            "exemple-garage-pitlane",
            "exemple-paysagiste-verdure",
            "exemple-menuisier-edito",
            "exemple-restaurant",
            "exemple-coiffeur",
            "exemple-dentiste",
        ]
        assert len({showcase.template_id for showcase in SHOWCASE_DEMO_SITES}) == len(SHOWCASE_DEMO_SITES)
        assert all(showcase.phone.startswith("02 99 00 00 ") for showcase in SHOWCASE_DEMO_SITES)


class TestEnsureAll:
    def test_creates_every_demo_online_without_prospect_nor_deadline(self, db: Session) -> None:
        owner = _owner(db)

        results = showcase_demo_service.ensure_all(db, owner)

        assert [created for _site, created in results] == [True] * len(SHOWCASE_DEMO_SITES)
        for (site, _created), showcase in zip(results, SHOWCASE_DEMO_SITES):
            assert site.slug == showcase.slug
            assert site.template_id == showcase.template_id
            assert site.is_showcase is True
            assert site.prospect_id is None
            assert site.status == DemoSiteStatus.ACTIVE.value
            assert site.demo_url_live is True
            assert site.demo_url is not None and site.demo_url.endswith(f"/{showcase.slug}")
            assert site.expires_at == SHOWCASE_EXPIRES_AT
            assert site.demo_link_sent_at is None
            assert site.storyblok_space_id is None
            assert site.content_json["businessName"] == showcase.business_name
            assert site.content_json["phone"] == showcase.phone
            assert site.content_json["city"] == showcase.city
            assert site.content_json["heroImage"]
            assert site.content_json["services"]

    def test_the_carpenter_demo_names_its_trade_on_the_multi_trade_template(self, db: Session) -> None:
        owner = _owner(db)

        showcase_demo_service.ensure_all(db, owner)

        carpenter = db.query(DemoSite).filter(DemoSite.slug == "exemple-menuisier-edito").one()
        assert carpenter.template_id == "artisan-edito"
        assert [card["title"] for card in carpenter.content_json["services"]][:2] == [
            "Agencement sur mesure",
            "Cuisines en bois massif",
        ]

    def test_replaying_keeps_the_existing_demos_and_their_content(self, db: Session) -> None:
        owner = _owner(db)
        first_run = showcase_demo_service.ensure_all(db, owner)
        plumber = first_run[0][0]
        plumber.content_json = {**plumber.content_json, "palette": {"primary": "#123456"}}
        plumber.status = DemoSiteStatus.UNAVAILABLE.value
        plumber.expires_at = datetime(2026, 11, 1)
        db.commit()
        plumber_id = plumber.id

        second_run = showcase_demo_service.ensure_all(db, owner)

        assert [created for _site, created in second_run] == [False] * len(SHOWCASE_DEMO_SITES)
        assert db.query(DemoSite).count() == len(SHOWCASE_DEMO_SITES)
        refreshed = db.query(DemoSite).filter(DemoSite.slug == "exemple-plombier-signature").one()
        assert refreshed.id == plumber_id
        assert refreshed.content_json["palette"] == {"primary": "#123456"}
        assert refreshed.status == DemoSiteStatus.ACTIVE.value
        assert refreshed.expires_at == SHOWCASE_EXPIRES_AT

    def test_rebuild_content_regenerates_an_existing_demo(self, db: Session) -> None:
        owner = _owner(db)
        plumber = showcase_demo_service.ensure_all(db, owner)[0][0]
        plumber.content_json = {"businessName": "Ancien contenu"}
        db.commit()

        showcase_demo_service.ensure_all(db, owner, rebuild_content=True)

        refreshed = db.query(DemoSite).filter(DemoSite.slug == "exemple-plombier-signature").one()
        assert refreshed.content_json["businessName"] == "Plomberie Kerhuel"

    def test_never_takes_over_the_demo_of_a_real_prospect(self, db: Session) -> None:
        owner = _owner(db)
        _prospect_demo(db, owner, slug="exemple-plombier-signature")

        with pytest.raises(ShowcaseSlugTakenError):
            showcase_demo_service.ensure_one(db, owner, SHOWCASE_DEMO_SITES[0])


class TestNothingEndsAShowroomDemo:
    def test_the_expiry_pass_cleans_a_prospect_demo_but_never_a_showroom_one(
        self, db: Session, expiry_side_effects_stubbed: None
    ) -> None:
        owner = _owner(db)
        _prospect_demo(db, owner)
        long_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=400)
        showroom = showcase_demo_service.ensure_one(db, owner, SHOWCASE_DEMO_SITES[0])[0]
        showroom.demo_link_sent_at = long_ago
        showroom.expires_at = long_ago
        db.commit()
        dormant_showroom = DemoSite(
            user_id=owner.id,
            slug="exemple-dormant",
            business_name="Vitrine endormie",
            template_id="dental",
            status=DemoSiteStatus.EXPIRED.value,
            is_showcase=True,
            content_json={"businessName": "Vitrine endormie"},
            expires_at=long_ago,
        )
        db.add(dormant_showroom)
        db.commit()

        cleaned = asyncio.run(demo_site_service.expire_due_sites(db))

        assert cleaned == 1
        assert db.query(DemoSite).filter(DemoSite.slug == "garage-central").one().status == DemoSiteStatus.DELETED.value
        db.refresh(showroom)
        assert showroom.status == DemoSiteStatus.ACTIVE.value
        assert showroom.content_json["businessName"] == "Plomberie Kerhuel"
        db.refresh(dormant_showroom)
        assert dormant_showroom.status == DemoSiteStatus.EXPIRED.value
        assert dormant_showroom.content_json is not None

    def test_the_withdrawn_page_knows_no_showroom_demo_while_the_public_page_serves_it(self, db: Session) -> None:
        owner = _owner(db)
        showroom = showcase_demo_service.ensure_one(db, owner, SHOWCASE_DEMO_SITES[0])[0]
        client = _client(db)

        public = client.get(f"{demo_sites_router.prefix}/public/{showroom.slug}")
        assert public.status_code == 200
        assert public.json()["is_showcase"] is True
        assert public.json()["expiry_date_label"] is None

        showroom.status = DemoSiteStatus.EXPIRED.value
        db.commit()
        assert client.get(f"{demo_sites_router.prefix}/public/{showroom.slug}/withdrawn").status_code == 404
        assert client.post(f"{demo_sites_router.prefix}/public/{showroom.slug}/revive").status_code == 404

    def test_an_email_carrying_its_link_starts_no_countdown(self, db: Session) -> None:
        owner = _owner(db)
        showroom = showcase_demo_service.ensure_one(db, owner, SHOWCASE_DEMO_SITES[0])[0]

        started = demo_site_service.start_demo_ttl(db, showroom, datetime.now(UTC))
        demo_site_service.restart_demo_ttl(db, showroom, datetime.now(UTC))

        assert started is False
        assert showroom.demo_link_sent_at is None
        assert showroom.expires_at == SHOWCASE_EXPIRES_AT

    def test_the_cms_space_pass_skips_a_showroom_demo(self, db: Session) -> None:
        owner = _owner(db)
        showcase_demo_service.ensure_all(db, owner)
        now = datetime.now(UTC)

        assert StoryblokPreswapService.next_site_without_space(db, now) is None

        fresh_prospect_demo = _prospect_demo(
            db, owner, demo_link_sent_at=None, expires_at=datetime(2099, 1, 1), created_at=now.replace(tzinfo=None)
        )
        assert StoryblokPreswapService.next_site_without_space(db, now) is fresh_prospect_demo

    def test_the_home_counter_of_live_demos_ignores_showroom_demos(self, db: Session) -> None:
        owner = _owner(db)
        showcase_demo_service.ensure_all(db, owner)
        _prospect_demo(db, owner)

        stats = asyncio.run(dashboard_stats(period_days=0, current_user=owner, db=db))

        assert stats.demo_sites_active == 1
