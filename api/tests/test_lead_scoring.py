"""
Unit tests for the demo-behaviour lead scoring — focused on the newer signals
(section views, outbound clicks) added for richer demo-link tracking.
"""
from services import lead_scoring as ls


def _pageview(session: str = "s1") -> dict:
    """A minimal $pageview event."""
    return {"event": "$pageview", "timestamp": "2026-07-13T10:00:00Z", "properties": {"$session_id": session}}


def test_section_views_are_counted_distinct() -> None:
    """demo_section_view contributes DISTINCT sections, not raw event count."""
    events = [
        _pageview(),
        {"event": "demo_section_view", "timestamp": "t", "properties": {"section": "Services"}},
        {"event": "demo_section_view", "timestamp": "t", "properties": {"section": "Avis"}},
        {"event": "demo_section_view", "timestamp": "t", "properties": {"section": "Services"}},
    ]
    result = ls.compute(events)
    assert result["signals"]["sections_viewed"] == 2


def test_outbound_clicks_counted() -> None:
    """demo_outbound_click increments the outbound signal."""
    events = [
        _pageview(),
        {"event": "demo_outbound_click", "timestamp": "t", "properties": {"host": "maps.google.com"}},
        {"event": "demo_outbound_click", "timestamp": "t", "properties": {"host": "instagram.com"}},
    ]
    result = ls.compute(events)
    assert result["signals"]["outbound_clicks"] == 2


def test_new_signals_raise_the_score() -> None:
    """Reading sections + an outbound click scores higher than a bare pageview."""
    base = ls.compute([_pageview()])
    engaged = ls.compute(
        [
            _pageview(),
            {"event": "demo_section_view", "timestamp": "t", "properties": {"section": "A"}},
            {"event": "demo_section_view", "timestamp": "t", "properties": {"section": "B"}},
            {"event": "demo_outbound_click", "timestamp": "t", "properties": {"host": "maps.google.com"}},
        ]
    )
    assert engaged["score"] > base["score"]


def test_engaged_event_alone_does_not_double_count() -> None:
    """demo_engaged is a timeline marker (derived) — it must not add to the score."""
    with_marker = ls.compute([_pageview(), {"event": "demo_engaged", "timestamp": "t", "properties": {}}])
    without = ls.compute([_pageview()])
    assert with_marker["score"] == without["score"]


def test_video_engagement_raises_the_score() -> None:
    """Replaying, going fullscreen and watched-time add attention to the score."""
    base = ls.compute([_pageview(), {"event": "demo_video_play", "timestamp": "t", "properties": {}}])
    engaged = ls.compute(
        [
            _pageview(),
            {"event": "demo_video_play", "timestamp": "t", "properties": {}},
            {"event": "demo_video_complete", "timestamp": "t", "properties": {}},
            {"event": "demo_video_replay", "timestamp": "t", "properties": {"count": 1}},
            {"event": "demo_video_fullscreen", "timestamp": "t", "properties": {"entered": True}},
            {"event": "demo_video_watch_time", "timestamp": "t", "properties": {"seconds": 32}},
        ]
    )
    assert engaged["signals"]["video_replays"] == 1
    assert engaged["signals"]["video_fullscreen"] == 1
    assert engaged["signals"]["video_watch_seconds"] == 32
    assert engaged["signals"]["video_max_progress"] >= 95
    assert engaged["score"] > base["score"]


def test_video_only_activity_gets_a_temperature() -> None:
    """A prospect who only watched the video is not left as 'unknown'."""
    result = ls.compute([
        {"event": "demo_video_play", "timestamp": "t", "properties": {}},
        {"event": "demo_video_watch_time", "timestamp": "t", "properties": {"seconds": 30}},
    ])
    assert result["temperature"] != "unknown"


def test_video_watch_time_keeps_the_max() -> None:
    """Cumulative watch-time events keep the largest value, not the sum."""
    result = ls.compute([
        _pageview(),
        {"event": "demo_video_watch_time", "timestamp": "t", "properties": {"seconds": 10}},
        {"event": "demo_video_watch_time", "timestamp": "t", "properties": {"seconds": 25}},
        {"event": "demo_video_watch_time", "timestamp": "t", "properties": {"seconds": 18}},
    ])
    assert result["signals"]["video_watch_seconds"] == 25


def test_non_scored_video_events_do_not_change_score() -> None:
    """pause / seek / mute / resume are timeline color, not scoring signals."""
    scored = ls.compute([_pageview(), {"event": "demo_video_play", "timestamp": "t", "properties": {}}])
    with_noise = ls.compute([
        _pageview(),
        {"event": "demo_video_play", "timestamp": "t", "properties": {}},
        {"event": "demo_video_pause", "timestamp": "t", "properties": {"percent": 40}},
        {"event": "demo_video_seek", "timestamp": "t", "properties": {"direction": "backward"}},
        {"event": "demo_video_mute", "timestamp": "t", "properties": {"muted": True}},
        {"event": "demo_video_resume", "timestamp": "t", "properties": {"percent": 40}},
    ])
    assert with_noise["score"] == scored["score"]


def test_aggregate_maps_new_keys() -> None:
    """The hot-leads aggregate path carries the new signals through."""
    signals = ls.build_signals_from_aggregate(
        {"pageviews": 3, "visits": 1, "sections_viewed": 4, "outbound_clicks": 2}
    )
    assert signals["sections_viewed"] == 4
    assert signals["outbound_clicks"] == 2
