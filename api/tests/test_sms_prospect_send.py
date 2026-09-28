"""A prospect SMS rendered from the library: it fits one segment, or it is not sent."""

import asyncio

import pytest
from sqlalchemy.orm import Session

import services.sms_service as sms_module
from models.ai_assistant import AiAssistant
from models.prospect_db import ProspectDB
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from services.ai_assistant.assistant_service import ai_assistant_service
from services.sms_service import SmsService
from tests.assistant_fakes import AcceptingSmsProvider, AsyncCallRecorder

# An 80-character demo slug: no template fits one segment with it.
_LONG_SLUG = "garage-de-la-grande-place-et-des-environs-de-charleville-mezieres-et-alentours-sud"


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> AcceptingSmsProvider:
    """An accepting SMS provider, an open legal window and a silent notification."""
    monkeypatch.setattr(SmsService, "legal_window_refusal", lambda self: None)
    monkeypatch.setattr(sms_module.notification_service, "notify_sms_event", AsyncCallRecorder())
    return AcceptingSmsProvider()


def _prospect(db: Session) -> ProspectDB:
    prospect = ProspectDB(
        name="Garage Martin",
        category="Garage automobile",
        phone="06 11 22 33 44",
        country="FR",
        source="google",
        confidence=2,
        user_id=7,
    )
    db.add(prospect)
    db.commit()
    return prospect


def _send(db: Session, provider: AcceptingSmsProvider, demo_url: str) -> sms_module.SmsSendOutcome:
    config = SmsConfig(user_id=7, sender="Dibodev")
    db.add(config)
    db.commit()
    return asyncio.run(
        SmsService(provider=provider).send_to_prospect(
            db, user_id=7, prospect=_prospect(db), config=config, demo_url=demo_url, cold=True
        )
    )


def test_a_template_that_overflows_one_segment_is_refused_and_never_sent(
    db: Session, provider: AcceptingSmsProvider
) -> None:
    outcome = _send(db, provider, f"https://demo.dibodev.fr/s/{_LONG_SLUG}")

    assert not outcome.sent
    assert outcome.reason is not None and "trop long" in outcome.reason and "2 SMS" in outcome.reason
    assert len(outcome.reason) <= 160  # the campaign queue keeps 160 characters of it
    assert provider.texts == []
    assert db.query(SmsMessage).count() == 0


def test_a_template_that_fits_one_segment_is_sent(db: Session, provider: AcceptingSmsProvider) -> None:
    outcome = _send(db, provider, "https://demo.dibodev.fr/s/garage-martin")

    assert outcome.sent
    [text] = provider.texts
    assert "demo.dibodev.fr/s/garage-martin" in text and text.endswith("STOP au 36180")
    assert outcome.message is not None and outcome.message.segments == 1


def test_a_receptionist_sms_looks_its_assistant_up_once(
    db: Session, provider: AcceptingSmsProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The template's fallback, the guard, the link and the countdown all read the same lookup."""
    prospect = _prospect(db)
    assistant = ai_assistant_service.create(
        db, user_id=7, business_name="Garage Martin", prospect_id=prospect.id, country="FR", use_brand_color=False
    )
    lookups: list[tuple[int, int]] = []

    def counting_lookup(db: Session, *, prospect_id: int, user_id: int) -> AiAssistant | None:
        lookups.append((prospect_id, user_id))
        return assistant

    monkeypatch.setattr(ai_assistant_service, "get_active_for_prospect", counting_lookup)
    config = SmsConfig(user_id=7, sender="Dibodev")
    db.add(config)
    db.commit()

    outcome = asyncio.run(
        SmsService(provider=provider).send_to_prospect(
            db, user_id=7, prospect=prospect, config=config, demo_url="", cold=True, template_key="assistant-24-7"
        )
    )

    assert outcome.sent
    assert lookups == [(prospect.id, 7)]
    assert "/s/ia/garage-martin " in provider.texts[0]
    assert assistant.demo_link_sent_at is not None


@pytest.mark.parametrize(
    ("sender", "text", "reason"),
    [
        ("", "Nouvelle demande", "Renseignez un nom d'expéditeur dans Paramètres → Relance SMS"),
        ("Dibodev", "a" * 161, "Message trop long : il partirait en 2 SMS. Raccourcissez-le pour tenir en 1 seul."),
    ],
)
def test_the_manual_and_the_service_sms_refuse_alike(
    db: Session, provider: AcceptingSmsProvider, sender: str, text: str, reason: str
) -> None:
    """The typed SMS and the receptionist's alert share the same guards: a sender name, one segment."""
    config = SmsConfig(user_id=7, sender=sender)
    db.add(config)
    db.commit()
    service = SmsService(provider=provider)

    service_outcome = asyncio.run(
        service.send_service_message(
            db, user_id=7, config=config, to_e164="+33611223344", text=text, recipient_name="Garage"
        )
    )
    manual_outcome = asyncio.run(service.send_manual(db, user_id=7, config=config, to_raw="06 11 22 33 44", text=text))

    assert (service_outcome.sent, service_outcome.reason) == (False, reason)
    assert (manual_outcome.sent, manual_outcome.reason) == (False, reason)
    assert provider.texts == []


def test_an_empty_service_sms_is_refused(db: Session, provider: AcceptingSmsProvider) -> None:
    config = SmsConfig(user_id=7, sender="Dibodev")
    db.add(config)
    db.commit()

    outcome = asyncio.run(
        SmsService(provider=provider).send_service_message(
            db, user_id=7, config=config, to_e164="+33611223344", text="   ", recipient_name="Garage"
        )
    )

    assert (outcome.sent, outcome.reason) == (False, "Message vide")
    assert provider.texts == []
