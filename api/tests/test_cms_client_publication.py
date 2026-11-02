"""The owner hears about the changes their client publishes from their own space, never about their own publications."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi import BackgroundTasks
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import api.v1.routes.webhooks as webhooks_module
import services.cms_client_publication_service as publication_module
from core.config import settings
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from services.cms_client_publication_service import CmsClientPublicationService, cms_client_publication_service
from services.notification_service import notification_service
from services.storyblok_service import storyblok_service
from services.templates import registry
from services.templates.site_content import storyblok_asset_key

_OWNER_ACCOUNT_ID = 180126754529568
_CLIENT_ACCOUNT_ID = 235478865162412
_TEMPLATE_ID = "mechanic-pitlane"
_HERO_PHOTO = "https://img.example/garage.jpg"
_FAQ = [{"question": "Faites-vous la carrosserie ?", "answer": "Non, nous travaillons avec des partenaires."}]
_PREVIOUS_CONTENT: dict[str, Any] = {"businessName": "TP Motorsport Sàrl", "heroImage": _HERO_PHOTO, "faq": _FAQ}


def _client_edit(**changes: Any) -> dict[str, Any]:
    """The site content once the client published some changes."""
    return {**_PREVIOUS_CONTENT, **changes}


def _cms_copy(url: str) -> str:
    """The address a push gives a photo's copy in the space library."""
    return f"https://a.storyblok.com/f/296169916056514/cdf44b5d09/{storyblok_asset_key(url)}.jpg"


def _site(db: Session, *, is_invite_sent: bool = True) -> DemoSite:
    site = DemoSite(
        user_id=7,
        prospect_id=None,
        slug="tp-motorsport",
        business_name="TP Motorsport Sàrl",
        status=DemoSiteStatus.ACTIVE.value,
        template_id=_TEMPLATE_ID,
        storyblok_space_id=296169916056514,
        storyblok_public_token="public-token",
        storyblok_invite_sent=is_invite_sent,
        content_json=dict(_PREVIOUS_CONTENT),
        expires_at=datetime.now(UTC) + timedelta(days=21),
    )
    db.add(site)
    db.commit()
    return site


@pytest.fixture
def storyblok_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The Storyblok lookups made, the client being the latest publisher unless a test says otherwise."""
    calls: list[str] = []

    async def get_token_owner_id() -> int:
        calls.append("token owner")
        return _OWNER_ACCOUNT_ID

    async def get_recent_story_publisher_id(space_id: int, published_after: datetime) -> int:
        calls.append("publisher")
        return _CLIENT_ACCOUNT_ID

    monkeypatch.setattr(storyblok_service, "get_token_owner_id", get_token_owner_id)
    monkeypatch.setattr(storyblok_service, "get_recent_story_publisher_id", get_recent_story_publisher_id)
    return calls


@pytest.fixture
def published_notifications(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """The « published » notifications raised, the push itself stubbed and the sessions on the test database."""
    raised: list[dict[str, Any]] = []

    async def notify_cms_published(_db: Session, **kwargs: Any) -> None:
        raised.append(kwargs)

    monkeypatch.setattr(publication_module, "SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(notification_service, "notify_cms_published", notify_cms_published)
    return raised


def test_a_client_publication_notifies_the_owner_with_the_sections_it_changed(
    db: Session, storyblok_calls: list[str], published_notifications: list[dict[str, Any]]
) -> None:
    site = _site(db)
    edited_faq = [
        {"question": "Faites-vous la carrosserie ?", "answer": "Non, mais nous avons des partenaires à Sion."}
    ]

    asyncio.run(
        CmsClientPublicationService().notify_if_published_by_client(
            site.id, _PREVIOUS_CONTENT, _client_edit(faq=edited_faq)
        )
    )

    assert [(notification["user_id"], notification["demo_site_id"]) for notification in published_notifications] == [
        (7, site.id)
    ]
    assert published_notifications[0]["changed_section_labels"] == ["Questions fréquentes"]


def test_a_publication_by_the_owners_account_notifies_nobody(
    db: Session, monkeypatch: pytest.MonkeyPatch, published_notifications: list[dict[str, Any]]
) -> None:
    """Generation, dashboard edits and the owner's own clicks all publish with the Management token's account."""
    site = _site(db)

    async def same_account(*_args: Any) -> int:
        return _OWNER_ACCOUNT_ID

    monkeypatch.setattr(storyblok_service, "get_token_owner_id", same_account)
    monkeypatch.setattr(storyblok_service, "get_recent_story_publisher_id", same_account)

    asyncio.run(
        CmsClientPublicationService().notify_if_published_by_client(site.id, _PREVIOUS_CONTENT, _client_edit(faq=[]))
    )

    assert published_notifications == []


def test_a_site_whose_client_was_never_invited_asks_storyblok_nothing(
    db: Session, storyblok_calls: list[str], published_notifications: list[dict[str, Any]]
) -> None:
    site = _site(db, is_invite_sent=False)

    asyncio.run(
        CmsClientPublicationService().notify_if_published_by_client(site.id, _PREVIOUS_CONTENT, _client_edit(faq=[]))
    )

    assert storyblok_calls == []
    assert published_notifications == []


def test_an_unreadable_activity_feed_notifies_nobody_and_raises_nothing(
    db: Session, monkeypatch: pytest.MonkeyPatch, published_notifications: list[dict[str, Any]]
) -> None:
    site = _site(db)

    async def owner(*_args: Any) -> int:
        return _OWNER_ACCOUNT_ID

    async def storyblok_down(*_args: Any, **_kwargs: Any) -> httpx.Response:
        raise httpx.ConnectError("Storyblok unreachable")

    monkeypatch.setattr(storyblok_service, "_token", "management-token")
    monkeypatch.setattr(storyblok_service, "get_token_owner_id", owner)
    monkeypatch.setattr(storyblok_service, "_storyblok_request", storyblok_down)

    asyncio.run(
        CmsClientPublicationService().notify_if_published_by_client(site.id, _PREVIOUS_CONTENT, _client_edit(faq=[]))
    )

    assert published_notifications == []


def test_a_client_publishing_again_within_ten_minutes_notifies_once(
    db: Session, storyblok_calls: list[str], published_notifications: list[dict[str, Any]]
) -> None:
    site = _site(db)
    publications = CmsClientPublicationService()

    for _ in range(3):
        asyncio.run(publications.notify_if_published_by_client(site.id, _PREVIOUS_CONTENT, _client_edit(faq=[])))

    assert len(published_notifications) == 1


def test_the_changed_sections_ignore_a_photo_the_cms_only_copied() -> None:
    """A stored photo comes back from the CMS as its library copy: only a photo the client uploaded is a change."""
    copied = _client_edit(heroImage=_cms_copy(_HERO_PHOTO))
    uploaded = _client_edit(heroImage="https://a.storyblok.com/f/296169916056514/1200x800/9a8b7c6d5e/devanture.jpg")

    assert registry.changed_section_labels(_TEMPLATE_ID, _PREVIOUS_CONTENT, copied) == []
    assert registry.changed_section_labels(_TEMPLATE_ID, _PREVIOUS_CONTENT, uploaded) == ["En-tête"]


def test_the_activity_feed_names_the_latest_publisher_only_when_recent(monkeypatch: pytest.MonkeyPatch) -> None:
    """The feed lists every action newest first; a publication older than the webhook's is never taken for it."""
    published_at = datetime(2026, 10, 28, 9, 30, tzinfo=UTC)
    feed = {
        "activities": [
            {
                "activity": {
                    "key": "asset.update",
                    "owner_id": _OWNER_ACCOUNT_ID,
                    "created_at": "2026-10-28T09:31:00.000Z",
                }
            },
            {
                "activity": {
                    "key": "story.publish",
                    "owner_id": _CLIENT_ACCOUNT_ID,
                    "created_at": "2026-10-28T09:30:00.000Z",
                }
            },
            {
                "activity": {
                    "key": "story.publish",
                    "owner_id": _OWNER_ACCOUNT_ID,
                    "created_at": "2026-10-27T14:57:50.695Z",
                }
            },
        ]
    }

    async def activity_feed(_client: httpx.AsyncClient, method: str, url: str, **_kwargs: Any) -> httpx.Response:
        return httpx.Response(200, json=feed, request=httpx.Request(method, url))

    monkeypatch.setattr(storyblok_service, "_token", "management-token")
    monkeypatch.setattr(storyblok_service, "_storyblok_request", activity_feed)

    recent = asyncio.run(
        storyblok_service.get_recent_story_publisher_id(296169916056514, published_at - timedelta(minutes=5))
    )
    stale = asyncio.run(
        storyblok_service.get_recent_story_publisher_id(296169916056514, published_at + timedelta(minutes=1))
    )

    assert recent == _CLIENT_ACCOUNT_ID
    assert stale is None


