"""Canada (CASL): no commercial email reaches a Canadian prospect until the sender's profile has a postal address.

The campaign queue holds the send back with the reason the campaign page shows; once the address is in the
profile, the email leaves with the sender's identification in its footer. Other countries are untouched, and
so are transactional emails.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.orm import Session

import services.email_sending_service as sending
from enums.sending_provider import SendingProvider
from models.campaign import Campaign, CampaignStatus
from models.email_log import EmailLog
from models.email_queue import EmailQueue
from models.email_template import EmailTemplate
from models.prospect_db import ProspectDB
from models.user import User
from services.campaign_queue_service import CampaignQueueService
from services.email_sending_service import EmailSendingService
from services.resend_service import ResendService
from services.unsubscribe_service import POSTAL_ADDRESS_MISSING_REFUSAL

_ADDRESS = "12 rue des Lilas, 35000 Rennes, France"
_SENDER_LINE = "Envoyé par Dibodev (Jean Dupont), 12 rue des Lilas, 35000 Rennes, France"


@pytest.fixture
def sent_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """The payloads handed to Resend, the sending identity and the funnel capture being stubbed."""
    payloads: list[dict[str, Any]] = []

    async def send_email(_self: ResendService, **kwargs: Any) -> dict[str, str]:
        payloads.append(kwargs)
        return {"message_id": f"msg_{len(payloads)}", "provider": "resend"}

    async def no_capture(_self: EmailSendingService, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(
        sending,
        "resolve_sending_identity",
        lambda _db, _user_id: SimpleNamespace(
            provider=SendingProvider.RESEND.value,
            gmail_account=None,
            from_email="jean@mail.example.com",
            from_name="Jean",
            resend_api_key="re_test",
        ),
    )
    monkeypatch.setattr(sending.settings, "dev_email_redirect", None)
    monkeypatch.setattr(ResendService, "send_email", send_email)
    monkeypatch.setattr(EmailSendingService, "_capture_email_sent", no_capture)
    return payloads


def _sender(db: Session, *, postal_address: str | None) -> User:
    sender = User(
        name="Jean Dupont",
        email="jean@example.com",
        hashed_password="x",
        company_name="Dibodev",
        postal_address=postal_address,
    )
    db.add(sender)
    db.flush()
    return sender


def _prospect(db: Session, sender: User, *, country: str) -> ProspectDB:
    prospect = ProspectDB(
        user_id=sender.id,
        name="Paysagement Tremblay",
        category="paysagiste",
        source="google_maps",
        email="info@tremblay.example",
        country=country,
    )
    db.add(prospect)
    db.flush()
    return prospect


def _claimed_first_email(db: Session, sender: User, prospect: ProspectDB) -> EmailQueue:
    """A J1 of an active email campaign, just claimed by the worker."""
    template = EmailTemplate(user_id=sender.id, name="Premier email", subject="Votre site", body_html="<p>Bonjour</p>")
    db.add(template)
    db.flush()
    campaign = Campaign(
        user_id=sender.id, name="Québec", status=CampaignStatus.ACTIVE, channel="email", template_id=template.id
    )
    db.add(campaign)
    db.flush()
    item = EmailQueue(
        user_id=sender.id,
        campaign_id=campaign.id,
        prospect_id=prospect.id,
        template_id=template.id,
        queue_type="initial",
        follow_up_index=0,
        scheduled_at=datetime.now(UTC).replace(tzinfo=None),
        status="sending",
    )
    db.add(item)
    db.commit()
    return item


def test_a_canadian_email_is_held_back_until_the_profile_has_a_postal_address(
    db: Session, sent_emails: list[dict[str, Any]]
) -> None:
    sender = _sender(db, postal_address=None)
    item = _claimed_first_email(db, sender, _prospect(db, sender, country="CA"))

    asyncio.run(CampaignQueueService(db)._dispatch(item))

    assert item.status == "skipped"
    assert item.skip_reason == POSTAL_ADDRESS_MISSING_REFUSAL
    assert sent_emails == []
    assert db.query(EmailLog).count() == 0


def test_a_canadian_email_leaves_with_the_sender_identification_once_the_address_is_set(
    db: Session, sent_emails: list[dict[str, Any]]
) -> None:
    sender = _sender(db, postal_address=_ADDRESS)
    item = _claimed_first_email(db, sender, _prospect(db, sender, country="CA"))

    asyncio.run(CampaignQueueService(db)._dispatch(item))

    assert item.status == "sent"
    assert len(sent_emails) == 1
    assert _SENDER_LINE in sent_emails[0]["html_body"]


def test_a_french_email_leaves_without_any_postal_address(db: Session, sent_emails: list[dict[str, Any]]) -> None:
    sender = _sender(db, postal_address=None)
    item = _claimed_first_email(db, sender, _prospect(db, sender, country="FR"))

    asyncio.run(CampaignQueueService(db)._dispatch(item))

    assert item.status == "sent"
    assert len(sent_emails) == 1
    assert "Envoyé par" not in sent_emails[0]["html_body"]
    assert "Se désabonner" in sent_emails[0]["html_body"]


def test_an_immediate_follow_up_to_canada_answers_the_reason(db: Session, sent_emails: list[dict[str, Any]]) -> None:
    sender = _sender(db, postal_address=None)
    prospect = _prospect(db, sender, country="CA")
    item = _claimed_first_email(db, sender, prospect)

    result = asyncio.run(CampaignQueueService(db).send_followup_now(item.campaign, prospect.id, item.template_id))

    assert result == {"success": False, "error": POSTAL_ADDRESS_MISSING_REFUSAL}
    assert sent_emails == []


def test_the_shared_send_path_refuses_a_canadian_email_without_an_address(
    db: Session, sent_emails: list[dict[str, Any]]
) -> None:
    """Even without the check the routes run first, the shared send path refuses and logs nothing."""
    sender = _sender(db, postal_address=None)
    prospect = _prospect(db, sender, country="CA")
    service = EmailSendingService(db)

    assert service.sender_identification_refusal(sender.id, str(prospect.id)) == POSTAL_ADDRESS_MISSING_REFUSAL
    with pytest.raises(Exception, match="Adresse postale manquante"):
        asyncio.run(
            service.send_via_user_identity(
                user_id=sender.id,
                recipient_email=prospect.email,
                subject="Votre site",
                body_html="<p>Bonjour</p>",
                prospect_id=str(prospect.id),
            )
        )
    assert sent_emails == []
    assert db.query(EmailLog).count() == 0


def test_a_transactional_email_to_a_canadian_client_is_never_held_back(
    db: Session, sent_emails: list[dict[str, Any]]
) -> None:
    sender = _sender(db, postal_address=None)
    prospect = _prospect(db, sender, country="CA")

    result = asyncio.run(
        EmailSendingService(db).send_via_user_identity(
            user_id=sender.id,
            recipient_email=prospect.email,
            subject="Votre facture",
            body_html="<p>Bonjour</p>",
            prospect_id=str(prospect.id),
            is_transactional=True,
        )
    )

    assert result["success"] is True
    assert len(sent_emails) == 1
