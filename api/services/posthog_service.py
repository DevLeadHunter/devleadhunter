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
    "demo_video_play",
    "demo_video_progress",
    "demo_video_complete",
    "demo_video_cta_click",
)


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
        properties: Optional[dict[str, Any]] = None,
        timestamp: Optional[str] = None,
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
        except Exception as exc:  # noqa: BLE001
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
        except Exception as exc:  # noqa: BLE001
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
        except Exception as exc:  # noqa: BLE001
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


posthog_service = PostHogService()
