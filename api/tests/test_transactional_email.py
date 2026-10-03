"""Unit tests for the transactional send path.

An invoice or payment email is owed to a client, so it must not carry the
prospection footer — and an address that unsubscribed from outreach must stay
billable. Outreach keeps both guards untouched.
"""

import asyncio
from types import SimpleNamespace

import pytest

import services.email_sending_service as sending
from enums.sending_provider import SendingProvider

# Building an EmailLog configures the whole mapper registry — import the models it
# reaches so SQLAlchemy can resolve every relationship by name.
from models.campaign_follow_up import CampaignFollowUp  # noqa: F401
from models.payment_account import PaymentAccount  # noqa: F401
from services.email_sending_service import EmailSendingService


class _FakeDB:
    """Session stand-in recording the email log the service builds."""

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, row: object) -> None:
        self.added.append(row)

    def get(self, _model: type, _ident: object) -> None:
        return None

    def commit(self) -> None:
        return None

    def refresh(self, row: object) -> None:
        row.id = 1


class _RecordingResend:
    """Captures the payload handed to the Resend provider."""

    def __init__(self) -> None:
        self.sent: dict = {}

    async def send_email(self, **kwargs: object) -> dict:
        self.sent = kwargs
        return {"message_id": "msg_1", "provider": "resend"}


def _service(monkeypatch: pytest.MonkeyPatch, *, unsubscribed: bool) -> tuple[EmailSendingService, _RecordingResend]:
    """Build a service whose provider, unsubscribe state and side effects are stubbed."""
    monkeypatch.setattr(
        sending,
        "resolve_sending_identity",
        lambda _db, _user_id: SimpleNamespace(
            provider=SendingProvider.RESEND.value,
            gmail_account=None,
            from_email="leo@mail.dibodev.fr",
            from_name="Léo",
            resend_api_key="re_test",
        ),
    )
    monkeypatch.setattr(sending.unsubscribe_service, "is_unsubscribed", lambda _db, _email: unsubscribed)
    monkeypatch.setattr(
        sending.unsubscribe_service, "add_unsubscribe_footer", lambda body, _link, **_kwargs: body + "<!--FOOTER-->"
    )
    monkeypatch.setattr(sending.unsubscribe_service, "generate_unsubscribe_link", lambda *_args: "https://x/u")

    service = EmailSendingService(_FakeDB())
    resend = _RecordingResend()
    service.resend_service = resend
    monkeypatch.setattr(service, "_mark_prospect_contacted", lambda _prospect_id: None)

    async def _no_capture(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(service, "_capture_email_sent", _no_capture)
    return service, resend


def _send(service: EmailSendingService, *, is_transactional: bool) -> dict:
    return asyncio.run(
        service.send_via_user_identity(
            user_id=1,
            recipient_email="client@example.fr",
            subject="Votre facture",
            body_html="<p>Bonjour</p>",
            is_transactional=is_transactional,
        )
    )


def test_transactional_email_carries_no_unsubscribe_footer(monkeypatch: pytest.MonkeyPatch) -> None:
    """An invoice email is not outreach: no footer, no one-click unsubscribe header."""
    service, resend = _service(monkeypatch, unsubscribed=False)
    result = _send(service, is_transactional=True)

    assert result["success"] is True
    assert "FOOTER" not in resend.sent["html_body"]
    assert resend.sent["extra_headers"] is None


def test_transactional_email_still_sent_to_an_unsubscribed_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unsubscribing from prospection must not make a client unbillable."""
    service, _resend = _service(monkeypatch, unsubscribed=True)
    assert _send(service, is_transactional=True)["success"] is True


def test_outreach_keeps_the_footer_and_the_unsubscribe_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    """The RGPD footer and the unsubscribe block still apply to prospection."""
    service, resend = _service(monkeypatch, unsubscribed=False)
    _send(service, is_transactional=False)
    assert "FOOTER" in resend.sent["html_body"]
    assert resend.sent["extra_headers"] is not None

    blocked, _resend = _service(monkeypatch, unsubscribed=True)
    with pytest.raises(Exception, match="désabonné"):
        _send(blocked, is_transactional=False)
