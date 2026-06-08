"""
Pure lead-scoring from demo-site behaviour + email engagement.

No I/O — takes raw events (from PostHog) and/or aggregated counts plus email
engagement, and returns structured signals + a hot/warm/cold temperature.
Kept dependency-free so it is trivially testable.
"""
from __future__ import annotations

from typing import Any, Optional, TypedDict


class BehaviorSignals(TypedDict):
    """Aggregated behavioural signals for a prospect (demo + email)."""

    visits: int
    pageviews: int
    cta_clicks: int
    phone_clicks: int
    contact_clicks: int
    max_scroll_depth: int
    total_seconds: int
    emails_sent: int
    emails_opened: int
    emails_clicked: int
    last_seen: Optional[str]


class BehaviorScore(TypedDict):
    """Computed lead score."""

    temperature: str  # hot | warm | cold | unknown
    score: int  # 0–100
    signals: BehaviorSignals


def empty_signals() -> BehaviorSignals:
    """Return a zeroed signals structure."""
    return {
        "visits": 0,
        "pageviews": 0,
        "cta_clicks": 0,
        "phone_clicks": 0,
        "contact_clicks": 0,
        "max_scroll_depth": 0,
        "total_seconds": 0,
        "emails_sent": 0,
        "emails_opened": 0,
        "emails_clicked": 0,
        "last_seen": None,
    }


def _has_any_activity(signals: BehaviorSignals) -> bool:
    """True when there is at least one demo or email signal."""
    return any(
        (
            signals["visits"],
            signals["pageviews"],
            signals["cta_clicks"],
            signals["phone_clicks"],
            signals["contact_clicks"],
            signals["total_seconds"],
            signals["emails_sent"],
            signals["emails_opened"],
            signals["emails_clicked"],
        )
    )


def score_from_signals(signals: BehaviorSignals) -> BehaviorScore:
    """Compute temperature + 0–100 score from a signals structure (demo + email)."""
    if not _has_any_activity(signals):
        return {"temperature": "unknown", "score": 0, "signals": signals}

    score = 0
    # Demo behaviour
    score += min(signals["visits"], 5) * 8
    score += min(signals["pageviews"], 6) * 3
    score += signals["cta_clicks"] * 10
    score += signals["phone_clicks"] * 20  # strongest demo intent
    score += signals["contact_clicks"] * 18
    score += min(signals["total_seconds"] // 30, 6) * 4
    if signals["max_scroll_depth"] >= 75:
        score += 8
    # Email engagement
    score += min(signals["emails_opened"], 5) * 4
    score += min(signals["emails_clicked"], 5) * 12  # clicked the demo link = strong intent
    score = min(score, 100)

    strong_intent = (
        signals["phone_clicks"] > 0 or signals["contact_clicks"] > 0 or signals["emails_clicked"] > 0
    )
    if strong_intent or score >= 60:
        temperature = "hot"
    elif score >= 25:
        temperature = "warm"
    else:
        temperature = "cold"

    return {"temperature": temperature, "score": score, "signals": signals}


def _apply_email(signals: BehaviorSignals, email: Optional[dict[str, Any]]) -> None:
    """Fold email engagement counts into a signals structure."""
    if not email:
        return
    signals["emails_sent"] = int(email.get("sent", 0) or 0)
    signals["emails_opened"] = int(email.get("opened", 0) or 0)
    signals["emails_clicked"] = int(email.get("clicked", 0) or 0)


def compute(events: list[dict[str, Any]], email: Optional[dict[str, Any]] = None) -> BehaviorScore:
    """
    Compute a lead score from raw demo events + optional email engagement.

    @param events - List of ``{"event", "timestamp", "properties"}`` items.
    @param email - Optional ``{"sent", "opened", "clicked"}`` counts.
    @returns Temperature, a 0–100 score and the underlying signals.
    """
    signals = empty_signals()
    sessions: set[str] = set()

    for ev in events:
        name = ev.get("event", "")
        props = ev.get("properties", {}) if isinstance(ev.get("properties"), dict) else {}

        session_id = props.get("$session_id") or props.get("session_id")
        if session_id:
            sessions.add(str(session_id))

        if name == "$pageview":
            signals["pageviews"] += 1
        elif name == "demo_cta_click":
            signals["cta_clicks"] += 1
        elif name == "demo_phone_click":
            signals["phone_clicks"] += 1
        elif name == "demo_contact_click":
            signals["contact_clicks"] += 1
        elif name == "demo_scroll_depth":
            depth = props.get("depth") or props.get("percent") or 0
            try:
                signals["max_scroll_depth"] = max(signals["max_scroll_depth"], int(depth))
            except (TypeError, ValueError):
                pass
        elif name == "demo_time_on_page":
            seconds = props.get("seconds") or props.get("duration") or 0
            try:
                signals["total_seconds"] += int(seconds)
            except (TypeError, ValueError):
                pass

    signals["visits"] = len(sessions) if sessions else (1 if signals["pageviews"] else 0)
    if events:
        signals["last_seen"] = events[0].get("timestamp")

    _apply_email(signals, email)
    return score_from_signals(signals)


def build_signals_from_aggregate(
    aggregate: dict[str, Any], email: Optional[dict[str, Any]] = None
) -> BehaviorSignals:
    """
    Build a signals structure from PostHog aggregate counts + email engagement.

    Used by the hot-leads list (one grouped query instead of per-prospect events).
    """
    signals = empty_signals()
    signals["pageviews"] = int(aggregate.get("pageviews", 0) or 0)
    signals["visits"] = int(aggregate.get("visits", 0) or 0)
    signals["cta_clicks"] = int(aggregate.get("cta_clicks", 0) or 0)
    signals["phone_clicks"] = int(aggregate.get("phone_clicks", 0) or 0)
    signals["contact_clicks"] = int(aggregate.get("contact_clicks", 0) or 0)
    last_seen = aggregate.get("last_seen")
    signals["last_seen"] = str(last_seen) if last_seen else None
    _apply_email(signals, email)
    return signals
