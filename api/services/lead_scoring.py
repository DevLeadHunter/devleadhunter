"""
Pure lead-scoring from demo-site behaviour + email engagement.

No I/O — takes raw events (from PostHog) and/or aggregated counts plus email
engagement, and returns structured signals + a hot/warm/cold temperature.
Kept dependency-free so it is trivially testable.
"""

from __future__ import annotations

from typing import Any, TypedDict


class BehaviorSignals(TypedDict):
    """Aggregated behavioural signals for a prospect (demo + email)."""

    visits: int
    pageviews: int
    sections_viewed: int
    cta_clicks: int
    phone_clicks: int
    contact_clicks: int
    outbound_clicks: int
    max_scroll_depth: int
    total_seconds: int
    video_plays: int
    video_completes: int
    video_replays: int
    video_fullscreen: int
    video_watch_seconds: int
    video_max_progress: int
    emails_sent: int
    emails_opened: int
    emails_clicked: int
    last_seen: str | None


class BehaviorScore(TypedDict):
    """Computed lead score."""

    temperature: str  # hot | warm | cold | unknown
    score: int  # 0–100
    signals: BehaviorSignals
    # Opportunity flag: the prospect's EXISTING website scored poorly on
    # Lighthouse → a redesign pitch has real ammunition. Orthogonal to the
    # engagement temperature but folded into the score as a bonus.
    site_improvable: bool


def empty_signals() -> BehaviorSignals:
    """Return a zeroed signals structure."""
    return {
        "visits": 0,
        "pageviews": 0,
        "sections_viewed": 0,
        "cta_clicks": 0,
        "phone_clicks": 0,
        "contact_clicks": 0,
        "outbound_clicks": 0,
        "max_scroll_depth": 0,
        "total_seconds": 0,
        "video_plays": 0,
        "video_completes": 0,
        "video_replays": 0,
        "video_fullscreen": 0,
        "video_watch_seconds": 0,
        "video_max_progress": 0,
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
            signals["sections_viewed"],
            signals["cta_clicks"],
            signals["phone_clicks"],
            signals["contact_clicks"],
            signals["outbound_clicks"],
            signals["total_seconds"],
            signals["video_plays"],
            signals["video_watch_seconds"],
            signals["video_replays"],
            signals["emails_sent"],
            signals["emails_opened"],
            signals["emails_clicked"],
        )
    )


