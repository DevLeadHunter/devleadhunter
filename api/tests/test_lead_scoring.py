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


def test_aggregate_maps_new_keys() -> None:
    """The hot-leads aggregate path carries the new signals through."""
    signals = ls.build_signals_from_aggregate(
        {"pageviews": 3, "visits": 1, "sections_viewed": 4, "outbound_clicks": 2}
    )
    assert signals["sections_viewed"] == 4
    assert signals["outbound_clicks"] == 2
