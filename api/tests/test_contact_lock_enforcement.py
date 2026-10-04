"""The cross-module lock holds on every sending path: manual SMS relance, campaign SMS and campaign email.

A prospect another module reserved is left out or skipped right before the send, and every message
actually sent refreshes its own module's stamp, so the lock counts from the module's last message.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.orm import Session

import services.campaign_queue_service as cqs
import services.email_signatures as email_signatures
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from services.campaign_queue_service import CampaignQueueService
from services.contact_lock_service import MODULE_AI_ASSISTANT, MODULE_WEBSITES
from services.demo_site_service import demo_site_service
from services.sms_config_service import sms_config_service
from services.sms_relance_service import SmsRelanceCandidate, sms_relance_service
from services.sms_service import sms_service

_USER_ID = 7
_NOW: datetime = datetime.now(UTC).replace(tzinfo=None)


class _FakeDB:
    """Counts commits, the only database call left once the dispatch helpers are stubbed."""

    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


def _stamped_prospect(module: str | None, days_ago: int) -> SimpleNamespace:
    """A prospect stub carrying a mobile, an email and the lock columns."""
    return SimpleNamespace(
        id=42,
        name="Garage Martin",
        email="garage@example.com",
        phone="06 12 34 56 78",
        country="FR",
        do_not_contact=False,
        contacted_by_module=module,
        contacted_by_module_at=_NOW - timedelta(days=days_ago) if module else None,
    )


def _emailed_prospect(db: Session, *, name: str, slug: str, reserved_by: str | None) -> ProspectDB:
    """A prospect emailed 40 days ago without reply, with a mobile and a live demo."""
    prospect = ProspectDB(
        user_id=_USER_ID,
        name=name,
        category="Garage",
        source="google_maps",
        phone="06 12 34 56 78",
        email=f"{slug}@example.com",
        contacted_by_module=reserved_by,
        contacted_by_module_at=_NOW - timedelta(days=10) if reserved_by else None,
    )
    db.add(prospect)
    db.flush()
    db.add(
        EmailLog(
            user_id=_USER_ID,
            prospect_id=prospect.id,
            recipient_email=prospect.email,
            subject="Votre site",
            body_html="<p>Bonjour</p>",
            provider="resend",
            status="sent",
            sent_at=_NOW - timedelta(days=40),
        )
    )
    db.add(
        DemoSite(
            user_id=_USER_ID,
            prospect_id=prospect.id,
            slug=slug,
            business_name=name,
            status="active",
            expires_at=datetime.now(UTC) + timedelta(days=10),
        )
    )
    db.commit()
    return prospect


def test_the_manual_relance_leaves_out_a_prospect_another_module_reserved(db: Session) -> None:
    """The SMS page never offers a website relance to a prospect the receptionist module just approached."""
    free = _emailed_prospect(db, name="Garage Martin", slug="garage-martin", reserved_by=None)
    reserved = _emailed_prospect(db, name="Plomberie Vidal", slug="plomberie-vidal", reserved_by=MODULE_AI_ASSISTANT)

    manual = sms_relance_service.find_candidates(db, _USER_ID)
    planned = sms_relance_service.find_relance_projection_candidates(db, _USER_ID)

    assert [candidate.prospect.id for candidate in manual] == [free.id]
    # The forecast keeps him: his planned row is then skipped with a visible reason.
    assert {candidate.prospect.id for candidate in planned} == {free.id, reserved.id}


def _relance_candidate(prospect: SimpleNamespace) -> SmsRelanceCandidate:
    return SmsRelanceCandidate(
        prospect=prospect,
        demo_site=SimpleNamespace(status="active", slug="garage-martin", video_status=None),
        demo_url="https://demo.example.com/garage-martin",
    )


def _stub_relance_send(monkeypatch: pytest.MonkeyPatch, *, sent: bool) -> None:
    async def send_to_prospect(_db: object, **_kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(sent=sent, reason=None if sent else "Refusé")

    monkeypatch.setattr(sms_config_service, "get", lambda _db, _user_id: SimpleNamespace(sender="GarageMartin"))
    monkeypatch.setattr(sms_service, "send_to_prospect", send_to_prospect)
    monkeypatch.setattr(demo_site_service, "restart_demo_ttl", lambda _db, _site, _sent_at: None)


def test_a_relance_sms_sent_stamps_the_websites_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Manual or automated, the relance is a website contact: the receptionist module waits from here."""
    _stub_relance_send(monkeypatch, sent=True)
    prospect = _stamped_prospect(None, 0)

    assert asyncio.run(sms_relance_service.send_relance(None, _USER_ID, _relance_candidate(prospect))) is True

    assert prospect.contacted_by_module == MODULE_WEBSITES
    assert prospect.contacted_by_module_at is not None


def test_a_refused_relance_sms_leaves_the_lock_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_relance_send(monkeypatch, sent=False)
    prospect = _stamped_prospect(None, 0)

    assert asyncio.run(sms_relance_service.send_relance(None, _USER_ID, _relance_candidate(prospect))) is False

    assert prospect.contacted_by_module is None


def _sms_item(prospect: SimpleNamespace) -> SimpleNamespace:
    """A queued receptionist SMS."""
    campaign = SimpleNamespace(user_id=_USER_ID, channel="sms", sms_template_key="assistant-24-7")
    return SimpleNamespace(
        prospect=prospect,
        campaign=campaign,
        queue_type="initial",
        sms_template_key=None,
        sms_message_id=None,
        status="sending",
        skip_reason=None,
    )


