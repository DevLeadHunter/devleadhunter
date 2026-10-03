"""
Campaign results: what a campaign's mails or SMS produced, prospect by prospect.

Assembles the sends of the campaign's queue (an SMS send carries its delivery report and its
cost), the human visits of each prospect's demo (PostHog sessions), the replies (captured mails,
demo banner messages, SMS replies consigned by hand, replies added by hand) and the sales into the
payload of the dashboard's « Résultats » tab, whichever the channel. Day series, rates and the
to-do list are derived from it by the dashboard, in the viewer's timezone.

The database is read in a worker thread and its pooled connection handed back before
PostHog is asked for the visits, so a slow PostHog answer never keeps a connection busy;
concurrent requests for the same results wait for one computation instead of repeating it.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from enums.demo_site_status import DemoSiteStatus
from enums.email_status import EmailStatus
from enums.order_status import WON_STATUSES
from enums.sms_status import SmsStatus
from models.campaign import Campaign
from models.demo_site import DemoSite
from models.demo_site_lead import LEAD_STATUS_SUBMITTED, DemoSiteLead
from models.email_log import EmailLog
from models.email_queue import EmailQueue
from models.email_reply import EmailReply
from models.order import Order
from models.prospect_db import ProspectDB
from models.sms_message import SmsMessage
from models.sms_reply import SmsReply
from schemas.campaign_results import (
    CampaignBenchmark,
    CampaignBenchmarksResponse,
    CampaignManualReplyCreate,
    CampaignResultsDemoSites,
    CampaignResultsNextSend,
    CampaignResultsProspect,
    CampaignResultsReply,
    CampaignResultsResponse,
    CampaignResultsSend,
    CampaignResultsTotals,
    CampaignResultsVisit,
)
from services.behavior_service import BehaviorService
from services.conversation_service import reply_display_text
from services.posthog_service import DemoSession, posthog_service
from services.reply_intent_service import NEGATIVE_INTENTS

_EXCERPT_LENGTH = 280
_INTENT_BY_VERDICT: dict[str, str] = {"interested": "interested", "refused": "not_interested", "other": "other"}
_SMS_REPLY_WITHOUT_TEXT = "Réponse notée sans son texte"


@dataclass
class _ProspectFacts:
    """Everything known about one prospect within one campaign, copied out of the database session."""

    prospect_id: int
    name: str
    category: str
    city: str | None
    is_email_undeliverable: bool
    sends: list[CampaignResultsSend] = field(default_factory=list)
    visits: list[CampaignResultsVisit] = field(default_factory=list)
    replies: list[CampaignResultsReply] = field(default_factory=list)
    sale_cents: int = 0
    sale_currency: str | None = None
    sms_cost_cents: int = 0
    window_end: datetime | None = None

    @classmethod
    def from_prospect(cls, prospect: ProspectDB, *, is_sms_campaign: bool) -> _ProspectFacts:
        """Start a prospect's facts from its row (his email's state means nothing to an SMS campaign)."""
        return cls(
            prospect_id=prospect.id,
            name=prospect.name,
            category=prospect.category,
            city=prospect.city,
            is_email_undeliverable=bool(prospect.email_undeliverable) and not is_sms_campaign,
        )

    @property
    def first_sent_at(self) -> datetime | None:
        """When the first message actually left, None while it has not."""
        return next((send.at for send in self.sends if send.step == 0 and send.status == "sent"), None)


@dataclass
class _CampaignReading:
    """One campaign as read from the database, with the facts of each of its prospects."""

    campaign_id: int
    name: str
    channel: str
    status: str
    started_at: datetime | None
    facts_by_prospect: dict[int, _ProspectFacts]


@dataclass
class _DatabaseReading:
    """What the database knows about some campaigns, read in one go before PostHog is asked for the visits."""

    campaigns: list[_CampaignReading]
    prospect_ids_by_slug: dict[str, set[int]]


class CampaignResultsService:
    """Builds a campaign's results and the benchmarks of the user's other campaigns."""

    _RESULTS_TTL_SECONDS = 60
    _BENCHMARKS_TTL_SECONDS = 600

    def __init__(self) -> None:
        self._results_cache: dict[tuple[int, int], tuple[float, CampaignResultsResponse]] = {}
        self._benchmarks_cache: dict[int, tuple[float, CampaignBenchmarksResponse]] = {}
        self._results_locks: dict[tuple[int, int], asyncio.Lock] = {}
        self._benchmarks_locks: dict[int, asyncio.Lock] = {}

    async def build(self, db: Session, user_id: int, campaign_id: int) -> CampaignResultsResponse | None:
        """
        Return the results of one of the user's campaigns, cached for a minute.

        Args:
            db: Active database session.
            user_id: Owner of the campaign.
            campaign_id: The campaign to read.

        Returns:
            The results, or None when the campaign does not exist for this user.
        """
        cache_key = (user_id, campaign_id)
        cached = self._fresh_results(cache_key)
        if cached is not None:
            return cached
        await asyncio.to_thread(self._release_connection, db)
        async with self._results_locks.setdefault(cache_key, asyncio.Lock()):
            cached = self._fresh_results(cache_key)
            if cached is not None:
                return cached
            loaded = await asyncio.to_thread(self._read_results, db, user_id, campaign_id)
            if loaded is None:
                return None
            reading, demo_sites = loaded
            await self._attach_visits(reading)
            response = self._assemble(reading.campaigns[0], demo_sites)
            self._results_cache[cache_key] = (time.monotonic() + self._RESULTS_TTL_SECONDS, response)
            return response

    async def build_benchmarks(self, db: Session, user_id: int) -> CampaignBenchmarksResponse:
        """
        Return the stage counts of every campaign of the user, email or SMS, that sent a first message, cached ten minutes.

        Args:
            db: Active database session.
            user_id: Owner of the campaigns.

        Returns:
            One benchmark per campaign, most recently started first.
        """
        cached = self._fresh_benchmarks(user_id)
        if cached is not None:
            return cached
        await asyncio.to_thread(self._release_connection, db)
        async with self._benchmarks_locks.setdefault(user_id, asyncio.Lock()):
            cached = self._fresh_benchmarks(user_id)
            if cached is not None:
                return cached
            reading = await asyncio.to_thread(self._read_benchmarks, db, user_id)
            await self._attach_visits(reading)
            benchmarks: list[CampaignBenchmark] = []
            for campaign in reading.campaigns:
                totals = self._totals(list(campaign.facts_by_prospect.values()), channel=campaign.channel)
                if totals.contacted == 0:
                    continue
                benchmarks.append(
                    CampaignBenchmark(
                        campaign_id=campaign.campaign_id,
                        name=campaign.name,
                        channel=campaign.channel,
                        status=campaign.status,
                        started_at=campaign.started_at,
                        contacted=totals.contacted,
                        visited=totals.visited,
                        replied=totals.replied,
                        interested=totals.interested,
                    )
                )
            benchmarks.sort(key=lambda benchmark: benchmark.started_at or datetime.min, reverse=True)
            response = CampaignBenchmarksResponse(campaigns=benchmarks)
            self._benchmarks_cache[user_id] = (time.monotonic() + self._BENCHMARKS_TTL_SECONDS, response)
            return response

    def add_manual_reply(
        self, db: Session, user_id: int, campaign_id: int, payload: CampaignManualReplyCreate
    ) -> CampaignResultsReply:
        """
        Record a reply that reached the user outside the app, attached to the last message of the campaign it answers.

        Like a captured reply, it marks that mail as replied, which stops the prospect's pending follow-ups. On
        an SMS campaign the reply is consigned as an SMS reply of the number the campaign texted, which holds
        the prospect's pending sends back the same way.

        Args:
            db: Active database session.
            user_id: Owner of the campaign.
            campaign_id: The campaign the reply belongs to.
            payload: Prospect, verdict, date and words of the reply.

        Returns:
            The recorded reply, as the results tab lists it.

        Raises:
            HTTPException: 404 when the campaign or the prospect is not the user's, 422 when no message was sent to them.
        """
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user_id).first()
        if campaign is None or all(prospect.id != payload.prospect_id for prospect in campaign.prospects):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found in this campaign")
        if campaign.channel == "sms":
            return self._add_manual_sms_reply(db, user_id, campaign_id, payload)
        email_log = (
            db.query(EmailLog)
            .filter(
                EmailLog.user_id == user_id,
                EmailLog.campaign_id == campaign_id,
                EmailLog.prospect_id == payload.prospect_id,
                EmailLog.sent_at.isnot(None),
            )
            .order_by(EmailLog.sent_at.desc())
            .first()
        )
        if email_log is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Aucun mail de cette campagne n'est encore parti vers ce prospect.",
            )
        now = datetime.now(UTC).replace(tzinfo=None)
        received_at = self._utc_naive(payload.received_at) or now
        reply = EmailReply(
            email_log_id=email_log.id,
            user_id=user_id,
            prospect_id=payload.prospect_id,
            from_email=email_log.recipient_email,
            subject=None,
            body_text=payload.message.strip() or None,
            resend_email_id=f"manual-{uuid.uuid4().hex}",
            matched_by="manual",
            is_auto_reply=False,
            received_at=received_at,
            handled_at=now,
            intent=_INTENT_BY_VERDICT[payload.verdict],
        )
        db.add(reply)
        if email_log.replied_at is None:
            email_log.replied_at = received_at
        email_log.status = EmailStatus.REPLIED.value
        db.commit()
        self._results_cache.pop((user_id, campaign_id), None)
        self._benchmarks_cache.pop(user_id, None)
        return CampaignResultsReply(
            id=f"email:{reply.id}",
            prospect_id=payload.prospect_id,
            received_at=received_at,
            verdict=payload.verdict,
            channel="manual",
            answered_step=self._step_of_log(db, email_log.id),
            excerpt=self._excerpt(payload.message),
            is_handled=True,
        )

    def _add_manual_sms_reply(
        self, db: Session, user_id: int, campaign_id: int, payload: CampaignManualReplyCreate
    ) -> CampaignResultsReply:
        """
        Consign the reply of an SMS campaign's prospect on the number its last SMS went to.

        Args:
            db: Active database session.
            user_id: Owner of the campaign.
            campaign_id: The SMS campaign the reply belongs to.
            payload: Prospect, verdict, date and words of the reply.

        Returns:
            The recorded reply, as the results tab lists it.

        Raises:
            HTTPException: 422 when no SMS of the campaign reached the prospect yet, or the reply is refused.
        """
        from services.sms_service import sms_service

        last_send = db.execute(
            select(EmailQueue, SmsMessage)
            .join(SmsMessage, SmsMessage.id == EmailQueue.sms_message_id)
            .where(
                EmailQueue.user_id == user_id,
                EmailQueue.campaign_id == campaign_id,
                EmailQueue.prospect_id == payload.prospect_id,
                EmailQueue.status == "sent",
            )
            .order_by(SmsMessage.created_at.desc())
            .limit(1)
        ).first()
        if last_send is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Aucun SMS de cette campagne n'est encore parti vers ce prospect.",
            )
        queue_item, message = last_send
        try:
            reply = sms_service.record_reply(
                db,
                user_id=user_id,
                prospect_id=payload.prospect_id,
                from_raw=message.to_e164,
                body=payload.message.strip() or _SMS_REPLY_WITHOUT_TEXT,
                received_at=self._utc_naive(payload.received_at),
                intent=_INTENT_BY_VERDICT[payload.verdict],
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        self._results_cache.pop((user_id, campaign_id), None)
        self._benchmarks_cache.pop(user_id, None)
        return CampaignResultsReply(
            id=f"sms:{reply.id}",
            prospect_id=payload.prospect_id,
            received_at=reply.received_at,
            verdict=payload.verdict,
            channel="sms",
            answered_step=0 if queue_item.queue_type == "initial" else max(1, queue_item.follow_up_index),
            excerpt=self._excerpt(payload.message),
            is_handled=True,
        )

    @staticmethod
    def _utc_naive(moment: datetime | None) -> datetime | None:
        """A moment as the database stores it: UTC without a timezone (None stays None)."""
        if moment is None or moment.tzinfo is None:
            return moment
        return moment.astimezone(UTC).replace(tzinfo=None)

    @staticmethod
    def is_human_session(session: DemoSession) -> bool:
        """
        Tell a person's visit from a mail scanner's prefetch.

        Link scanners load the page once, from a data centre: a desktop or unknown device, no
        city, and nothing but page views. A person scrolls, reads a section or stays long
        enough to send a time event, wherever they are.

        Args:
            session: The session to judge.

        Returns:
            False only for a session that looks like a scanner.
        """
        looks_like_datacenter = session.city is None and session.device_type in (None, "Desktop")
        return not (looks_like_datacenter and session.interaction_count == 0)

    @staticmethod
    def active_seconds(session: DemoSession) -> int:
        """Visible time of a session: the time sent on leaving, else the time at which it qualified as engaged."""
        seconds = session.time_on_page_seconds if session.time_on_page_seconds is not None else session.engaged_seconds
        return max(0, round(seconds or 0))

    @staticmethod
    def reply_verdict(intent: str | None) -> str:
        """Map a reply's classified intent onto the verdict the results show."""
        if intent == "interested":
            return "interested"
        if intent in NEGATIVE_INTENTS:
            return "refused"
        return "other"

    @staticmethod
    def prospect_state(facts: _ProspectFacts) -> str:
        """The furthest stage a prospect reached: sale, then reply verdicts, visit, silence, or not sent yet."""
        verdicts = {reply.verdict for reply in facts.replies}
        if facts.sale_cents > 0:
            return "sold"
        if "interested" in verdicts:
            return "interested"
        if "refused" in verdicts:
            return "refused"
        if verdicts:
            return "replied"
        if facts.visits:
            return "visited"
        if facts.first_sent_at is not None:
            return "silent"
        if any(send.step == 0 and send.status == "planned" for send in facts.sends):
            return "pending"
        return "not_sent"

    def _fresh_results(self, cache_key: tuple[int, int]) -> CampaignResultsResponse | None:
        """The cached results of a campaign while they are less than a minute old."""
        cached = self._results_cache.get(cache_key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        return None

    def _fresh_benchmarks(self, user_id: int) -> CampaignBenchmarksResponse | None:
        """The cached benchmarks of a user while they are less than ten minutes old."""
        cached = self._benchmarks_cache.get(user_id)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        return None

    @staticmethod
    def _release_connection(db: Session) -> None:
        """
        End the session's read transaction so its pooled connection goes back before a long wait.

        A commit rather than a rollback: these reads leave nothing pending, and a commit never
        discards what a caller may have written on the same session.
        """
        db.commit()

    def _read_results(
        self, db: Session, user_id: int, campaign_id: int
    ) -> tuple[_DatabaseReading, CampaignResultsDemoSites] | None:
        """Read one of the user's campaigns and its demo sites, then hand the connection back."""
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user_id).first()
        if campaign is None:
            return None
        reading = self._read_campaigns(db, user_id, [campaign])
        demo_sites = self._demo_sites(db, user_id, list(reading.campaigns[0].facts_by_prospect))
        self._release_connection(db)
        return reading, demo_sites

    def _read_benchmarks(self, db: Session, user_id: int) -> _DatabaseReading:
        """Read every campaign the user launched, email or SMS, then hand the connection back."""
        campaigns = db.query(Campaign).filter(Campaign.user_id == user_id, Campaign.started_at.isnot(None)).all()
        reading = self._read_campaigns(db, user_id, campaigns)
        self._release_connection(db)
        return reading

    def _read_campaigns(self, db: Session, user_id: int, campaigns: list[Campaign]) -> _DatabaseReading:
        """Read the facts of the campaigns' prospects and the demo slugs their visits are looked up by."""
        facts_by_campaign = self._collect_facts(db, user_id, campaigns)
        prospect_ids = sorted({prospect_id for facts in facts_by_campaign.values() for prospect_id in facts})
        slugs_by_prospect = BehaviorService.slugs_by_prospect(db, user_id, prospect_ids) if prospect_ids else {}
        prospect_ids_by_slug: dict[str, set[int]] = defaultdict(set)
        for prospect_id, slugs in slugs_by_prospect.items():
            for slug in slugs:
                prospect_ids_by_slug[slug].add(prospect_id)
        return _DatabaseReading(
            campaigns=[
                _CampaignReading(
                    campaign_id=campaign.id,
                    name=campaign.name,
                    channel=campaign.channel,
                    status=str(getattr(campaign.status, "value", campaign.status)),
                    started_at=campaign.started_at,
                    facts_by_prospect=facts_by_campaign[campaign.id],
                )
                for campaign in campaigns
            ],
            prospect_ids_by_slug=prospect_ids_by_slug,
        )

    def _collect_facts(
        self, db: Session, user_id: int, campaigns: list[Campaign]
    ) -> dict[int, dict[int, _ProspectFacts]]:
        """Load sends, replies, banner messages, SMS replies and sales of each campaign's prospects (visits come later)."""
        facts_by_campaign: dict[int, dict[int, _ProspectFacts]] = {
            campaign.id: {
                prospect.id: _ProspectFacts.from_prospect(prospect, is_sms_campaign=campaign.channel == "sms")
                for prospect in campaign.prospects
            }
            for campaign in campaigns
        }
        campaign_ids = list(facts_by_campaign)
        if not campaign_ids:
            return facts_by_campaign
        step_by_log_id = self._attach_sends(db, user_id, campaign_ids, facts_by_campaign)
        self._attach_email_replies(db, user_id, campaign_ids, step_by_log_id, facts_by_campaign)
        prospect_ids = sorted({pid for facts in facts_by_campaign.values() for pid in facts})
        self._attach_window_ends(db, user_id, prospect_ids, facts_by_campaign)
        self._attach_banner_messages(db, user_id, prospect_ids, facts_by_campaign)
        self._attach_sms_replies(db, user_id, prospect_ids, facts_by_campaign)
        self._attach_sales(db, user_id, prospect_ids, facts_by_campaign)
        return facts_by_campaign

    @staticmethod
    def _attach_sends(
        db: Session, user_id: int, campaign_ids: list[int], facts_by_campaign: dict[int, dict[int, _ProspectFacts]]
    ) -> dict[int, int]:
        """Turn the campaigns' queue rows into sends, and return the step of each dispatched mail by email log id.

        A mail's send carries its bounce; an SMS's send its delivery failure and its cost.
        """
        rows = db.execute(
            select(EmailQueue, EmailLog, SmsMessage)
            .outerjoin(EmailLog, EmailLog.id == EmailQueue.email_log_id)
            .outerjoin(SmsMessage, SmsMessage.id == EmailQueue.sms_message_id)
            .where(EmailQueue.user_id == user_id, EmailQueue.campaign_id.in_(campaign_ids))
            .order_by(EmailQueue.scheduled_at)
        ).all()
        step_by_log_id: dict[int, int] = {}
        status_by_queue_status = {"sent": "sent", "pending": "planned", "sending": "planned", "failed": "failed"}
        for queue_item, email_log, sms_message in rows:
            facts = facts_by_campaign.get(queue_item.campaign_id, {}).get(queue_item.prospect_id)
            if facts is None:
                continue
            step = 0 if queue_item.queue_type == "initial" else max(1, queue_item.follow_up_index)
            send_status = status_by_queue_status.get(queue_item.status, "skipped")
            sent_at: datetime | None = None
            is_bounced: bool = False
            if email_log is not None:
                sent_at = email_log.sent_at
                is_bounced = email_log.bounced_at is not None or email_log.status == EmailStatus.BOUNCED.value
            elif sms_message is not None:
                sent_at = sms_message.created_at
                is_bounced = sms_message.status == SmsStatus.FAILED.value
                if send_status == "sent":
                    facts.sms_cost_cents += sms_message.price_cents or 0
            facts.sends.append(
                CampaignResultsSend(
                    step=step,
                    status=send_status,
                    at=sent_at if send_status == "sent" and sent_at else queue_item.scheduled_at,
                    is_bounced=is_bounced,
                )
            )
            if email_log is not None:
                step_by_log_id[email_log.id] = step
        return step_by_log_id

    def _attach_email_replies(
        self,
        db: Session,
        user_id: int,
        campaign_ids: list[int],
        step_by_log_id: dict[int, int],
        facts_by_campaign: dict[int, dict[int, _ProspectFacts]],
    ) -> None:
        """Attach the human replies to the campaigns' mails, captured or added by hand."""
        rows = db.execute(
            select(EmailReply, EmailLog.campaign_id)
            .join(EmailLog, EmailLog.id == EmailReply.email_log_id)
            .where(
                EmailReply.user_id == user_id,
                EmailReply.is_auto_reply.is_(False),
                EmailLog.campaign_id.in_(campaign_ids),
            )
        ).all()
        for reply, campaign_id in rows:
            facts = facts_by_campaign.get(campaign_id, {}).get(reply.prospect_id or -1)
            if facts is None:
                continue
            facts.replies.append(
                CampaignResultsReply(
                    id=f"email:{reply.id}",
                    prospect_id=facts.prospect_id,
                    received_at=reply.received_at or reply.created_at,
                    verdict=self.reply_verdict(reply.intent),
                    channel="manual" if reply.matched_by == "manual" else "email",
                    answered_step=step_by_log_id.get(reply.email_log_id, 0),
                    excerpt=self._excerpt(reply_display_text(reply)),
                    is_handled=reply.handled_at is not None,
                )
            )

    @staticmethod
    def _attach_window_ends(
        db: Session, user_id: int, prospect_ids: list[int], facts_by_campaign: dict[int, dict[int, _ProspectFacts]]
    ) -> None:
        """Close each prospect's window at the first message of a later campaign, so its visits are not counted twice."""
        if not prospect_ids:
            return
        rows = db.execute(
            select(EmailQueue.campaign_id, EmailQueue.prospect_id, EmailLog.sent_at, SmsMessage.created_at)
            .outerjoin(EmailLog, EmailLog.id == EmailQueue.email_log_id)
            .outerjoin(SmsMessage, SmsMessage.id == EmailQueue.sms_message_id)
            .where(
                EmailQueue.user_id == user_id,
                EmailQueue.prospect_id.in_(prospect_ids),
                EmailQueue.queue_type == "initial",
                or_(EmailLog.sent_at.isnot(None), and_(SmsMessage.id.isnot(None), EmailQueue.status == "sent")),
            )
        ).all()
        first_messages_by_prospect: dict[int, list[tuple[int, datetime]]] = defaultdict(list)
        for campaign_id, prospect_id, mail_sent_at, sms_sent_at in rows:
            first_messages_by_prospect[prospect_id].append((campaign_id, mail_sent_at or sms_sent_at))
        for campaign_id, facts_by_prospect in facts_by_campaign.items():
            for prospect_id, facts in facts_by_prospect.items():
                started = facts.first_sent_at
                if started is None:
                    continue
                later = [
                    sent_at
                    for other_id, sent_at in first_messages_by_prospect.get(prospect_id, [])
                    if other_id != campaign_id and sent_at > started
                ]
                facts.window_end = min(later) if later else None

    @staticmethod
    def _attach_banner_messages(
        db: Session, user_id: int, prospect_ids: list[int], facts_by_campaign: dict[int, dict[int, _ProspectFacts]]
    ) -> None:
        """Attach the messages prospects sent from their demo's banner during each campaign's window."""
        if not prospect_ids:
            return
        leads = (
            db.query(DemoSiteLead)
            .filter(
                DemoSiteLead.user_id == user_id,
                DemoSiteLead.prospect_id.in_(prospect_ids),
                DemoSiteLead.status == LEAD_STATUS_SUBMITTED,
            )
            .all()
        )
        for facts_by_prospect in facts_by_campaign.values():
            for lead in leads:
                facts = facts_by_prospect.get(lead.prospect_id or -1)
                if facts is None or facts.first_sent_at is None or lead.created_at < facts.first_sent_at:
                    continue
                if facts.window_end is not None and lead.created_at >= facts.window_end:
                    continue
                facts.replies.append(
                    CampaignResultsReply(
                        id=f"banner:{lead.id}",
                        prospect_id=facts.prospect_id,
                        received_at=lead.created_at,
                        verdict="interested",
                        channel="banner",
                        answered_step=CampaignResultsService._answered_step(facts, lead.created_at),
                        excerpt=CampaignResultsService._excerpt(lead.message or ""),
                        is_handled=lead.handled_at is not None,
                    )
                )

    @staticmethod
    def _attach_sms_replies(
        db: Session, user_id: int, prospect_ids: list[int], facts_by_campaign: dict[int, dict[int, _ProspectFacts]]
    ) -> None:
        """Attach the SMS replies consigned for the prospects during each campaign's window (the sender is one-way)."""
        if not prospect_ids:
            return
        replies = db.query(SmsReply).filter(SmsReply.user_id == user_id, SmsReply.prospect_id.in_(prospect_ids)).all()
        for facts_by_prospect in facts_by_campaign.values():
            for reply in replies:
                facts = facts_by_prospect.get(reply.prospect_id or -1)
                if facts is None or facts.first_sent_at is None or reply.received_at < facts.first_sent_at:
                    continue
                if facts.window_end is not None and reply.received_at >= facts.window_end:
                    continue
                facts.replies.append(
                    CampaignResultsReply(
                        id=f"sms:{reply.id}",
                        prospect_id=facts.prospect_id,
                        received_at=reply.received_at,
                        verdict=CampaignResultsService.reply_verdict(reply.intent),
                        channel="sms",
                        answered_step=CampaignResultsService._answered_step(facts, reply.received_at),
                        excerpt=CampaignResultsService._excerpt(reply.body),
                        is_handled=True,
                    )
                )

    @staticmethod
    def _answered_step(facts: _ProspectFacts, answered_at: datetime) -> int:
        """The step of the last message that had left when the prospect answered (0 for the first one)."""
        sent_steps = [send.step for send in facts.sends if send.status == "sent" and send.at <= answered_at]
        return max(sent_steps, default=0)

    @staticmethod
    def _attach_sales(
        db: Session, user_id: int, prospect_ids: list[int], facts_by_campaign: dict[int, dict[int, _ProspectFacts]]
    ) -> None:
        """Attach the paid orders of each prospect placed after the campaign's first mail."""
        if not prospect_ids:
            return
        orders = (
            db.query(Order)
            .filter(
                Order.user_id == user_id,
                Order.prospect_id.in_(prospect_ids),
                Order.status.in_(WON_STATUSES),
                Order.deleted_at.is_(None),
            )
            .all()
        )
        for facts_by_prospect in facts_by_campaign.values():
            for order in orders:
                facts = facts_by_prospect.get(order.prospect_id or -1)
                paid_at = order.paid_at or order.created_at
                if facts is None or facts.first_sent_at is None or paid_at < facts.first_sent_at:
                    continue
                facts.sale_cents += order.amount_cents
                facts.sale_currency = facts.sale_currency or order.currency

    async def _attach_visits(self, reading: _DatabaseReading) -> None:
        """Attach each prospect's human visits within its campaign window, from one PostHog query."""
        all_facts = [facts for campaign in reading.campaigns for facts in campaign.facts_by_prospect.values()]
        started = [facts.first_sent_at for facts in all_facts if facts.first_sent_at is not None]
        if not started:
            return
        prospect_ids_by_slug = reading.prospect_ids_by_slug
        sessions = await posthog_service.get_demo_sessions(list(prospect_ids_by_slug), min(started))
        for facts in all_facts:
            first_sent_at = facts.first_sent_at
            if first_sent_at is None:
                continue
            for session in sessions:
                if facts.prospect_id not in prospect_ids_by_slug.get(session.slug, set()):
                    continue
                if session.started_at < first_sent_at or not self.is_human_session(session):
                    continue
                if facts.window_end is not None and session.started_at >= facts.window_end:
                    continue
                facts.visits.append(
                    CampaignResultsVisit(
                        started_at=session.started_at,
                        active_seconds=self.active_seconds(session),
                        device_type=session.device_type,
                    )
                )

    def _assemble(self, campaign: _CampaignReading, demo_sites: CampaignResultsDemoSites) -> CampaignResultsResponse:
        """Shape one campaign's facts into the results payload."""
        all_facts = list(campaign.facts_by_prospect.values())
        planned = sorted(
            ((send.at, facts.name) for facts in all_facts for send in facts.sends if send.status == "planned"),
            key=lambda planned_send: planned_send[0],
        )
        return CampaignResultsResponse(
            campaign_id=campaign.campaign_id,
            channel=campaign.channel,
            generated_at=datetime.now(UTC).replace(tzinfo=None),
            is_visit_tracking_available=posthog_service.is_configured,
            totals=self._totals(all_facts, channel=campaign.channel),
            next_send=CampaignResultsNextSend(at=planned[0][0], prospect_name=planned[0][1]) if planned else None,
            last_planned_send_at=planned[-1][0] if planned else None,
            demo_sites=demo_sites,
            prospects=[
                CampaignResultsProspect(
                    id=facts.prospect_id,
                    name=facts.name,
                    category=facts.category,
                    city=facts.city,
                    state=self.prospect_state(facts),
                    is_email_undeliverable=facts.is_email_undeliverable,
                    sends=sorted(facts.sends, key=lambda send: (send.step, send.at)),
                    visits=sorted(facts.visits, key=lambda visit: visit.started_at),
                )
                for facts in all_facts
            ],
            replies=sorted(
                (reply for facts in all_facts for reply in facts.replies), key=lambda reply: reply.received_at
            ),
        )

    def _totals(self, all_facts: list[_ProspectFacts], *, channel: str) -> CampaignResultsTotals:
        """Count the prospects at each stage, the message volumes and, for an SMS campaign, what its SMS cost."""
        states = [self.prospect_state(facts) for facts in all_facts]
        sends = [send for facts in all_facts for send in facts.sends]
        return CampaignResultsTotals(
            prospects=len(all_facts),
            contacted=sum(1 for facts in all_facts if facts.first_sent_at is not None),
            visited=sum(1 for facts in all_facts if facts.visits),
            replied=sum(1 for facts in all_facts if facts.replies),
            interested=sum(1 for state in states if state in ("sold", "interested")),
            refused=sum(1 for state in states if state == "refused"),
            sales=sum(1 for facts in all_facts if facts.sale_cents > 0),
            revenue_cents=sum(facts.sale_cents for facts in all_facts),
            currency=next((facts.sale_currency for facts in all_facts if facts.sale_currency), None),
            first_mails_sent=sum(1 for send in sends if send.step == 0 and send.status == "sent"),
            follow_ups_sent=sum(1 for send in sends if send.step > 0 and send.status == "sent"),
            bounced=sum(1 for send in sends if send.is_bounced),
            failed=sum(1 for send in sends if send.status == "failed"),
            planned_first_mails=sum(1 for send in sends if send.step == 0 and send.status == "planned"),
            planned_follow_ups=sum(1 for send in sends if send.step > 0 and send.status == "planned"),
            sms_cost_cents=sum(facts.sms_cost_cents for facts in all_facts) if channel == "sms" else None,
        )

    @staticmethod
    def _demo_sites(db: Session, user_id: int, prospect_ids: list[int]) -> CampaignResultsDemoSites:
        """Count the campaign's demo sites still online and the expiry range of those whose countdown started."""
        if not prospect_ids:
            return CampaignResultsDemoSites(online=0)
        online_sites = (
            db.query(DemoSite.expires_at, DemoSite.demo_link_sent_at)
            .filter(
                DemoSite.user_id == user_id,
                DemoSite.prospect_id.in_(prospect_ids),
                DemoSite.status == DemoSiteStatus.ACTIVE.value,
            )
            .all()
        )
        expiries = [expires_at for expires_at, demo_link_sent_at in online_sites if demo_link_sent_at is not None]
        return CampaignResultsDemoSites(
            online=len(online_sites),
            first_expiry_at=min(expiries) if expiries else None,
            last_expiry_at=max(expiries) if expiries else None,
        )

    @staticmethod
    def _step_of_log(db: Session, email_log_id: int) -> int:
        """The sequence step of a dispatched mail (0 for the first mail)."""
        queue_item = db.query(EmailQueue).filter(EmailQueue.email_log_id == email_log_id).first()
        if queue_item is None or queue_item.queue_type == "initial":
            return 0
        return max(1, queue_item.follow_up_index)

    @staticmethod
    def _excerpt(text: str) -> str:
        """The reply's words on one line, cut at a readable length."""
        single_line = " ".join((text or "").split())
        if len(single_line) <= _EXCERPT_LENGTH:
            return single_line
        return single_line[: _EXCERPT_LENGTH - 1].rstrip() + "…"


campaign_results_service = CampaignResultsService()