def score_from_signals(signals: BehaviorSignals, site_improvable: bool = False) -> BehaviorScore:
    """Compute temperature + 0–100 score from a signals structure (demo + email).

    Args:
        signals: Aggregated demo + email signals.
        site_improvable: Lighthouse verdict on the prospect's EXISTING website (True = weak site → redesign opportunity). Adds a score bonus once the prospect shows any engagement; never creates activity by itself.

    Returns:
        Temperature, 0–100 score, signals and the opportunity flag.
    """
    if not _has_any_activity(signals):
        # No engagement: the weak-website opportunity is surfaced via the flag
        # but must not fabricate a temperature on its own.
        return {"temperature": "unknown", "score": 0, "signals": signals, "site_improvable": site_improvable}

    score = 0
    # Demo behaviour
    score += min(signals["visits"], 5) * 8
    score += min(signals["pageviews"], 6) * 3
    score += min(signals["sections_viewed"], 5) * 3  # read several sections = genuine interest
    score += signals["cta_clicks"] * 10
    score += signals["phone_clicks"] * 20  # strongest demo intent
    score += signals["contact_clicks"] * 18
    score += min(signals["outbound_clicks"], 3) * 6  # clicked map/social = intent to verify the business
    score += min(signals["total_seconds"] // 30, 6) * 4
    if signals["max_scroll_depth"] >= 75:
        score += 8
    # Prospection video: pressing play = real curiosity; watching to the end
    # (30-45 s of full attention) = a strong warm-up signal. Rewatching, going
    # fullscreen and actual watched seconds are extra attention signals — capped
    # so the video can't dominate the score, and additive with play/complete.
    score += min(signals["video_plays"], 2) * 8
    score += min(signals["video_completes"], 1) * 12
    score += min(signals["video_replays"], 2) * 8  # re-watched = strong interest
    score += min(signals["video_fullscreen"], 1) * 6  # went fullscreen = deliberate attention
    score += min(signals["video_watch_seconds"] // 10, 3) * 2  # real seconds actually watched
    if signals["video_max_progress"] >= 75:
        score += 4  # watched most of the clip even without hitting 95 %
    # Email engagement
    score += min(signals["emails_opened"], 5) * 4
    score += min(signals["emails_clicked"], 5) * 12  # clicked the demo link = strong intent
    # Redesign opportunity: an engaged prospect whose current site is weak is
    # easier to close (the pitch has proof) → flat bonus.
    if site_improvable:
        score += 10
    score = min(score, 100)

    strong_intent = signals["phone_clicks"] > 0 or signals["contact_clicks"] > 0 or signals["emails_clicked"] > 0
    if strong_intent or score >= 60:
        temperature = "hot"
    elif score >= 25:
        temperature = "warm"
    else:
        temperature = "cold"

    return {"temperature": temperature, "score": score, "signals": signals, "site_improvable": site_improvable}


def _apply_email(signals: BehaviorSignals, email: dict[str, Any] | None) -> None:
    """Fold email engagement counts into a signals structure."""
    if not email:
        return
    signals["emails_sent"] = int(email.get("sent", 0) or 0)
    signals["emails_opened"] = int(email.get("opened", 0) or 0)
    signals["emails_clicked"] = int(email.get("clicked", 0) or 0)


def compute(
    events: list[dict[str, Any]],
    email: dict[str, Any] | None = None,
    site_improvable: bool = False,
) -> BehaviorScore:
    """
    Compute a lead score from raw demo events + optional email engagement.

    Args:
        events: List of ``{"event", "timestamp", "properties"}`` items.
        email: Optional ``{"sent", "opened", "clicked"}`` counts.
        site_improvable: Lighthouse verdict on the prospect's existing website.

    Returns:
        Temperature, a 0–100 score and the underlying signals.
    """
    signals = empty_signals()
    sessions: set[str] = set()
    section_names: set[str] = set()

    for ev in events:
        name = ev.get("event", "")
        props = ev.get("properties", {}) if isinstance(ev.get("properties"), dict) else {}

        session_id = props.get("$session_id") or props.get("session_id")
        if session_id:
            sessions.add(str(session_id))

        if name == "$pageview":
            signals["pageviews"] += 1
        elif name == "demo_section_view":
            # Count DISTINCT sections read (reading several = genuine interest).
            section_names.add(str(props.get("section") or props.get("position") or "?"))
        elif name == "demo_cta_click":
            signals["cta_clicks"] += 1
        elif name == "demo_phone_click":
            signals["phone_clicks"] += 1
        elif name == "demo_contact_click":
            signals["contact_clicks"] += 1
        elif name == "demo_outbound_click":
            signals["outbound_clicks"] += 1
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
        elif name == "demo_video_play":
            signals["video_plays"] += 1
        elif name == "demo_video_complete":
            signals["video_completes"] += 1
        elif name == "demo_video_replay":
            signals["video_replays"] += 1
        elif name == "demo_video_fullscreen":
            if props.get("entered"):
                signals["video_fullscreen"] += 1
        elif name == "demo_video_progress":
            percent = props.get("percent") or 0
            try:
                signals["video_max_progress"] = max(signals["video_max_progress"], int(percent))
            except (TypeError, ValueError):
                pass
        elif name == "demo_video_watch_time":
            seconds = props.get("seconds") or 0
            try:
                # Events are cumulative — keep the largest watched-seconds seen.
                signals["video_watch_seconds"] = max(signals["video_watch_seconds"], int(seconds))
            except (TypeError, ValueError):
                pass

    # A complete (≥95 %) implies max progress even if no progress event landed.
    if signals["video_completes"] > 0:
        signals["video_max_progress"] = max(signals["video_max_progress"], 95)

    signals["sections_viewed"] = len(section_names)
    signals["visits"] = len(sessions) if sessions else (1 if signals["pageviews"] else 0)
    if events:
        signals["last_seen"] = events[0].get("timestamp")

    _apply_email(signals, email)
    return score_from_signals(signals, site_improvable=site_improvable)


def build_signals_from_aggregate(aggregate: dict[str, Any], email: dict[str, Any] | None = None) -> BehaviorSignals:
    """
    Build a signals structure from PostHog aggregate counts + email engagement.

    Used by the hot-leads list (one grouped query instead of per-prospect events).
    """
    signals = empty_signals()
    signals["pageviews"] = int(aggregate.get("pageviews", 0) or 0)
    signals["visits"] = int(aggregate.get("visits", 0) or 0)
    signals["sections_viewed"] = int(aggregate.get("sections_viewed", 0) or 0)
    signals["cta_clicks"] = int(aggregate.get("cta_clicks", 0) or 0)
    signals["phone_clicks"] = int(aggregate.get("phone_clicks", 0) or 0)
    signals["contact_clicks"] = int(aggregate.get("contact_clicks", 0) or 0)
    signals["outbound_clicks"] = int(aggregate.get("outbound_clicks", 0) or 0)
    last_seen = aggregate.get("last_seen")
    signals["last_seen"] = str(last_seen) if last_seen else None
    _apply_email(signals, email)
    return signals
