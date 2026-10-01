"""The contact page of the marketing site: the message reaches the publisher's inbox and one reply answers the visitor."""

import asyncio
from datetime import datetime
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.requests import Request

import api.v1.routes.site_contact as site_contact_route
import services.site_contact_service as site_contact_module
from core.config import settings
from enums.user_role import UserRole
from models.user import User
from schemas.site_contact import SiteContactRequest
from services.notification_service import notification_service
from services.rate_limiter import SlidingWindowRateLimiter
from services.sending_identity import SendingIdentity, SendingNotConfiguredError
from services.site_contact_email import SiteContactEmail
from services.site_contact_service import SiteContactDeliveryError, SiteContactService

_CAMPAIGN_IDENTITY = SendingIdentity(
    provider="resend", from_email="leo@mail.dibodev.fr", from_name="Léo", resend_api_key="re_test"
)
_THURSDAY_MORNING = datetime(2026, 10, 1, 9, 42)


class _RecordingResend:
    """A Resend client that keeps the emails it is asked to send, or refuses every one of them."""

    def __init__(self, *, refuses: bool = False) -> None:
        self.sent: list[dict[str, Any]] = []
        self._refuses = refuses

    async def send_email(self, **kwargs: Any) -> dict[str, str]:
        if self._refuses:
            raise RuntimeError("Resend API error 500")
        self.sent.append(kwargs)
        return {"message_id": "re_1", "provider": "resend"}


@pytest.fixture
def notified(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[dict[str, Any]]]:
    """The contact and error notifications the service raises."""
    calls: dict[str, list[dict[str, Any]]] = {"contact": [], "error": []}

    async def notify_site_contact(**kwargs: Any) -> None:
        calls["contact"].append(kwargs)

    async def notify_error(**kwargs: Any) -> None:
        calls["error"].append(kwargs)

    monkeypatch.setattr(site_contact_module.notification_service, "notify_site_contact", notify_site_contact)
    monkeypatch.setattr(site_contact_module.notification_service, "notify_error", notify_error)
    return calls


@pytest.fixture
def campaign_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """The admin sends through Resend, from the campaigns address."""
    monkeypatch.setattr(SiteContactService, "_resolve_sender_identity", staticmethod(lambda db: _CAMPAIGN_IDENTITY))


def _message(**overrides: Any) -> SiteContactRequest:
    """A visitor's message about credits, with the fields a test wants to change."""
    fields: dict[str, Any] = {
        "topic": "credits",
        "name": "Camille Martin",
        "email": "camille@studio-exemple.fr",
        "message": "Bonjour, combien coûte un crédit ?",
    }
    fields.update(overrides)
    return SiteContactRequest(**fields)


def _visitor_request(address: str = "203.0.113.9") -> Request:
    """The HTTP request of a visitor seen behind nginx."""
    return Request({"type": "http", "headers": [(b"x-forwarded-for", address.encode())], "client": ("127.0.0.1", 80)})


def test_the_message_reaches_the_inbox_and_a_reply_answers_the_visitor(
    db: Session, notified: dict[str, list[dict[str, Any]]], campaign_identity: None
) -> None:
    resend = _RecordingResend()

    asyncio.run(SiteContactService(resend).send(db, _message()))

    [email] = resend.sent
    assert email["to_email"] == settings.contact_form_to
    assert email["reply_to"] == "camille@studio-exemple.fr"
    assert email["from_email"] == "leo@mail.dibodev.fr"
    assert email["subject"] == "Nouveau message · Camille Martin · Crédits et facturation"
    assert "combien coûte un crédit" in email["text_body"]


def test_the_visitor_text_is_escaped_in_the_html_email(
    db: Session, notified: dict[str, list[dict[str, Any]]], campaign_identity: None
) -> None:
    resend = _RecordingResend()

    asyncio.run(SiteContactService(resend).send(db, _message(message="<script>alert(1)</script>")))

    [email] = resend.sent
    assert "<script>" not in email["html_body"]
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in email["html_body"]


