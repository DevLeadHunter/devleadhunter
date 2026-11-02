"""A click on the number or email of the prospect's own site never reads as a click on the owner's contact."""

import asyncio
from typing import Any

import pytest
from sqlalchemy.orm import Session

import services.notification_service as notification_module
from services.notification_service import notification_service


def test_the_sites_own_contact_is_told_apart_from_the_owners(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """The site's links show the prospect's number and email; the banner chip and the withdrawn page show the owner's."""
    pushed_bodies: list[str] = []

    async def dispatch(**kwargs: Any) -> None:
        pushed_bodies.append(kwargs["body"])

    monkeypatch.setattr(notification_service, "_dispatch", dispatch)
    monkeypatch.setattr(notification_module.activity_log_service, "record", lambda **kwargs: None)

    for event in ("demo_site_phone_click", "demo_site_contact_click", "demo_phone_click", "demo_contact_click"):
        asyncio.run(
            notification_service.notify_demo_event(
                db, user_id=7, prospect_id=None, event_name=event, fallback_name="tp-motorsport"
            )
        )

    assert pushed_bodies == [
        "🌐 Site web · A cliqué le numéro de son site",
        "🌐 Site web · A cliqué l'email de son site",
        "🌐 Site web · A cliqué ton numéro",
        "🌐 Site web · A cliqué ton mail de contact",
    ]