def _stub_sms_dispatch(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Make the campaign SMS path sendable and return the ids of the prospects actually texted."""
    texted: list[int] = []

    async def send_to_prospect(_db: object, **kwargs: Any) -> SimpleNamespace:
        texted.append(kwargs["prospect"].id)
        return SimpleNamespace(sent=True, reason=None, message=None)

    monkeypatch.setattr(sms_config_service, "get", lambda _db, _user_id: SimpleNamespace(sender="GarageMartin"))
    monkeypatch.setattr(sms_service, "legal_window_refusal", lambda country=None: None)
    monkeypatch.setattr(sms_service, "send_to_prospect", send_to_prospect)
    monkeypatch.setattr(CampaignQueueService, "_has_active_assistant", lambda _self, _pid, _uid: True)
    monkeypatch.setattr(CampaignQueueService, "_active_demo_for_prospect", lambda _self, _pid, _uid: None)
    monkeypatch.setattr(CampaignQueueService, "_schedule_follow_ups", lambda _self, _item: None)
    return texted


def test_a_campaign_sms_skips_a_prospect_another_module_took_since_the_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    texted = _stub_sms_dispatch(monkeypatch)
    item = _sms_item(_stamped_prospect(MODULE_WEBSITES, 3))
    db = _FakeDB()

    asyncio.run(CampaignQueueService(db)._dispatch_sms(item))

    assert texted == []
    assert db.commits == 1
    assert item.status == "skipped"
    assert item.skip_reason == "Réservé par un autre module"


def test_a_campaign_sms_sent_refreshes_the_lock_of_its_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """The reservation made at the enqueue moves to the actual send."""
    texted = _stub_sms_dispatch(monkeypatch)
    prospect = _stamped_prospect(MODULE_AI_ASSISTANT, 20)
    reserved_at: datetime = prospect.contacted_by_module_at
    item = _sms_item(prospect)

    asyncio.run(CampaignQueueService(_FakeDB())._dispatch_sms(item))

    assert texted == [42]
    assert item.status == "sent"
    assert prospect.contacted_by_module == MODULE_AI_ASSISTANT
    assert prospect.contacted_by_module_at > reserved_at


def _email_item(prospect: SimpleNamespace) -> SimpleNamespace:
    """A queued J1 email of a website campaign."""
    campaign = SimpleNamespace(user_id=_USER_ID, channel="email", include_video=False, user=None)
    template = SimpleNamespace(subject="Votre site", body_html="<p>Bonjour</p>", signature_id=None, layout="plain")
    return SimpleNamespace(
        prospect=prospect,
        campaign=campaign,
        template=template,
        user=SimpleNamespace(name="Marc Dupont", company_name=None, postal_address=None),
        user_id=_USER_ID,
        campaign_id=3,
        queue_type="initial",
        ab_variant=None,
        status="sending",
        skip_reason=None,
        email_log_id=None,
    )


def _stub_email_dispatch(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Make the campaign email path sendable as a website campaign and return the addresses actually emailed."""
    emailed: list[str] = []

    class _Sender:
        def __init__(self, _db: object) -> None:
            pass

        def replace_variables(self, text: str, _variables: dict[str, str]) -> str:
            return text

        async def send_via_user_identity(self, **kwargs: Any) -> dict[str, object]:
            emailed.append(kwargs["recipient_email"])
            return {"success": True, "email_log_id": 5}

    monkeypatch.setattr(cqs.unsubscribe_service, "is_unsubscribed", lambda _db, _email: False)
    monkeypatch.setattr(CampaignQueueService, "_email_campaign_module", lambda _self, _campaign: MODULE_WEBSITES)
    monkeypatch.setattr(CampaignQueueService, "_demo_link_for_prospect", lambda _self, _pid, _uid, _variant: "")
    monkeypatch.setattr(CampaignQueueService, "_schedule_follow_ups", lambda _self, _item: None)
    monkeypatch.setattr(cqs.PricingService, "sale_price_cents", lambda _db, _uid: 50000)
    monkeypatch.setattr(cqs.AssistantPricingService, "monthly_price_cents", lambda _db, _uid: 2900)
    monkeypatch.setattr(cqs.EmailVariables, "build_for_prospect", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(cqs, "EmailSendingService", _Sender)
    monkeypatch.setattr(email_signatures, "render_signature_html", lambda *_args, **_kwargs: "")
    return emailed


def test_a_campaign_email_skips_a_prospect_another_module_took_since_the_enqueue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emailed = _stub_email_dispatch(monkeypatch)
    item = _email_item(_stamped_prospect(MODULE_AI_ASSISTANT, 3))
    db = _FakeDB()

    asyncio.run(CampaignQueueService(db)._dispatch(item))

    assert emailed == []
    assert db.commits == 1
    assert item.status == "skipped"
    assert item.skip_reason == "Réservé par un autre module"


def test_a_campaign_email_sent_refreshes_the_lock_of_its_module(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each message of the sequence pushes the other modules back: the lock counts from the last one."""
    emailed = _stub_email_dispatch(monkeypatch)
    prospect = _stamped_prospect(MODULE_WEBSITES, 20)
    reserved_at: datetime = prospect.contacted_by_module_at
    item = _email_item(prospect)

    asyncio.run(CampaignQueueService(_FakeDB())._dispatch(item))

    assert emailed == ["garage@example.com"]
    assert item.status == "sent"
    assert prospect.contacted_by_module == MODULE_WEBSITES
    assert prospect.contacted_by_module_at > reserved_at
