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
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from services import lead_scoring
from services.llm_service import llm_service
from services.posthog_service import posthog_service

# Human labels for the timeline.
_EVENT_LABELS: dict[str, str] = {
    "$pageview": "Visite de la démo",
    "demo_cta_click": "Clic sur un bouton d'action",
    "demo_phone_click": "Clic sur le téléphone",
    "demo_contact_click": "Clic sur le contact",
    "demo_scroll_depth": "A fait défiler la page",
    "demo_time_on_page": "Temps passé sur la page",
    "email_sent": "Email envoyé",
    "email_opened": "Email ouvert",
    "email_clicked": "Lien de l'email cliqué",
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
        logs = (
            db.query(EmailLog)
            .filter(EmailLog.user_id == user_id, EmailLog.prospect_id == prospect_id)
            .all()
        )
        sent = opened = clicked = 0
        timeline: list[dict[str, Any]] = []
        for log in logs:
            if log.sent_at:
                sent += 1
                timeline.append(self._email_entry("email_sent", log.sent_at))
            if log.opened_at:
                opened += 1
                timeline.append(self._email_entry("email_opened", log.opened_at))
            if log.clicked_at:
                clicked += 1
                timeline.append(self._email_entry("email_clicked", log.clicked_at))
        return {"sent": sent, "opened": opened, "clicked": clicked, "timeline": timeline}

    def _email_engagement_bulk(
        self, db: Session, user_id: int, prospect_ids: list[int]
    ) -> dict[int, dict[str, int]]:
        """Return email engagement counts per prospect (one grouped query)."""
        if not prospect_ids:
            return {}
        rows = db.execute(
            select(
                EmailLog.prospect_id,
                func.count(EmailLog.sent_at),
                func.count(EmailLog.opened_at),
                func.count(EmailLog.clicked_at),
            )
            .where(EmailLog.user_id == user_id, EmailLog.prospect_id.in_(prospect_ids))
            .group_by(EmailLog.prospect_id)
        ).all()
        result: dict[int, dict[str, int]] = {}
        for pid, sent, opened, clicked in rows:
            if pid is None:
                continue
            result[int(pid)] = {"sent": int(sent or 0), "opened": int(opened or 0), "clicked": int(clicked or 0)}
        return result

    @staticmethod
    def _email_entry(event_type: str, when: Any) -> dict[str, Any]:
        """Build a timeline entry for an email event."""
        ts = when.isoformat() if hasattr(when, "isoformat") else str(when)
        return {"type": event_type, "label": _EVENT_LABELS.get(event_type, event_type), "timestamp": ts, "properties": {}}

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
        """Return combined (demo + email) temperature, score, signals and timeline."""
        events = await self._events_for_prospect(db, user_id, prospect_id)
        email = self._email_engagement(db, user_id, prospect_id)
        site_improvable = self._site_improvable(db, prospect_id)
        score = lead_scoring.compute(events, email=email, site_improvable=site_improvable)
        return {
            "temperature": score["temperature"],
            "score": score["score"],
            "signals": score["signals"],
            "site_improvable": score["site_improvable"],
            "timeline": self._build_timeline(events, email["timeline"]),
            "has_data": bool(events) or email["sent"] > 0,
            "tracking_configured": posthog_service.is_configured,
        }

    async def get_summary(self, db: Session, user_id: int, prospect: ProspectDB) -> str:
        """Return an AI (or rule-based) summary + relance advice for a prospect."""
        behavior = await self.get_behavior(db, user_id, prospect.id)
        return await llm_service.summarize_behavior(
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
        behavior = await self.get_behavior(db, user_id, prospect.id)
        name_parts = (prospect.name or "").split()
        return await llm_service.draft_followup(
            business_name=prospect.name,
            first_name=name_parts[0] if name_parts else "",
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

        prospects = (
            db.query(ProspectDB)
            .filter(ProspectDB.id.in_(prospect_ids), ProspectDB.user_id == user_id)
            .all()
        )
        prospect_by_id = {p.id: p for p in prospects}

        leads: list[dict[str, Any]] = []
        for pid, slugs in pid_to_slugs.items():
            prospect = prospect_by_id.get(pid)
            if not prospect:
                continue
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

            signals = lead_scoring.build_signals_from_aggregate(combined, email_by_pid.get(pid))
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


behavior_service = BehaviorService()
