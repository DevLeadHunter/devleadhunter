"""
Web Push notification schemas — VAPID key, subscription payload, test result,
plus the persisted in-app notification history.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PushKeys(BaseModel):
    """Client encryption keys from a browser PushSubscription."""

    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    """A browser push subscription registered by the PWA."""

    endpoint: str = Field(..., max_length=500)
    keys: PushKeys
    user_agent: str = Field(default="", max_length=400)


class PushSubscriptionDelete(BaseModel):
    """Endpoint to unregister."""

    endpoint: str = Field(..., max_length=500)


class VapidKeyResponse(BaseModel):
    """Public VAPID key exposed to the browser to subscribe."""

    public_key: str | None = None
    configured: bool = False


class TestNotificationResult(BaseModel):
    """Diagnostic returned by the test endpoint so the PWA can tell where push breaks."""

    configured: bool = False
    subscriptions: int = 0
    delivered: int = 0
    failed: int = 0
    detail: str | None = None


class DemoEventIn(BaseModel):
    """A behavioural event beaconed from a live demo/video page (public, unauthenticated)."""

    demo_slug: str = Field(..., max_length=255)
    event: str = Field(..., max_length=64)
    label: str | None = Field(default=None, max_length=120)
    host: str | None = Field(default=None, max_length=255)
    seconds: int | None = None
    max_scroll: int | None = None
    # Free-text left by the prospect through the demo CTA banner (``demo_lead`` event).
    message: str | None = Field(default=None, max_length=1000)
    # Marketing channel that brought the visit ('email' / 'sms' / 'direct'), from the ``?src=`` link.
    channel: str | None = Field(default=None, max_length=16)
    browser_timezone: str | None = Field(default=None, max_length=64)
    browser_language: str | None = Field(default=None, max_length=35)
    is_automated_browser: bool = False


class NotificationOut(BaseModel):
    """One stored in-app notification, as returned to the settings history list."""

    id: int
    category: str
    level: str
    title: str
    body: str
    url: str
    read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    """A page of the user's notification history plus the current unread count."""

    items: list[NotificationOut]
    unread_count: int
