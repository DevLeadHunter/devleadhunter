"""
PostHog read-side integration.

Demo sites capture behaviour with posthog-js (client side). This service reads
those events back via the PostHog query API (HogQL) to power lead scoring,
the behaviour timeline and AI summaries. Degrades gracefully (returns an empty
list) when PostHog is not configured.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

# Custom events emitted by the demo-host (plus PostHog's built-in "$pageview").
DEMO_EVENTS: tuple[str, ...] = (
    "$pageview",
    "demo_section_view",
    "demo_cta_click",
    "demo_phone_click",
    "demo_contact_click",
    "demo_outbound_click",
    "demo_scroll_depth",
    "demo_time_on_page",
    "demo_engaged",
    "demo_cta_banner_open",
    "demo_cta_banner_auto_open",
    "demo_cta_banner_field_focus",
    "demo_cta_banner_submitted",
    "demo_cta_banner_collapse",
    "demo_cta_banner_abandoned",
    "demo_video_play",
    "demo_video_resume",
    "demo_video_pause",
    "demo_video_replay",
    "demo_video_progress",
    "demo_video_complete",
    "demo_video_watch_time",
    "demo_video_seek",
    "demo_video_fullscreen",
    "demo_video_mute",
    "demo_video_cta_click",
    # The receptionist's video page (/va) emits the same events under its own prefix.
    "assistant_video_play",
    "assistant_video_resume",
    "assistant_video_pause",
    "assistant_video_replay",
    "assistant_video_progress",
    "assistant_video_complete",
    "assistant_video_watch_time",
    "assistant_video_seek",
    "assistant_video_fullscreen",
    "assistant_video_mute",
    "assistant_video_cta_click",
)


@dataclass(frozen=True)
class DemoSession:
    """
    One browsing session on a demo, summarised from its events.

    Attributes:
        slug: Demo slug the session browsed.
        session_id: PostHog session id.
        started_at: First event of the session (naive UTC).
        device_type: ``Mobile``, ``Desktop``, ``Tablet``, or None when unknown.
        city: GeoIP city, None when PostHog could not place the visitor.
        interaction_count: Events other than page views (scroll, section, click, time…).
        time_on_page_seconds: Visible time reported when the visitor left, None when it never arrived.
        engaged_seconds: Visible time when the visit qualified as engaged, None when it never did.
    """

    slug: str
    session_id: str
    started_at: datetime
    device_type: str | None
    city: str | None
    interaction_count: int
    time_on_page_seconds: float | None
    engaged_seconds: float | None


class PostHogService:
    """Reads demo-site behavioural events from PostHog."""

    def __init__(self) -> None:
        self._host: str = settings.posthog_api_host.rstrip("/")
        self._project_id = settings.posthog_project_id
        self._api_key = settings.posthog_personal_api_key
        self._ingestion_host: str = settings.posthog_ingestion_host.rstrip("/")
        self._project_api_key = settings.posthog_project_api_key

    @property
    def is_configured(self) -> bool:
        """True when both a project id and a personal API key are available (read side)."""
        return bool(self._project_id and self._api_key)

    @property
    def can_capture(self) -> bool:
        """True when server-side event capture is configured (write side, phc_ key)."""
        return bool(self._project_api_key)

    async def capture(
        self,
        *,
        distinct_id: str,
        event: str,
        properties: dict[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> None:
        """
        Send a server-side event to PostHog (best-effort, never raises).

        Pushes email engagement events into the PostHog event stream so they can be
        combined with demo events in funnels. ``distinct_id`` should match the demo
        capture (the demo slug) so both streams resolve to the same person.
        """
        if not self.can_capture or not distinct_id or not event:
            return
        body: dict[str, Any] = {
            "api_key": self._project_api_key,
            "event": event,
            "distinct_id": distinct_id,
            "properties": properties or {},
        }
        if timestamp:
            body["timestamp"] = timestamp
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(f"{self._ingestion_host}/capture/", json=body)
                response.raise_for_status()
        except Exception as exc:
            logger.warning("PostHog capture failed (event=%s): %s", event, exc)

    @staticmethod
    def _safe_slug(slug: str) -> str:
        """Sanitize a slug for safe inlining in a HogQL string literal."""
        return re.sub(r"[^a-zA-Z0-9_-]", "", slug or "")

    async def _run_query(self, query: str) -> list[Any]:
        """Run a HogQL query and return the raw result rows ([] on error / not configured)."""
        if not self.is_configured:
            return []
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self._host}/api/projects/{self._project_id}/query/",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"query": {"kind": "HogQLQuery", "query": query}},
                )
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
        except Exception as exc:
            logger.warning("PostHog query failed: %s", exc)
            return []
        results = payload.get("results", [])
        return results if isinstance(results, list) else []

    async def get_aggregate_by_slugs(self, slugs: list[str]) -> dict[str, dict[str, Any]]:
        """
        Return aggregated behaviour counts per demo slug (one grouped query).

        Each value: ``{pageviews, visits, phone_clicks, contact_clicks, cta_clicks,
        sections_viewed, outbound_clicks, last_seen}``.
        Empty dict when PostHog is not configured / no data.
        """
        safe_slugs = [self._safe_slug(s) for s in slugs if self._safe_slug(s)]
        if not self.is_configured or not safe_slugs:
            return {}

        in_list = ", ".join(f"'{s}'" for s in safe_slugs)
        query = (
            "SELECT properties.demo_slug AS slug, "
            "countIf(event = '$pageview') AS pageviews, "
            "count(DISTINCT properties.$session_id) AS visits, "
            "countIf(event = 'demo_phone_click') AS phone_clicks, "
            "countIf(event = 'demo_contact_click') AS contact_clicks, "
            "countIf(event = 'demo_cta_click') AS cta_clicks, "
            "uniqIf(properties.section, event = 'demo_section_view') AS sections_viewed, "
            "countIf(event = 'demo_outbound_click') AS outbound_clicks, "
            "max(timestamp) AS last_seen "
            "FROM events "
            f"WHERE properties.demo_slug IN ({in_list}) "
            "GROUP BY slug"
        )
        rows = await self._run_query(query)
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) < 9:
                continue
            slug = str(row[0])
            result[slug] = {
                "pageviews": row[1],
                "visits": row[2],
                "phone_clicks": row[3],
                "contact_clicks": row[4],
                "cta_clicks": row[5],
                "sections_viewed": row[6],
                "outbound_clicks": row[7],
                "last_seen": row[8],
            }
        return result

    async def get_demo_sessions(self, slugs: list[str], since: datetime) -> list[DemoSession]:
        """
        Return every browsing session on the given demos since a moment, one grouped query.

        Only demo events count (``DEMO_EVENTS``): the email events mirrored under the same
        ``demo_slug`` are server-side and never make a visit.

        Args:
            slugs: Demo slugs to read.
            since: Earliest session start to keep (naive UTC).

        Returns:
            The sessions, oldest first; empty when PostHog is not configured, no slug is given or the query fails.
        """
        safe_slugs = sorted({self._safe_slug(s) for s in slugs if self._safe_slug(s)})
        if not self.is_configured or not safe_slugs:
            return []
        in_list = ", ".join(f"'{s}'" for s in safe_slugs)
        demo_events_list = ", ".join(f"'{e}'" for e in DEMO_EVENTS)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S")
        query = (
            "SELECT properties.demo_slug AS slug, properties.$session_id AS session_id, "
            "min(timestamp) AS started_at, "
            "any(properties.$device_type) AS device_type, "
            "any(properties.$geoip_city_name) AS city, "
            "countIf(event != '$pageview') AS interaction_count, "
            "maxIf(toFloat(properties.seconds), event = 'demo_time_on_page') AS time_on_page_seconds, "
            "maxIf(toFloat(properties.engaged_seconds), event = 'demo_engaged') AS engaged_seconds "
            "FROM events "
            f"WHERE properties.demo_slug IN ({in_list}) "
            f"AND event IN ({demo_events_list}) "
            f"AND timestamp >= '{since_str}' "
            "GROUP BY slug, session_id "
            "ORDER BY started_at "
            "LIMIT 10000"
        )
        sessions: list[DemoSession] = []
        for row in await self._run_query(query):
            if not isinstance(row, (list, tuple)) or len(row) < 8 or not row[0] or not row[1] or not row[2]:
                continue
            sessions.append(
                DemoSession(
                    slug=str(row[0]),
                    session_id=str(row[1]),
                    started_at=self._to_naive_utc(str(row[2])),
                    device_type=str(row[3]) if row[3] else None,
                    city=str(row[4]) if row[4] else None,
                    interaction_count=int(row[5] or 0),
                    time_on_page_seconds=float(row[6]) if row[6] is not None else None,
                    engaged_seconds=float(row[7]) if row[7] is not None else None,
                )
            )
        return sessions

    @staticmethod
    def _to_naive_utc(value: str) -> datetime:
        """Parse a PostHog ISO timestamp into the naive UTC datetimes the API stores."""
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed
        return parsed.astimezone(UTC).replace(tzinfo=None)

    async def get_events_for_slug(self, slug: str, *, limit: int = 300) -> list[dict[str, Any]]:
        """
        Return raw DEMO behavioural events captured for a demo slug, newest first.

        Restricted to demo events (``DEMO_EVENTS``): email events are also
        mirrored into PostHog under the same ``demo_slug`` (for funnels), but the
        in-app behaviour timeline sources email from ``EmailLog`` — so filtering
        here avoids showing each email event twice.

        Each item: ``{"event": str, "timestamp": str, "properties": dict}``.
        Returns an empty list when PostHog is not configured or on error.
        """
        if not self.is_configured:
            return []

        safe_slug = self._safe_slug(slug)
        if not safe_slug:
            return []

        demo_events_list = ", ".join(f"'{e}'" for e in DEMO_EVENTS)
        query = (
            "SELECT event, timestamp, properties "
            "FROM events "
            f"WHERE properties.demo_slug = '{safe_slug}' "
            f"AND event IN ({demo_events_list}) "
            f"ORDER BY timestamp DESC LIMIT {int(limit)}"
        )

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self._host}/api/projects/{self._project_id}/query/",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"query": {"kind": "HogQLQuery", "query": query}},
                )
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
        except Exception as exc:
            logger.warning("PostHog query failed for slug=%s: %s", slug, exc)
            return []

        results = payload.get("results", [])
        events: list[dict[str, Any]] = []
        for row in results:
            if not isinstance(row, (list, tuple)) or len(row) < 3:
                continue
            event_name, timestamp, properties = row[0], row[1], row[2]
            if isinstance(properties, str):
                # HogQL may return properties as a JSON string.
                import json

                try:
                    properties = json.loads(properties)
                except (ValueError, TypeError):
                    properties = {}
            events.append(
                {
                    "event": str(event_name),
                    "timestamp": str(timestamp),
                    "properties": properties if isinstance(properties, dict) else {},
                }
            )
        return events

    async def count_demo_visits_since(self, slugs: list[str], since: datetime) -> dict[str, int]:
        """
        Count demo pageviews and qualified visits for the given slugs since a timestamp.

        Used by the daily recap so it never persists demo events itself. Returns
        ``{"pageviews": int, "engaged": int}`` — zeros when PostHog is not configured,
        no slugs are given, or the query fails.
        """
        safe_slugs = [self._safe_slug(s) for s in slugs if self._safe_slug(s)]
        if not self.is_configured or not safe_slugs:
            return {"pageviews": 0, "engaged": 0}
        in_list = ", ".join(f"'{s}'" for s in safe_slugs)
        since_str = since.strftime("%Y-%m-%d %H:%M:%S")
        query = (
            "SELECT countIf(event = '$pageview') AS pageviews, "
            "countIf(event = 'demo_engaged') AS engaged "
            "FROM events "
            f"WHERE properties.demo_slug IN ({in_list}) "
            f"AND timestamp >= '{since_str}'"
        )
        rows = await self._run_query(query)
        if rows and isinstance(rows[0], (list, tuple)) and len(rows[0]) >= 2:
            return {"pageviews": int(rows[0][0] or 0), "engaged": int(rows[0][1] or 0)}
        return {"pageviews": 0, "engaged": 0}


posthog_service = PostHogService()