def test_the_token_owner_is_asked_once(monkeypatch: pytest.MonkeyPatch) -> None:
    requested_urls: list[str] = []

    async def users_me(_client: httpx.AsyncClient, method: str, url: str, **_kwargs: Any) -> httpx.Response:
        requested_urls.append(url)
        return httpx.Response(200, json={"user": {"id": _OWNER_ACCOUNT_ID}}, request=httpx.Request(method, url))

    monkeypatch.setattr(storyblok_service, "_token", "management-token")
    monkeypatch.setattr(storyblok_service, "_token_owner_id", None)
    monkeypatch.setattr(storyblok_service, "_storyblok_request", users_me)

    owner_ids = [asyncio.run(storyblok_service.get_token_owner_id()) for _ in range(2)]

    assert owner_ids == [_OWNER_ACCOUNT_ID, _OWNER_ACCOUNT_ID]
    assert requested_urls == ["https://mapi.storyblok.com/v1/users/me"]


def test_the_webhook_hands_the_publication_to_the_check_once_the_content_is_saved(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = _site(db)
    edited_faq = [
        {"question": "Faites-vous la carrosserie ?", "answer": "Non, mais nous avons des partenaires à Sion."}
    ]
    published_story = {
        "component": "page",
        "body": registry.to_storyblok_site_content(_TEMPLATE_ID, _client_edit(faq=edited_faq)),
    }

    async def fetch_published_home_content(public_token: str) -> dict[str, Any]:
        return published_story

    class PublishRequest:
        async def body(self) -> bytes:
            return json.dumps({"action": "published", "space_id": 296169916056514, "full_slug": "home"}).encode()

    monkeypatch.setattr(settings, "storyblok_webhook_secret", None)
    monkeypatch.setattr(storyblok_service, "fetch_published_home_content", fetch_published_home_content)
    monkeypatch.setattr(webhooks_module.activity_log_service, "record", lambda **kwargs: None)
    tasks = BackgroundTasks()

    asyncio.run(
        webhooks_module.storyblok_webhook(PublishRequest(), background_tasks=tasks, webhook_signature="", db=db)
    )

    db.refresh(site)
    assert site.content_json["faq"] == edited_faq
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].func == cms_client_publication_service.notify_if_published_by_client
    assert tasks.tasks[0].args[:2] == (site.id, _PREVIOUS_CONTENT)
    assert tasks.tasks[0].args[2]["faq"] == edited_faq
