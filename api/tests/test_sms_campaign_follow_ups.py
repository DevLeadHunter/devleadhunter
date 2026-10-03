"""An SMS campaign relances like an email campaign: first SMS, then its relance after the chosen sending days.

The relance is a library relance step of the campaign, scheduled when the first SMS leaves and counted
in sending days on the prospect's clock. It holds back on a reply, and a relance built around the video
leaves only with the prospect's video: its fallback recalls an email the prospect never received.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

import services.sms_service as sms_service_module
from enums.sms_message_kind import SmsMessageKind
from models.campaign import Campaign, CampaignStatus
from models.campaign_follow_up import CampaignFollowUp
from models.demo_site import DemoSite
from models.email_queue import EmailQueue
from models.prospect_db import ProspectDB
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from models.sms_reply import SmsReply
from models.user import User
from schemas.campaign import CampaignFollowUpCreate
from services.campaign_follow_up_rules import CampaignFollowUpRules
from services.campaign_queue_service import CampaignQueueService
from services.send_policy_service import send_policy_service
from services.sms_auto_campaign_service import SMS_AUTO_RELANCE_KIND
from services.sms_service import sms_service
from tests.assistant_fakes import AcceptingSmsProvider, AsyncCallRecorder

_USER_ID = 7
_VIDEO_RELANCE_KEY = "offre-a-vie-video"


@pytest.fixture
def provider(db: Session, monkeypatch: pytest.MonkeyPatch) -> AcceptingSmsProvider:
    """A sender with a phone and an SMS config, an accepting provider, and an always open legal window."""
    db.add(
        User(
            id=_USER_ID,
            name="Léo Guillaume",
            email="leo@example.com",
            hashed_password="hash",
            contact_phone="06 42 19 38 12",
        )
    )
    db.add(SmsConfig(user_id=_USER_ID, sender="Dibodev"))
    db.commit()
    accepting = AcceptingSmsProvider()
    monkeypatch.setattr(sms_service, "_provider", accepting)
    monkeypatch.setattr(sms_service, "legal_window_refusal", lambda country=None: None)
    monkeypatch.setattr(sms_service_module.notification_service, "notify_sms_event", AsyncCallRecorder())
    return accepting


def _campaign(db: Session, *, relance_key: str = _VIDEO_RELANCE_KEY, delay_days: int = 3) -> Campaign:
    campaign = Campaign(
        user_id=_USER_ID,
        name="Vague 4 — SMS France",
        status=CampaignStatus.ACTIVE,
        channel="sms",
        sms_template_key="direct",
        started_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(campaign)
    db.flush()
    db.add(CampaignFollowUp(campaign_id=campaign.id, sms_template_key=relance_key, delay_days=delay_days, position=1))
    db.commit()
    return campaign


def _prospect(db: Session, campaign: Campaign, *, has_video: bool = True) -> ProspectDB:
    prospect = ProspectDB(
        user_id=_USER_ID, name="Jardins Martin", category="Paysagiste", source="google", phone="06 12 34 56 78"
    )
    db.add(prospect)
    db.flush()
    db.add(
        DemoSite(
            user_id=_USER_ID,
            prospect_id=prospect.id,
            slug="jardins-martin",
            business_name=prospect.name,
            status="active",
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=21),
            video_status="ready" if has_video else None,
        )
    )
    campaign.prospects = [prospect]
    db.commit()
    return prospect


def _queued(db: Session, campaign: Campaign, prospect: ProspectDB) -> EmailQueue:
    item = EmailQueue(
        user_id=_USER_ID,
        campaign_id=campaign.id,
        prospect_id=prospect.id,
        queue_type="initial",
        follow_up_index=0,
        scheduled_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1),
        status="sending",
    )
    db.add(item)
    db.commit()
    return item


def _relance_of(db: Session, campaign: Campaign) -> EmailQueue:
    return db.query(EmailQueue).filter(EmailQueue.campaign_id == campaign.id, EmailQueue.queue_type == "followup").one()


def _send_relance_now(db: Session, relance: EmailQueue) -> None:
    relance.status = "sending"
    db.commit()
    asyncio.run(CampaignQueueService(db)._dispatch_sms(relance))


def test_the_first_sms_schedules_its_relance_after_the_chosen_sending_days(
    db: Session, provider: AcceptingSmsProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _campaign(db, delay_days=5)
    prospect = _prospect(db, campaign)
    first_sms = _queued(db, campaign, prospect)
    counted_delays: list[int] = []
    original_slot = send_policy_service.follow_up_slot

    def follow_up_slot(policy: object, sent_at: datetime, delay_days: int, *, timezone_name: str) -> datetime:
        counted_delays.append(delay_days)
        return original_slot(policy, sent_at, delay_days, timezone_name=timezone_name)

    monkeypatch.setattr(send_policy_service, "follow_up_slot", follow_up_slot)

    asyncio.run(CampaignQueueService(db)._dispatch_sms(first_sms))

    relance = _relance_of(db, campaign)
    assert (first_sms.status, first_sms.sms_message_id) == ("sent", db.query(SmsMessage).one().id)
    assert counted_delays == [5]
    assert (relance.status, relance.sms_template_key, relance.follow_up_index) == ("pending", _VIDEO_RELANCE_KEY, 1)
    assert relance.scheduled_at > first_sms.scheduled_at + timedelta(days=5)


def test_the_relance_sends_the_video_link_as_the_prospect_s_relance(
    db: Session, provider: AcceptingSmsProvider
) -> None:
    campaign = _campaign(db)
    prospect = _prospect(db, campaign)
    asyncio.run(CampaignQueueService(db)._dispatch_sms(_queued(db, campaign, prospect)))
    relance = _relance_of(db, campaign)

    _send_relance_now(db, relance)

    kinds = [message.kind for message in db.query(SmsMessage).order_by(SmsMessage.id)]
    assert relance.status == "sent"
    assert kinds == [SmsMessageKind.FIRST_CONTACT.value, SmsMessageKind.FOLLOW_UP.value]
    assert "/s/v/jardins-martin" in provider.texts[1]
    assert relance.sms_message_id == db.query(SmsMessage).order_by(SmsMessage.id.desc()).first().id


def test_a_video_relance_without_the_video_is_skipped_instead_of_recalling_an_email(
    db: Session, provider: AcceptingSmsProvider
) -> None:
    campaign = _campaign(db)
    prospect = _prospect(db, campaign, has_video=False)
    asyncio.run(CampaignQueueService(db)._dispatch_sms(_queued(db, campaign, prospect)))
    relance = _relance_of(db, campaign)

    _send_relance_now(db, relance)

    assert (relance.status, relance.skip_reason) == ("skipped", "Pas de vidéo prête pour la relance")
    assert len(provider.texts) == 1


def test_a_consigned_sms_reply_holds_the_relance_back(db: Session, provider: AcceptingSmsProvider) -> None:
    campaign = _campaign(db)
    prospect = _prospect(db, campaign)
    asyncio.run(CampaignQueueService(db)._dispatch_sms(_queued(db, campaign, prospect)))
    relance = _relance_of(db, campaign)
    db.add(SmsReply(user_id=_USER_ID, prospect_id=prospect.id, from_number="+33612345678", body="Oui, rappelez-moi"))
    db.commit()

    _send_relance_now(db, relance)

    assert (relance.status, relance.skip_reason) == ("skipped", "Le prospect a répondu")
    assert len(provider.texts) == 1


def test_a_demo_that_dies_before_the_relance_records_the_skip_at_the_first_sms(
    db: Session, provider: AcceptingSmsProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign = _campaign(db)
    prospect = _prospect(db, campaign)
    monkeypatch.setattr(
        send_policy_service,
        "follow_up_slot",
        lambda policy, sent_at, delay_days, *, timezone_name: sent_at + timedelta(days=60),
    )

    asyncio.run(CampaignQueueService(db)._dispatch_sms(_queued(db, campaign, prospect)))

    relance = _relance_of(db, campaign)
    assert (relance.status, relance.skip_reason) == ("skipped", "Site démo expiré avant la relance")


class TestRules:
    @staticmethod
    def _sms_campaign() -> Campaign:
        return Campaign(user_id=_USER_ID, name="SMS", channel="sms", sms_template_key="direct")

    @staticmethod
    def _step(**template: str | int) -> CampaignFollowUpCreate:
        return CampaignFollowUpCreate(delay_days=3, position=1, **template)

    def test_a_video_relance_may_follow_a_first_sms(self) -> None:
        steps = [self._step(sms_template_key=_VIDEO_RELANCE_KEY)]

        assert CampaignFollowUpRules.refusal(self._sms_campaign(), steps, first_contact_key="direct") is None

    def test_a_relance_recalling_an_email_cannot_follow_a_first_sms(self) -> None:
        steps = [self._step(sms_template_key="rappel-court")]

        refusal = CampaignFollowUpRules.refusal(self._sms_campaign(), steps, first_contact_key="direct")

        assert refusal is not None and "rappelle votre email" in refusal

    def test_an_sms_campaign_sends_one_relance_at_most(self) -> None:
        steps = [self._step(sms_template_key=_VIDEO_RELANCE_KEY), self._step(sms_template_key="refonte-relance")]

        refusal = CampaignFollowUpRules.refusal(self._sms_campaign(), steps, first_contact_key="direct")

        assert refusal == "Une campagne SMS envoie un premier SMS puis une seule relance."

    def test_the_relance_sells_the_offer_of_the_first_sms(self) -> None:
        steps = [self._step(sms_template_key="assistant-prix-cash")]

        refusal = CampaignFollowUpRules.refusal(self._sms_campaign(), steps, first_contact_key="direct")

        assert refusal is not None and "même offre" in refusal

    def test_an_email_campaign_relances_with_email_templates(self) -> None:
        email_campaign = Campaign(user_id=_USER_ID, name="Email", channel="email")
        steps = [self._step(sms_template_key=_VIDEO_RELANCE_KEY)]

        refusal = CampaignFollowUpRules.refusal(email_campaign, steps, first_contact_key=None)

        assert refusal == "Choisissez un modèle d'email pour chaque relance."

    def test_the_j30_campaign_is_already_a_relance(self) -> None:
        j30_campaign = Campaign(user_id=_USER_ID, name="J+30", channel="sms", system_kind=SMS_AUTO_RELANCE_KIND)

        refusal = CampaignFollowUpRules.refusal(
            j30_campaign, [self._step(sms_template_key=_VIDEO_RELANCE_KEY)], first_contact_key="rappel-court"
        )

        assert refusal is not None

    def test_a_step_names_an_email_template_or_an_sms_template(self) -> None:
        with pytest.raises(ValueError):
            CampaignFollowUpCreate(template_id=3, sms_template_key=_VIDEO_RELANCE_KEY)
