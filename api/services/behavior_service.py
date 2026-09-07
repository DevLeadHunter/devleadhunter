"""
Behaviour service — unifies demo events (PostHog) and email engagement (EmailLog)
for a prospect.

Resolves a prospect's demo slugs, reads their behavioural events + email
engagement, computes a combined lead score + timeline, and (optionally) an AI
summary / personalised follow-up. Read paths degrade gracefully when PostHog /
Groq are not configured.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.demo_site_lead import DemoSiteLead
from models.email_log import EmailLog
from models.email_reply import EmailReply
from models.prospect_db import ProspectDB
from services import lead_scoring
from services.llm_service import llm_service
from services.posthog_service import posthog_service
from services.reply_intent_service import NEGATIVE_INTENTS

# Human labels for the timeline.
_EVENT_LABELS: dict[str, str] = {
    "$pageview": "Visite de la démo",
    "demo_section_view": "A consulté une section",
    "demo_cta_click": "Clic sur un bouton d'action",
    "demo_phone_click": "Clic sur le téléphone",
    "demo_contact_click": "Clic sur le contact",
    "demo_outbound_click": "Clic vers un lien externe",
    "demo_scroll_depth": "A fait défiler la page",
    "demo_time_on_page": "Temps passé sur la page",
    "demo_engaged": "Visite qualifiée (engagé)",
    "demo_cta_banner_open": "A ouvert le formulaire de contact",
    "demo_cta_banner_auto_open": "Le formulaire s'est ouvert en fin de page",
    "demo_cta_banner_field_focus": "A commencé à écrire un message",
    "demo_cta_banner_submitted": "A envoyé un message (intéressé)",
    "demo_cta_banner_collapse": "A réduit le formulaire de contact",
    "demo_cta_banner_abandoned": "A quitté avec le formulaire ouvert",
    "demo_video_play": "Lecture de la vidéo de prospection",
    "demo_video_resume": "Reprise de la vidéo",
    "demo_video_pause": "Vidéo mise en pause",
    "demo_video_replay": "A revu la vidéo",
    "demo_video_progress": "Vidéo regardée en partie",
    "demo_video_complete": "Vidéo regardée en entier",
    "demo_video_watch_time": "Temps de visionnage de la vidéo",
    "demo_video_seek": "A avancé / reculé dans la vidéo",
    "demo_video_fullscreen": "Vidéo en plein écran",
    "demo_video_mute": "A coupé / remis le son",
    "demo_video_cta_click": "Clic « Découvrir le site » depuis la vidéo",
    "email_sent": "Email envoyé",
    "email_opened": "Email ouvert",
    "email_clicked": "Lien de l'email cliqué",
    "email_replied": "A répondu à l'email",
    "demo_lead": "S'est déclaré intéressé depuis sa démo",
}


class BehaviorService:
    """Aggregates demo behaviour + email engagement for a prospect."""

    # ------------------------------------------------------------------ #
    # Demo slugs / events
    # ------------------------------------------------------------------ #

    def _slugs_for_prospect(self, db: Session, user_id: int, prospect_id: int) -> list[str]:
        """Return the demo slugs linked to a prospect (owned by the user)."""
        sites = (
            db.query(DemoSite)
            .filter(
                DemoSite.prospect_id == prospect_id,
                DemoSite.user_id == user_id,
                DemoSite.status != DemoSiteStatus.DELETED.value,
            )
            .all()
        )
        return [site.slug for site in sites if site.slug]

    async def _events_for_prospect(self, db: Session, user_id: int, prospect_id: int) -> list[dict[str, Any]]:
        """Fetch and merge behavioural events across all of a prospect's demos."""
        slugs = self._slugs_for_prospect(db, user_id, prospect_id)
        events: list[dict[str, Any]] = []
        for slug in slugs:
            events.extend(await posthog_service.get_events_for_slug(slug))
        events.sort(key=lambda e: str(e.get("timestamp", "")), reverse=True)
        return events

    # ------------------------------------------------------------------ #
    # Email engagement (EmailLog)
    # ------------------------------------------------------------------ #

    def _email_engagement(self, db: Session, user_id: int, prospect_id: int) -> dict[str, Any]:
        """Return email engagement counts + timeline entries for a prospect."""
        logs = db.query(EmailLog).filter(EmailLog.user_id == user_id, EmailLog.prospect_id == prospect_id).all()
        sent = opened = clicked = replied = reopens = 0
        timeline: list[dict[str, Any]] = []
        for log in logs:
            if log.sent_at:
                sent += 1
                timeline.append(self._email_entry("email_sent", log.sent_at))
            if log.opened_at:
                opened += 1
                open_count = log.open_count or 1
                reopens += max(open_count - 1, 0)
                timeline.append(self._email_entry("email_opened", log.opened_at, count=open_count))
            if log.clicked_at:
                clicked += 1
                timeline.append(self._email_entry("email_clicked", log.clicked_at))
            if log.replied_at:
                replied += 1
                timeline.append(self._email_entry("email_replied", log.replied_at))
        # Reply-level intent: a « pas intéressé » must cool the lead, not heat it.
        intents = (
            db.execute(
                select(EmailReply.intent).where(
                    EmailReply.user_id == user_id,
                    EmailReply.prospect_id == prospect_id,
                    EmailReply.is_auto_reply.is_(False),
                )
            )
            .scalars()
            .all()
        )
        negative = sum(1 for intent in intents if intent in NEGATIVE_INTENTS)
        if intents:
            # Unclassified (NULL) counts as neutral-positive: benefit of the doubt.
            replied = len(intents) - negative
        return {
            "sent": sent,
            "opened": opened,
            "clicked": clicked,
            "replied": replied,
            "negative_replies": negative,
            "reopens": reopens,
            "timeline": timeline,
        }

    def _email_engagement_bulk(self, db: Session, user_id: int, prospect_ids: list[int]) -> dict[int, dict[str, int]]:
        """Return email engagement counts per prospect (one grouped query)."""
        if not prospect_ids:
            return {}
        rows = db.execute(
            select(
                EmailLog.prospect_id,
                func.count(EmailLog.sent_at),
                func.count(EmailLog.opened_at),
                func.count(EmailLog.clicked_at),
                func.count(EmailLog.replied_at),
                func.coalesce(func.sum(EmailLog.open_count), 0),
            )
            .where(EmailLog.user_id == user_id, EmailLog.prospect_id.in_(prospect_ids))
            .group_by(EmailLog.prospect_id)
        ).all()
        # Reply-level intent breakdown (one grouped query): negatives cool the lead.
        reply_rows = db.execute(
            select(
                EmailReply.prospect_id,
                func.sum(case((EmailReply.intent.in_(NEGATIVE_INTENTS), 1), else_=0)),
                func.count(EmailReply.id),
            )
            .where(
                EmailReply.user_id == user_id,
                EmailReply.prospect_id.in_(prospect_ids),
                EmailReply.is_auto_reply.is_(False),
            )
            .group_by(EmailReply.prospect_id)
        ).all()
        intent_by_pid: dict[int, tuple[int, int]] = {
            int(pid): (int(negative or 0), int(total or 0)) for pid, negative, total in reply_rows if pid is not None
        }
        result: dict[int, dict[str, int]] = {}
        for pid, sent, opened, clicked, replied, total_opens in rows:
            if pid is None:
                continue
            opened_count = int(opened or 0)
            # sum(open_count) - count(opened_at) = reopens (machine-only rows contribute 0 to both).
            reopens = max(int(total_opens or 0) - opened_count, 0)
            negative, total_replies = intent_by_pid.get(int(pid), (0, 0))
            result[int(pid)] = {
                "sent": int(sent or 0),
                "opened": opened_count,
                "clicked": int(clicked or 0),
                "replied": (total_replies - negative) if total_replies else int(replied or 0),
                "negative_replies": negative,
                "reopens": reopens,
            }
        return result

    # ------------------------------------------------------------------ #
    # Demo leads (« Ce site vous plaît ? » banner)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _demo_leads(db: Session, user_id: int, prospect_id: int) -> list[DemoSiteLead]:
        """Return the prospect's banner leads, newest first."""
        return (
            db.query(DemoSiteLead)
            .filter(DemoSiteLead.user_id == user_id, DemoSiteLead.prospect_id == prospect_id)
            .order_by(DemoSiteLead.created_at.desc())
            .all()
        )

    @staticmethod
    def _demo_leads_count_bulk(db: Session, user_id: int, prospect_ids: list[int]) -> dict[int, int]:
        """Return the banner-lead count per prospect (one grouped query)."""
        if not prospect_ids:
            return {}
        rows = db.execute(
            select(DemoSiteLead.prospect_id, func.count(DemoSiteLead.id))
            .where(DemoSiteLead.user_id == user_id, DemoSiteLead.prospect_id.in_(prospect_ids))
            .group_by(DemoSiteLead.prospect_id)
        ).all()
        return {int(pid): int(count or 0) for pid, count in rows if pid is not None}

    @staticmethod
    def _email_entry(event_type: str, when: Any, count: int = 1) -> dict[str, Any]:
        """Build a timeline entry for an email event (open count folds into the open label)."""
        ts = when.isoformat() if hasattr(when, "isoformat") else str(when)
        label = _EVENT_LABELS.get(event_type, event_type)
        if event_type == "email_opened" and count > 1:
            label = f"{label} ({count}×)"
        return {
            "type": event_type,
            "label": label,
            "timestamp": ts,
            "properties": {},
        }

    # ------------------------------------------------------------------ #
    # Timeline
    # ------------------------------------------------------------------ #

    def _build_timeline(
        self, events: list[dict[str, Any]], email_timeline: list[dict[str, Any]], *, limit: int = 60
    ) -> list[dict[str, Any]]:
        """Merge demo events + email events into one timeline, newest first."""
        demo: list[dict[str, Any]] = [
            {
                "type": ev.get("event", ""),
                "label": _EVENT_LABELS.get(ev.get("event", ""), ev.get("event", "")),
                "timestamp": ev.get("timestamp"),
                "properties": ev.get("properties", {}),
            }
            for ev in events
        ]
        merged = demo + email_timeline
        merged.sort(key=lambda e: str(e.get("timestamp", "")), reverse=True)
        return merged[:limit]

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    @staticmethod
    def _site_improvable(db: Session, prospect_id: int) -> bool:
        """Lighthouse verdict on the prospect's existing website (False when unaudited)."""
        prospect = db.get(ProspectDB, prospect_id)
        audit = prospect.lighthouse_json if prospect is not None else None
        return bool(audit.get("is_improvable")) if isinstance(audit, dict) else False

    async def get_behavior(self, db: Session, user_id: int, prospect_id: int) -> dict[str, Any]:
        """Return combined (demo + email + banner leads) temperature, score, signals and timeline."""
        events = await self._events_for_prospect(db, user_id, prospect_id)
        email = self._email_engagement(db, user_id, prospect_id)
        leads = self._demo_leads(db, user_id, prospect_id)
        lead_entries = [
            {
                "type": "demo_lead",
                "label": _EVENT_LABELS["demo_lead"],
                "timestamp": lead.created_at.isoformat() if lead.created_at else None,
                "properties": {"message": lead.message or ""},
            }
            for lead in leads
        ]
        site_improvable = self._site_improvable(db, prospect_id)
        score = lead_scoring.compute(events, email=email, site_improvable=site_improvable, demo_leads=len(leads))
        return {
            "temperature": score["temperature"],
            "score": score["score"],
            "signals": score["signals"],
            "site_improvable": score["site_improvable"],
            "timeline": self._build_timeline(events, email["timeline"] + lead_entries),
            # The prospect's own words — shown prominently in the drawer, newest first.
            "leads": [
                {
                    "message": lead.message,
                    "created_at": lead.created_at.isoformat() if lead.created_at else None,
                }
                for lead in leads
            ],
            "has_data": bool(events) or email["sent"] > 0 or bool(leads),
            "tracking_configured": posthog_service.is_configured,
        }

    async def get_summary(self, db: Session, user_id: int, prospect: ProspectDB) -> str:
        """Return an AI (or rule-based) summary + relance advice for a prospect."""
        from models.user import User

        user = db.get(User, user_id)
        behavior = await self.get_behavior(db, user_id, prospect.id)
        return await llm_service.summarize_behavior(
            sender_name=user.name if user else "",
            company_name=user.company_name if user else None,
            business_name=prospect.name,
            temperature=behavior["temperature"],
            signals=behavior["signals"],
        )

    async def draft_personalized_followup(
        self,
        db: Session,
        user_id: int,
        prospect: ProspectDB,
        *,
        base_subject: str,
        base_body_html: str,
    ) -> dict[str, str]:
        """Draft a behaviour-personalised follow-up email for a prospect."""
        from models.user import User
        from services.email_variables import EmailVariables

        user = db.get(User, user_id)
        behavior = await self.get_behavior(db, user_id, prospect.id)
        first_name, _last, _gender = EmailVariables.resolved_contact(db, prospect.id)
        return await llm_service.draft_followup(
            sender_name=user.name if user else "",
            company_name=user.company_name if user else None,
            business_name=prospect.name,
            first_name=first_name or "",
            temperature=behavior["temperature"],
            signals=behavior["signals"],
            base_subject=base_subject,
            base_body_html=base_body_html,
        )

    async def get_hot_leads(self, db: Session, user_id: int, *, limit: int = 20) -> list[dict[str, Any]]:
        """
        Return the user's hottest leads (demo + email), newest-strongest first.

        One grouped PostHog query for all demo slugs + one grouped email query —
        efficient enough for a dashboard widget. Excludes leads with no activity.
        """
        sites = (
            db.query(DemoSite)
            .filter(
                DemoSite.user_id == user_id,
                DemoSite.prospect_id.isnot(None),
                DemoSite.status != DemoSiteStatus.DELETED.value,
            )
            .all()
        )
        pid_to_slugs: dict[int, list[str]] = defaultdict(list)
        for site in sites:
            if site.prospect_id and site.slug:
                pid_to_slugs[site.prospect_id].append(site.slug)
        if not pid_to_slugs:
            return []

        all_slugs = [slug for slugs in pid_to_slugs.values() for slug in slugs]
        aggregate = await posthog_service.get_aggregate_by_slugs(all_slugs)
        prospect_ids = list(pid_to_slugs.keys())
        email_by_pid = self._email_engagement_bulk(db, user_id, prospect_ids)
        demo_leads_by_pid = self._demo_leads_count_bulk(db, user_id, prospect_ids)

        prospects = db.query(ProspectDB).filter(ProspectDB.id.in_(prospect_ids), ProspectDB.user_id == user_id).all()
        prospect_by_id = {p.id: p for p in prospects}

        leads: list[dict[str, Any]] = []
        for pid, slugs in pid_to_slugs.items():
            prospect = prospect_by_id.get(pid)
            if not prospect:
                continue
            combined = self._combine_slug_aggregates(aggregate, slugs)
            signals = lead_scoring.build_signals_from_aggregate(
                combined, email_by_pid.get(pid), demo_leads=demo_leads_by_pid.get(pid, 0)
            )
            audit = prospect.lighthouse_json if isinstance(prospect.lighthouse_json, dict) else None
            score = lead_scoring.score_from_signals(
                signals, site_improvable=bool(audit.get("is_improvable")) if audit else False
            )
            if score["temperature"] == "unknown":
                continue
            leads.append(
                {
                    "prospect_id": pid,
                    "name": prospect.name,
                    "city": prospect.city,
                    "temperature": score["temperature"],
                    "score": score["score"],
                    "site_improvable": score["site_improvable"],
                    "last_seen": combined["last_seen"],
                    "signals": score["signals"],
                }
            )

        leads.sort(key=lambda lead: lead["score"], reverse=True)
        return leads[:limit]

    @staticmethod
    def _combine_slug_aggregates(aggregate: dict[str, Any], slugs: list[str]) -> dict[str, Any]:
        """Sum a prospect's demo aggregate across all its slugs (keeping the latest last_seen)."""
        combined: dict[str, Any] = {
            "pageviews": 0,
            "visits": 0,
            "phone_clicks": 0,
            "contact_clicks": 0,
            "cta_clicks": 0,
            "last_seen": None,
        }
        for slug in slugs:
            agg = aggregate.get(slug)
            if not agg:
                continue
            for key in ("pageviews", "visits", "phone_clicks", "contact_clicks", "cta_clicks"):
                combined[key] += int(agg.get(key, 0) or 0)
            last = agg.get("last_seen")
            if last and (combined["last_seen"] is None or str(last) > str(combined["last_seen"])):
                combined["last_seen"] = last
        return combined

    @staticmethod
    def _improvable_by_prospect(db: Session, user_id: int, prospect_ids: list[int]) -> dict[int, bool]:
        """Map each prospect id to its Lighthouse 'improvable website' verdict (False when unaudited)."""
        prospects = db.query(ProspectDB).filter(ProspectDB.id.in_(prospect_ids), ProspectDB.user_id == user_id).all()
        result: dict[int, bool] = {}
        for prospect in prospects:
            audit = prospect.lighthouse_json if isinstance(prospect.lighthouse_json, dict) else None
            result[prospect.id] = bool(audit.get("is_improvable")) if audit else False
        return result

    async def get_temperatures(self, db: Session, user_id: int, prospect_ids: list[int]) -> dict[int, dict[str, Any]]:
        """
        Return the hot/warm/cold temperature + score for each given prospect (demo + email).

        One grouped PostHog query + one grouped email query, whatever the number of
        prospects. Prospects with no activity get temperature "unknown".

        Args:
            db: Active database session.
            user_id: Owner of the prospects.
            prospect_ids: Prospects to score.

        Returns:
            ``{prospect_id: {"temperature": str, "score": int}}``.
        """
        if not prospect_ids:
            return {}
        sites = (
            db.query(DemoSite)
            .filter(
                DemoSite.user_id == user_id,
                DemoSite.prospect_id.in_(prospect_ids),
                DemoSite.status != DemoSiteStatus.DELETED.value,
            )
            .all()
        )
        pid_to_slugs: dict[int, list[str]] = defaultdict(list)
        for site in sites:
            if site.prospect_id and site.slug:
                pid_to_slugs[site.prospect_id].append(site.slug)

        all_slugs = [slug for slugs in pid_to_slugs.values() for slug in slugs]
        aggregate = await posthog_service.get_aggregate_by_slugs(all_slugs) if all_slugs else {}
        email_by_pid = self._email_engagement_bulk(db, user_id, prospect_ids)
        demo_leads_by_pid = self._demo_leads_count_bulk(db, user_id, prospect_ids)
        improvable_by_pid = self._improvable_by_prospect(db, user_id, prospect_ids)

        result: dict[int, dict[str, Any]] = {}
        for pid in prospect_ids:
            combined = self._combine_slug_aggregates(aggregate, pid_to_slugs.get(pid, []))
            signals = lead_scoring.build_signals_from_aggregate(
                combined, email_by_pid.get(pid), demo_leads=demo_leads_by_pid.get(pid, 0)
            )
            score = lead_scoring.score_from_signals(signals, site_improvable=improvable_by_pid.get(pid, False))
            result[pid] = {"temperature": score["temperature"], "score": score["score"]}
        return result


behavior_service = BehaviorService()