def test_a_mobile_can_be_called_or_texted_on_whatsapp_from_the_email() -> None:
    email = SiteContactEmail.render(_message(phone="06 12 34 56 78"), received_at=_THURSDAY_MORNING)

    assert 'href="tel:+33612345678"' in email.html
    assert 'href="https://wa.me/33612345678"' in email.html


def test_a_landline_can_be_called_but_not_texted_from_the_email() -> None:
    email = SiteContactEmail.render(_message(phone="01 23 45 67 89"), received_at=_THURSDAY_MORNING)

    assert 'href="tel:+33123456789"' in email.html
    assert "wa.me" not in email.html


def test_without_a_phone_the_email_only_offers_to_reply() -> None:
    email = SiteContactEmail.render(_message(), received_at=_THURSDAY_MORNING)

    assert "tel:" not in email.html
    assert "Téléphone" not in email.text


def test_the_reply_opens_with_a_subject_in_the_language_of_the_site() -> None:
    email = SiteContactEmail.render(_message(locale="en"), received_at=_THURSDAY_MORNING)

    assert 'href="mailto:camille@studio-exemple.fr?subject=Your%20message%20on%20devleadhunter.fr"' in email.html
    assert "Langue du site : Anglais" in email.text


@pytest.mark.parametrize(
    ("received_at", "deadline"),
    [
        (datetime(2026, 10, 1, 9, 42), "vendredi 2 octobre 2026"),
        (datetime(2026, 10, 2, 18, 0), "lundi 5 octobre 2026"),
        (datetime(2026, 10, 3, 11, 0), "lundi 5 octobre 2026"),
        (datetime(2026, 10, 4, 22, 30), "lundi 5 octobre 2026"),
    ],
)
def test_the_answer_is_due_the_next_weekday(received_at: datetime, deadline: str) -> None:
    email = SiteContactEmail.render(_message(), received_at=received_at)

    assert f"À répondre au plus tard {deadline}" in email.text


def test_the_message_keeps_its_line_breaks_in_the_email() -> None:
    email = SiteContactEmail.render(_message(message="Bonjour,\r\nÀ bientôt"), received_at=_THURSDAY_MORNING)

    assert "Bonjour,<br>À bientôt" in email.html


def test_the_admins_are_notified_once_the_mail_left(
    db: Session, notified: dict[str, list[dict[str, Any]]], campaign_identity: None
) -> None:
    asyncio.run(SiteContactService(_RecordingResend()).send(db, _message(topic="privacy")))

    assert notified["contact"] == [
        {
            "name": "Camille Martin",
            "email": "camille@studio-exemple.fr",
            "topic_label": "Données personnelles",
            "message": "Bonjour, combien coûte un crédit ?",
        }
    ]
    assert notified["error"] == []


def test_a_refused_mail_fails_and_tells_the_admins_who_wrote(
    db: Session, notified: dict[str, list[dict[str, Any]]], campaign_identity: None
) -> None:
    with pytest.raises(SiteContactDeliveryError):
        asyncio.run(SiteContactService(_RecordingResend(refuses=True)).send(db, _message()))

    [error] = notified["error"]
    assert "camille@studio-exemple.fr" in error["message"]
    assert notified["contact"] == []


