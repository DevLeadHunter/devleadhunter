"""A client who joins their editing space is announced to the owner once, whether the button or the watch sees it."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import services.cms_invitation_watch_service as watch_module
import services.demo_site_service as demo_site_module
import services.notification_service as notification_module
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from services.cms_invitation_watch_service import cms_invitation_watch_service
from services.demo_site_service import demo_site_service
from services.notification_service import notification_service
from services.storyblok_service import storyblok_service


def _invited_site(
    db: Session,
    *,
    slug: str = "tp-motorsport",
    status: str = DemoSiteStatus.ACTIVE.value,
    collaborator_status: str | None = "pending",
    is_invite_sent: bool = True,
) -> DemoSite:
    site = DemoSite(
        user_id=7,
        prospect_id=179,
        slug=slug,
        business_name="TP Motorsport Sàrl",
        status=status,
        email="telmo@example.com",
        storyblok_space_id=296169916056514,
        storyblok_invite_sent=is_invite_sent,
        storyblok_collaborator_status=collaborator_status,
        expires_at=datetime.now(UTC) + timedelta(days=21),
    )
    db.add(site)
    db.commit()
    return site


def _storyblok_answers(monkeypatch: pytest.MonkeyPatch, collaborator_status: str) -> None:
    async def get_collaborator_status(space_id: int, email: str) -> str:
        return collaborator_status

    monkeypatch.setattr(storyblok_service, "get_collaborator_status", get_collaborator_status)


@pytest.fixture
def joined_notifications(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """The « joined » notifications the refresh raises, the push itself stubbed."""
    raised: list[dict[str, Any]] = []

    async def notify_cms_joined(_db: Session, **kwargs: Any) -> None:
        raised.append(kwargs)

    monkeypatch.setattr(demo_site_module.notification_service, "notify_cms_joined", notify_cms_joined)
    return raised


def test_the_first_join_notifies_the_owner_once(
    db: Session, monkeypatch: pytest.MonkeyPatch, joined_notifications: list[dict[str, Any]]
) -> None:
    """A second check of a client who already joined stays silent."""
    site = _invited_site(db)
    _storyblok_answers(monkeypatch, "joined")

    asyncio.run(demo_site_service.refresh_cms_collaborator_status(db, site))
    first_joined_at = site.storyblok_joined_at
    asyncio.run(demo_site_service.refresh_cms_collaborator_status(db, site))

    assert site.storyblok_collaborator_status == "joined"
    assert first_joined_at is not None
    assert site.storyblok_joined_at == first_joined_at
    assert [(notification["user_id"], notification["prospect_id"]) for notification in joined_notifications] == [
        (7, 179)
    ]
    assert joined_notifications[0]["demo_site_id"] == site.id


def test_an_invitation_not_accepted_yet_notifies_nobody(
    db: Session, monkeypatch: pytest.MonkeyPatch, joined_notifications: list[dict[str, Any]]
) -> None:
    """Pending, missing from the collaborators or unreadable, the invitation stays pending and silent."""
    site = _invited_site(db)

    for collaborator_status in ("pending", "not_invited", "unknown"):
        _storyblok_answers(monkeypatch, collaborator_status)
        asyncio.run(demo_site_service.refresh_cms_collaborator_status(db, site))

    assert site.storyblok_collaborator_status == "pending"
    assert site.storyblok_joined_at is None
    assert joined_notifications == []


def test_a_failed_notification_never_fails_the_refresh(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    site = _invited_site(db)
    _storyblok_answers(monkeypatch, "joined")

    async def broken_push(_db: Session, **kwargs: Any) -> None:
        raise RuntimeError("push service down")

    monkeypatch.setattr(demo_site_module.notification_service, "notify_cms_joined", broken_push)

    refreshed = asyncio.run(demo_site_service.refresh_cms_collaborator_status(db, site))

    assert refreshed.storyblok_collaborator_status == "joined"
    assert refreshed.storyblok_joined_at is not None


def test_storyblok_is_asked_without_holding_a_database_connection(
    db: Session, monkeypatch: pytest.MonkeyPatch, joined_notifications: list[dict[str, Any]]
) -> None:
    site = _invited_site(db)
    db.refresh(site)
    is_transaction_open_while_asked: list[bool] = []

    async def get_collaborator_status(space_id: int, email: str) -> str:
        is_transaction_open_while_asked.append(db.in_transaction())
        return "pending"

    monkeypatch.setattr(storyblok_service, "get_collaborator_status", get_collaborator_status)

    asyncio.run(demo_site_service.refresh_cms_collaborator_status(db, site))

    assert is_transaction_open_while_asked == [False]


def test_the_owner_is_told_who_joined_and_lands_on_their_prospect(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same shape as the demo pushes: the prospect in the title, the site module then the action in the body."""
    pushed: list[dict[str, Any]] = []
    logged: list[dict[str, Any]] = []

    async def dispatch(**kwargs: Any) -> None:
        pushed.append(kwargs)

    monkeypatch.setattr(notification_service, "_dispatch", dispatch)
    monkeypatch.setattr(notification_module.activity_log_service, "record", lambda **kwargs: logged.append(kwargs))
    prospect = ProspectDB(name="TP Motorsport", category="Garage", source="google", confidence=2, user_id=7)
    db.add(prospect)
    db.commit()

    asyncio.run(
        notification_service.notify_cms_joined(
            db, user_id=7, prospect_id=prospect.id, fallback_name="TP Motorsport Sàrl", demo_site_id=108
        )
    )

    assert [(push["title"], push["body"], push["url"], push["tag"]) for push in pushed] == [
        (
            "🔑 TP Motorsport",
            "🌐 Site web · A rejoint son espace d'édition",
            f"/dashboard/my-prospects?open={prospect.id}",
            "cms-joined-108",
        )
    ]
    assert [(entry["action"], entry["title"], entry["entity_id"]) for entry in logged] == [
        ("cms_joined", "TP Motorsport · A rejoint son espace d'édition", prospect.id)
    ]


def test_the_watch_rereads_only_the_pending_invitations(
    db: Session, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Joined, uninvited and deleted sites are never polled, and one site's failure never skips the next one."""
    refreshed_slugs: list[str] = []

    async def refresh_cms_collaborator_status(_db: Session, demo_site: DemoSite) -> DemoSite:
        refreshed_slugs.append(demo_site.slug)
        if demo_site.slug == "garage-sans-reponse":
            raise RuntimeError("Storyblok did not answer")
        return demo_site

    monkeypatch.setattr(watch_module, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(
        watch_module.demo_site_service, "refresh_cms_collaborator_status", refresh_cms_collaborator_status
    )
    _invited_site(db, slug="garage-sans-reponse")
    _invited_site(db, slug="tp-motorsport")
    _invited_site(db, slug="deja-rejoint", collaborator_status="joined")
    _invited_site(db, slug="pas-invite", collaborator_status=None, is_invite_sent=False)
    _invited_site(db, slug="site-supprime", status=DemoSiteStatus.DELETED.value)

    asyncio.run(cms_invitation_watch_service.check_pending_invitations())

    assert refreshed_slugs == ["garage-sans-reponse", "tp-motorsport"]
