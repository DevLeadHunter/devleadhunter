"""An SMS campaign's results read like an email campaign's, its data told in SMS.

A send is the SMS it wrote: its time, its delivery failure, its cost. A reply is an SMS reply consigned
by hand (the sender is one-way) or the demo banner. Email and SMS campaigns compare with one another.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from models.campaign import Campaign, CampaignStatus
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.email_queue import EmailQueue
from models.prospect_db import ProspectDB
from models.sms_message import SmsMessage
from models.sms_reply import SmsReply
from schemas.campaign_results import CampaignManualReplyCreate
from services import campaign_results_service as results_module
from services.campaign_results_service import CampaignResultsService
from services.posthog_service import DemoSession

USER_ID = 7
LAUNCH = datetime(2026, 10, 12, 9, 30)


@pytest.fixture
def fake_sessions(monkeypatch: pytest.MonkeyPatch) -> list[DemoSession]:
    sessions: list[DemoSession] = []

    async def get_demo_sessions(slugs: list[str], since: datetime) -> list[DemoSession]:
        return [session for session in sessions if session.slug in slugs and session.started_at >= since]

    monkeypatch.setattr(results_module.posthog_service, "get_demo_sessions", get_demo_sessions)
    return sessions


def _campaign(db: Session, *, channel: str, name: str) -> Campaign:
    campaign = Campaign(user_id=USER_ID, name=name, status=CampaignStatus.ACTIVE, channel=channel, started_at=LAUNCH)
    db.add(campaign)
    db.flush()
    return campaign


def _prospect(db: Session, name: str, slug: str) -> ProspectDB:
    prospect = ProspectDB(
        name=name,
        category="paysagiste",
        source="google",
        confidence=2,
        user_id=USER_ID,
        phone="06 12 34 56 78",
        email_undeliverable=True,
    )
    db.add(prospect)
    db.flush()
    db.add(
        DemoSite(
            user_id=USER_ID,
            prospect_id=prospect.id,
            slug=slug,
            business_name=name,
            status="active",
            expires_at=LAUNCH + timedelta(days=21),
        )
    )
    return prospect


def _sms_send(
    db: Session,
    campaign: Campaign,
    prospect: ProspectDB,
    *,
    at: datetime,
    step: int = 0,
    sms_status: str = "delivered",
    price_cents: int = 6,
) -> None:
    message = SmsMessage(
        user_id=USER_ID,
        prospect_id=prospect.id,
        to_e164="+33612345678",
        sender="Dibodev",
        body="Bonjour",
        status=sms_status,
        segments=1,
        price_cents=price_cents,
        created_at=at,
    )
    db.add(message)
    db.flush()
    db.add(
        EmailQueue(
            user_id=USER_ID,
            campaign_id=campaign.id,
            prospect_id=prospect.id,
            queue_type="initial" if step == 0 else "followup",
            follow_up_index=step,
            scheduled_at=at,
            status="sent",
            sms_message_id=message.id,
        )
    )


def _session(slug: str, started_at: datetime) -> DemoSession:
    return DemoSession(
        slug=slug,
        session_id=f"{slug}-{started_at.isoformat()}",
        started_at=started_at,
        device_type="Mobile",
        city="Genève",
        interaction_count=4,
        time_on_page_seconds=35.0,
        engaged_seconds=20.0,
    )


@pytest.mark.asyncio
async def test_an_sms_campaign_counts_its_sms_like_mails(db: Session, fake_sessions: list[DemoSession]) -> None:
    campaign = _campaign(db, channel="sms", name="Vague 4 — SMS Suisse")
    reader = _prospect(db, "Jardins Martin", "jardins-martin")
    unreached = _prospect(db, "Garage Favre", "garage-favre")
    campaign.prospects = [reader, unreached]
    _sms_send(db, campaign, reader, at=LAUNCH)
    _sms_send(db, campaign, reader, at=LAUNCH + timedelta(days=3), step=1)
    _sms_send(db, campaign, unreached, at=LAUNCH + timedelta(minutes=30), sms_status="failed")
    db.add(
        SmsReply(
            user_id=USER_ID,
            prospect_id=reader.id,
            from_number="+33612345678",
            body="Oui ça m'intéresse, appelez-moi",
            received_at=LAUNCH + timedelta(days=3, hours=1),
            intent="interested",
        )
    )
    db.commit()
    fake_sessions.append(_session("jardins-martin", LAUNCH + timedelta(minutes=12)))

    results = await CampaignResultsService().build(db, USER_ID, campaign.id)

    assert results is not None
    assert results.channel == "sms"
    totals = results.totals
    assert (totals.contacted, totals.visited, totals.replied, totals.interested) == (2, 1, 1, 1)
    assert (totals.first_mails_sent, totals.follow_ups_sent, totals.bounced) == (2, 1, 1)
    assert totals.sms_cost_cents == 18
    [reply] = results.replies
    assert (reply.channel, reply.verdict, reply.answered_step) == ("sms", "interested", 1)
    assert all(not prospect.is_email_undeliverable for prospect in results.prospects)


@pytest.mark.asyncio
async def test_an_email_campaign_has_no_sms_cost(db: Session, fake_sessions: list[DemoSession]) -> None:
    campaign = _campaign(db, channel="email", name="Vague 4 — Email Suisse")
    campaign.prospects = [_prospect(db, "Jardins Martin", "jardins-martin")]
    db.commit()

    results = await CampaignResultsService().build(db, USER_ID, campaign.id)

    assert results is not None
    assert (results.channel, results.totals.sms_cost_cents) == ("email", None)


def test_a_reply_added_by_hand_on_an_sms_campaign_is_an_sms_reply_that_holds_the_relance_back(db: Session) -> None:
    campaign = _campaign(db, channel="sms", name="Vague 4 — SMS France")
    prospect = _prospect(db, "Jardins Martin", "jardins-martin")
    campaign.prospects = [prospect]
    _sms_send(db, campaign, prospect, at=LAUNCH)
    db.add(
        EmailQueue(
            user_id=USER_ID,
            campaign_id=campaign.id,
            prospect_id=prospect.id,
            queue_type="followup",
            follow_up_index=1,
            scheduled_at=LAUNCH + timedelta(days=3),
            status="pending",
            sms_template_key="offre-a-vie-video",
        )
    )
    db.commit()

    reply = CampaignResultsService().add_manual_reply(
        db,
        USER_ID,
        campaign.id,
        CampaignManualReplyCreate(prospect_id=prospect.id, verdict="refused", message="Non merci"),
    )

    consigned = db.query(SmsReply).one()
    relance = db.query(EmailQueue).filter(EmailQueue.queue_type == "followup").one()
    assert (reply.channel, reply.verdict, reply.answered_step) == ("sms", "refused", 0)
    assert (consigned.body, consigned.intent, consigned.from_number) == ("Non merci", "not_interested", "+33612345678")
    assert relance.status == "skipped"


@pytest.mark.asyncio
async def test_benchmarks_compare_email_and_sms_campaigns(db: Session, fake_sessions: list[DemoSession]) -> None:
    email_campaign = _campaign(db, channel="email", name="Vague 4 — Email France")
    sms_campaign = _campaign(db, channel="sms", name="Vague 4 — SMS France")
    emailed = _prospect(db, "Électricité Faure", "electricite-faure")
    texted = _prospect(db, "Plomberie Vidal", "plomberie-vidal")
    email_campaign.prospects = [emailed]
    sms_campaign.prospects = [texted]
    email_log = EmailLog(
        user_id=USER_ID,
        prospect_id=emailed.id,
        campaign_id=email_campaign.id,
        recipient_email="faure@example.com",
        subject="Votre site",
        body_html="<p>Bonjour</p>",
        provider="resend",
        status="delivered",
        sent_at=LAUNCH,
    )
    db.add(email_log)
    db.flush()
    db.add(
        EmailQueue(
            user_id=USER_ID,
            campaign_id=email_campaign.id,
            prospect_id=emailed.id,
            queue_type="initial",
            scheduled_at=LAUNCH,
            status="sent",
            email_log_id=email_log.id,
        )
    )
    _sms_send(db, sms_campaign, texted, at=LAUNCH)
    db.commit()

    benchmarks = await CampaignResultsService().build_benchmarks(db, USER_ID)

    channels = {benchmark.name: benchmark.channel for benchmark in benchmarks.campaigns}
    assert channels == {"Vague 4 — Email France": "email", "Vague 4 — SMS France": "sms"}
