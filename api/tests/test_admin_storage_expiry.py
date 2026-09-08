"""The storage page anchors a demo deliverable's expiry on its demo's real lifecycle.

Historically the page flagged any video/thumbnail older than a fixed 14 days — which, once the demo TTL
moved to 21 days and started counting from the first send (not generation), wrongly flagged files still
tied to live or not-yet-sent demos. Expiry is now read from the demo row itself (``expire_due_sites``
purges exactly when ``expires_at`` passes), so the page and the cleanup agree.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from api.v1.routes.admin_storage import _classify, _expiry_state, _slug_from_key
from enums.demo_site_status import DemoSiteStatus

_NOW = datetime(2026, 9, 9, 12, 0, 0, tzinfo=UTC)


def _demo(status: str, sent_at: datetime | None, expires_at: datetime) -> SimpleNamespace:
    """Build a stand-in demo row exposing the columns ``_expiry_state`` reads."""
    return SimpleNamespace(status=status, demo_link_sent_at=sent_at, expires_at=expires_at)


def test_missing_demo_is_a_leftover() -> None:
    # No demo references the file any more → the cleanup should already have removed it.
    assert _expiry_state(None, _NOW) == (True, None, False)


def test_delivered_demo_is_permanent() -> None:
    # A sold demo is excluded from the TTL, even with an expires_at in the past.
    demo = _demo(DemoSiteStatus.DELIVERED.value, _NOW - timedelta(days=100), _NOW - timedelta(days=100))
    assert _expiry_state(demo, _NOW) == (False, None, False)


def test_link_not_sent_is_pending() -> None:
    # A pre-generated demo whose link was never emailed: countdown not started, never flagged.
    demo = _demo(DemoSiteStatus.ACTIVE.value, None, datetime(2099, 12, 31, tzinfo=UTC))
    assert _expiry_state(demo, _NOW) == (False, None, True)


def test_live_demo_reports_remaining_days() -> None:
    demo = _demo(DemoSiteStatus.ACTIVE.value, _NOW - timedelta(days=11), _NOW + timedelta(days=10))
    is_expired, expires_in, pending = _expiry_state(demo, _NOW)
    assert is_expired is False
    assert pending is False
    assert expires_in == 10


def test_past_expiry_is_expired() -> None:
    demo = _demo(DemoSiteStatus.ACTIVE.value, _NOW - timedelta(days=22), _NOW - timedelta(days=1))
    assert _expiry_state(demo, _NOW) == (True, None, False)


def test_naive_expires_at_is_treated_as_utc() -> None:
    # SQLite/MySQL can hand back a naive datetime; it must not crash the tz-aware comparison.
    demo = _demo(DemoSiteStatus.ACTIVE.value, _NOW - timedelta(days=22), datetime(2026, 9, 8, 12, 0, 0))
    assert _expiry_state(demo, _NOW)[0] is True


def test_slug_strips_background_suffix() -> None:
    # The montage background anchors on the same demo as the final video.
    assert _slug_from_key("videos/websites/chez-mimon.mp4") == "chez-mimon"
    assert _slug_from_key("videos/websites/chez-mimon-background.mp4") == "chez-mimon"
    assert _slug_from_key("images/websites/chez-mimon.jpg") == "chez-mimon"


def test_slug_is_none_for_non_deliverables() -> None:
    assert _slug_from_key("images/prospects/29/abc.jpg") is None
    assert _slug_from_key("uploads/manual/2026/09/abc.jpg") is None
    assert _slug_from_key("videos/presenter/7.mp4") is None


def test_classify_recognises_new_kinds() -> None:
    assert _classify("videos/websites/foo-background.mp4") == "website_background"
    assert _classify("videos/websites/foo.mp4") == "website_video"
    assert _classify("uploads/manual/2026/09/abc.jpg") == "manual"
