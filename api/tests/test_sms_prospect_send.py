"""A prospect SMS rendered from the library: it fits one segment, or it is not sent."""

import asyncio

import pytest
from sqlalchemy.orm import Session

import services.sms_service as sms_module
from models.prospect_db import ProspectDB
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from services.sms_service import SmsService
from tests.assistant_fakes import AcceptingSmsProvider, AsyncCallRecorder

# A demo slug as long as the site's used to allow (80 characters): no template fits one segment with it.
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
