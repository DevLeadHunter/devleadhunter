"""A campaign's results count each prospect once, at the furthest stage the campaign's mails took them.

Visits are human sessions on the prospect's demo inside the campaign's window (after its first
mail, before a later campaign's first mail); replies come from captured mails, the demo banner
and replies added by hand; a paid order makes a sale.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from models.campaign import Campaign, CampaignStatus
from models.demo_site import DemoSite
from models.demo_site_lead import LEAD_STATUS_SUBMITTED, DemoSiteLead
from models.email_log import EmailLog
from models.email_queue import EmailQueue
from models.email_reply import EmailReply
from models.order import Order
from models.prospect_db import ProspectDB
from schemas.campaign_results import CampaignManualReplyCreate
from services import campaign_results_service as results_module
from services.campaign_results_service import CampaignResultsService
from services.posthog_service import DemoSession

USER_ID = 7
LAUNCH = datetime(2026, 9, 22, 9, 30)


def _prospect(db: Session, name: str, slug: str) -> ProspectDB:
    prospect = ProspectDB(name=name, category="paysagiste", source="google", confidence=2, user_id=USER_ID)
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


def _send(
    db: Session, campaign: Campaign, prospect: ProspectDB, *, at: datetime, step: int = 0, sent: bool = True
) -> EmailLog | None:
    email_log = None
    if sent:
        email_log = EmailLog(
            user_id=USER_ID,
            prospect_id=prospect.id,
            campaign_id=campaign.id,
            recipient_email=f"{prospect.id}@example.com",
            subject="Le site",
            body_html="<p>Bonjour</p>",
            provider="resend",
            status="delivered",
            sent_at=at,
        )
        db.add(email_log)
        db.flush()
    db.add(
        EmailQueue(
            user_id=USER_ID,
            campaign_id=campaign.id,
            prospect_id=prospect.id,
            queue_type="initial" if step == 0 else "followup",
            follow_up_index=step,
            scheduled_at=at,
            status="sent" if sent else "pending",
            email_log_id=email_log.id if email_log else None,
        )
    )
    return email_log


def _session(slug: str, started_at: datetime, *, interactions: int = 6, seconds: float | None = 40.0) -> DemoSession:
    return DemoSession(
        slug=slug,
        session_id=f"{slug}-{started_at.isoformat()}",
        started_at=started_at,
        device_type="Mobile",
        city="Lausanne",
        interaction_count=interactions,
        time_on_page_seconds=seconds,
        engaged_seconds=20.0,
    )


@pytest.fixture
def campaign(db: Session) -> Campaign:
    campaign = Campaign(
        user_id=USER_ID, name="Vague 3 — Suisse", status=CampaignStatus.COMPLETED, channel="email", started_at=LAUNCH
    )
    db.add(campaign)
    db.flush()
    return campaign


@pytest.fixture
def fake_sessions(monkeypatch: pytest.MonkeyPatch) -> list[DemoSession]:
    sessions: list[DemoSession] = []

    async def get_demo_sessions(slugs: list[str], since: datetime) -> list[DemoSession]:
        return [session for session in sessions if session.slug in slugs and session.started_at >= since]

    monkeypatch.setattr(results_module.posthog_service, "get_demo_sessions", get_demo_sessions)
    return sessions


def test_a_scanner_prefetch_is_not_a_visit() -> None:
    scanner = DemoSession("garage", "s1", LAUNCH, "Desktop", None, 0, None, None)
    reader_without_city = DemoSession("garage", "s2", LAUNCH, "Mobile", None, 0, None, None)
    assert not CampaignResultsService.is_human_session(scanner)
    assert CampaignResultsService.is_human_session(reader_without_city)


@pytest.mark.asyncio
async def test_each_prospect_lands_on_the_furthest_stage_its_mails_took_it(
    db: Session, campaign: Campaign, fake_sessions: list[DemoSession]
) -> None:
    buyer = _prospect(db, "Garage Nomade", "garage-nomade")
    interested = _prospect(db, "Les projets d'Hugo", "les-projets-d-hugo")
    refuser = _prospect(db, "AK Paysagiste", "ak-paysagiste")
    banner = _prospect(db, "TP Motorsport", "tp-motorsport")
    visitor = _prospect(db, "Jardin du Monde", "jardin-du-monde")
    silent = _prospect(db, "Jardins A. Haziri", "jardins-a-haziri")
    waiting = _prospect(db, "Newtech", "newtech")
    campaign.prospects = [buyer, interested, refuser, banner, visitor, silent, waiting]
    db.flush()
    logs = {p.id: _send(db, campaign, p, at=LAUNCH) for p in (buyer, interested, refuser, banner, visitor, silent)}
    _send(db, campaign, banner, at=LAUNCH + timedelta(days=3), step=1)
    _send(db, campaign, waiting, at=LAUNCH + timedelta(days=6), sent=False)
    for prospect, intent in ((interested, "interested"), (refuser, "not_interested")):
        db.add(
            EmailReply(
                email_log_id=logs[prospect.id].id,
                user_id=USER_ID,
                prospect_id=prospect.id,
                from_email="p@example.com",
                body_text="Ça peut être intéressant\n\nLe lun. a écrit :\n> Bonjour",
                resend_email_id=f"r-{prospect.id}",
                matched_by="token",
                is_auto_reply=False,
                received_at=LAUNCH + timedelta(hours=2),
                intent=intent,
            )
        )
    banner_site = db.query(DemoSite).filter(DemoSite.prospect_id == banner.id).one()
    db.add(
        DemoSiteLead(
            user_id=USER_ID,
            prospect_id=banner.id,
            demo_site_id=banner_site.id,
            message="Ça pourrait intéresser",
            status=LEAD_STATUS_SUBMITTED,
            created_at=LAUNCH + timedelta(days=4),
        )
    )
    db.add(
        Order(
            user_id=USER_ID, prospect_id=buyer.id, status="paid", amount_cents=50000, paid_at=LAUNCH + timedelta(days=5)
        )
    )
    db.commit()
    fake_sessions.extend(
        [
            _session("jardin-du-monde", LAUNCH - timedelta(days=1)),
            _session("jardin-du-monde", LAUNCH + timedelta(minutes=6)),
            _session("jardin-du-monde", LAUNCH + timedelta(minutes=47), seconds=None),
            _session("garage-nomade", LAUNCH + timedelta(minutes=28)),
        ]
    )

    results = await CampaignResultsService().build(db, USER_ID, campaign.id)

    assert results is not None
    states = {prospect.name: prospect.state for prospect in results.prospects}
    assert states == {
        "Garage Nomade": "sold",
        "Les projets d'Hugo": "interested",
        "AK Paysagiste": "refused",
        "TP Motorsport": "interested",
        "Jardin du Monde": "visited",
        "Jardins A. Haziri": "silent",
        "Newtech": "pending",
    }
    visitor_visits = next(p for p in results.prospects if p.name == "Jardin du Monde").visits
    assert [visit.active_seconds for visit in visitor_visits] == [40, 20]
    totals = results.totals
    assert (totals.contacted, totals.visited, totals.replied, totals.interested, totals.refused, totals.sales) == (
        6,
        2,
        3,
        3,
        1,
        1,
    )
    assert (totals.first_mails_sent, totals.follow_ups_sent, totals.planned_first_mails) == (6, 1, 1)
    banner_reply = next(reply for reply in results.replies if reply.channel == "banner")
    assert banner_reply.answered_step == 1
    email_reply = next(reply for reply in results.replies if reply.prospect_id == interested.id)
    assert email_reply.excerpt == "Ça peut être intéressant"
    assert results.next_send is not None and results.next_send.prospect_name == "Newtech"
    assert results.demo_sites.online == 7


@pytest.mark.asyncio
async def test_a_later_campaign_keeps_its_own_visits(
    db: Session, campaign: Campaign, fake_sessions: list[DemoSession]
) -> None:
    prospect = _prospect(db, "Barbershop63", "barbershop63")
    campaign.prospects = [prospect]
    reminder = Campaign(
        user_id=USER_ID, name="Dernier rappel", status=CampaignStatus.COMPLETED, channel="email", started_at=LAUNCH
    )
    db.add(reminder)
    db.flush()
    reminder.prospects = [prospect]
    _send(db, campaign, prospect, at=LAUNCH)
    _send(db, reminder, prospect, at=LAUNCH + timedelta(days=10))
    db.commit()
    fake_sessions.extend(
        [
            _session("barbershop63", LAUNCH + timedelta(hours=1)),
            _session("barbershop63", LAUNCH + timedelta(days=10, hours=1)),
        ]
    )

    first = await CampaignResultsService().build(db, USER_ID, campaign.id)
    later = await CampaignResultsService().build(db, USER_ID, reminder.id)

    assert first is not None and later is not None
    assert len(first.prospects[0].visits) == 1
    assert len(later.prospects[0].visits) == 1


@pytest.mark.asyncio
async def test_a_reply_added_by_hand_counts_and_marks_the_mail_replied(
    db: Session, campaign: Campaign, fake_sessions: list[DemoSession]
) -> None:
    prospect = _prospect(db, "AK Paysagiste", "ak-paysagiste")
    campaign.prospects = [prospect]
    _send(db, campaign, prospect, at=LAUNCH)
    follow_up_log = _send(db, campaign, prospect, at=LAUNCH + timedelta(days=5), step=1)
    db.commit()
    service = CampaignResultsService()
    assert (await service.build(db, USER_ID, campaign.id)).totals.replied == 0

    reply = service.add_manual_reply(
        db,
        USER_ID,
        campaign.id,
        CampaignManualReplyCreate(prospect_id=prospect.id, verdict="refused", message="Retirez mon site."),
    )

    assert (reply.channel, reply.answered_step, reply.is_handled) == ("manual", 1, True)
    assert follow_up_log is not None and follow_up_log.replied_at is not None
    results = await service.build(db, USER_ID, campaign.id)
    assert results is not None
    assert results.prospects[0].state == "refused"
    assert results.replies[0].excerpt == "Retirez mon site."


@pytest.mark.asyncio
async def test_benchmarks_skip_campaigns_that_never_sent(
    db: Session, campaign: Campaign, fake_sessions: list[DemoSession]
) -> None:
    prospect = _prospect(db, "Schoch Electricité", "schoch-electricite")
    campaign.prospects = [prospect]
    draft_like = Campaign(
        user_id=USER_ID, name="Pas partie", status=CampaignStatus.ACTIVE, channel="email", started_at=LAUNCH
    )
    db.add(draft_like)
    _send(db, campaign, prospect, at=LAUNCH)
    db.commit()
    fake_sessions.append(_session("schoch-electricite", LAUNCH + timedelta(minutes=25)))

    benchmarks = await CampaignResultsService().build_benchmarks(db, USER_ID)

    assert [(b.name, b.contacted, b.visited) for b in benchmarks.campaigns] == [("Vague 3 — Suisse", 1, 1)]