def test_the_admin_email_account_sends_before_another_admin(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    db.add(User(id=1, name="Autre admin", email="autre@dibodev.fr", hashed_password="x", role=UserRole.ADMIN.value))
    db.add(User(id=2, name="Léo", email=settings.admin_email, hashed_password="x", role=UserRole.SUPER_ADMIN.value))
    db.commit()
    monkeypatch.setattr(
        site_contact_module,
        "resolve_sending_identity",
        lambda session, user_id: SendingIdentity(
            provider="resend", from_email=f"user{user_id}@mail.dibodev.fr", from_name=""
        ),
    )

    identity = SiteContactService._resolve_sender_identity(db)

    assert identity.from_email == "user2@mail.dibodev.fr"


def test_an_admin_who_cannot_send_through_resend_is_skipped(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    db.add(User(id=1, name="Léo", email=settings.admin_email, hashed_password="x", role=UserRole.SUPER_ADMIN.value))
    db.add(User(id=2, name="Autre admin", email="autre@dibodev.fr", hashed_password="x", role=UserRole.ADMIN.value))
    db.add(User(id=3, name="Client", email="client@exemple.fr", hashed_password="x", role=UserRole.USER.value))
    db.commit()

    def resolve(session: Session, user_id: int) -> SendingIdentity:
        if user_id == 1:
            raise SendingNotConfiguredError("Resend non configuré")
        return SendingIdentity(provider="resend", from_email=f"user{user_id}@mail.dibodev.fr", from_name="")

    monkeypatch.setattr(site_contact_module, "resolve_sending_identity", resolve)

    identity = SiteContactService._resolve_sender_identity(db)

    assert identity.from_email == "user2@mail.dibodev.fr"


def test_a_name_written_on_several_lines_becomes_one_line() -> None:
    assert _message(name="Camille\n  Martin").name == "Camille Martin"


def test_an_empty_phone_is_dropped() -> None:
    assert _message(phone="   ").phone is None


@pytest.mark.parametrize("overrides", [{"name": "   "}, {"message": ""}, {"email": "camille"}, {"message": "x" * 5001}])
def test_an_incomplete_message_is_refused(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        _message(**overrides)


def test_a_filled_honeypot_is_answered_without_sending(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[SiteContactRequest] = []

    async def send(session: Session, request: SiteContactRequest) -> None:
        sent.append(request)

    monkeypatch.setattr(site_contact_route.site_contact_service, "send", send)
    monkeypatch.setattr(site_contact_route, "site_contact_limiter", SlidingWindowRateLimiter(5, 3600))

    response = asyncio.run(
        site_contact_route.send_contact_message(_message(website="https://spam.example"), _visitor_request(), db)
    )

    assert response.status == "sent"
    assert sent == []


def test_a_visitor_is_stopped_after_five_messages_in_an_hour(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    async def send(session: Session, request: SiteContactRequest) -> None:
        return None

    monkeypatch.setattr(site_contact_route.site_contact_service, "send", send)
    monkeypatch.setattr(site_contact_route, "site_contact_limiter", SlidingWindowRateLimiter(5, 3600))
    for _ in range(5):
        asyncio.run(site_contact_route.send_contact_message(_message(), _visitor_request(), db))

    with pytest.raises(HTTPException) as refusal:
        asyncio.run(site_contact_route.send_contact_message(_message(), _visitor_request(), db))

    assert refusal.value.status_code == 429


def test_the_contact_notification_reaches_every_admin_with_a_short_excerpt(monkeypatch: pytest.MonkeyPatch) -> None:
    dispatched: list[dict[str, Any]] = []

    async def dispatch(**kwargs: Any) -> None:
        dispatched.append(kwargs)

    monkeypatch.setattr(notification_service, "_dispatch", dispatch)
    monkeypatch.setattr(notification_service, "_active_admin_ids", lambda context: [1, 2])

    asyncio.run(
        notification_service.notify_site_contact(
            name="Camille Martin", email="camille@studio-exemple.fr", topic_label="Autre", message="Bonjour\n" * 200
        )
    )

    assert [call["user_id"] for call in dispatched] == [1, 2]
    assert dispatched[0]["title"] == "📨 Camille Martin"
    assert dispatched[0]["body"].startswith("Page contact · Autre · camille@studio-exemple.fr — « Bonjour Bonjour")
    assert dispatched[0]["body"].endswith("… »")
    assert len(dispatched[0]["body"]) < 300


def test_a_message_that_did_not_leave_answers_503(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    async def send(session: Session, request: SiteContactRequest) -> None:
        raise SiteContactDeliveryError("Resend API error 500")

    monkeypatch.setattr(site_contact_route.site_contact_service, "send", send)
    monkeypatch.setattr(site_contact_route, "site_contact_limiter", SlidingWindowRateLimiter(5, 3600))

    with pytest.raises(HTTPException) as refusal:
        asyncio.run(site_contact_route.send_contact_message(_message(), _visitor_request(), db))

    assert refusal.value.status_code == 503
