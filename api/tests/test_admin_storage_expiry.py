"""The storage page anchors a demo deliverable's expiry on its demo's real lifecycle.

Historically the page flagged any video/thumbnail older than a fixed 14 days — which, once the demo TTL
moved to 21 days and started counting from the first send (not generation), wrongly flagged files still
tied to live or not-yet-sent demos. Expiry is now read from the demo row itself (``expire_due_sites``
purges exactly when ``expires_at`` passes), so the page and the cleanup agree.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy.orm import Session

from api.v1.routes.admin_storage import _classify, _expired_deliverable_keys, _expiry_state, _slug_from_key
from enums.ai_assistant_status import AiAssistantStatus
from enums.demo_site_status import DemoSiteStatus
from enums.storage_object_kind import StorageObjectKind
from services.ai_assistant.assistant_service import ai_assistant_service

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


def test_every_key_prefix_maps_to_one_storage_kind() -> None:
    kind_by_sample_key = {
        "videos/websites/foo.mp4": StorageObjectKind.WEBSITE_VIDEO,
        "images/websites/foo.jpg": StorageObjectKind.WEBSITE_THUMBNAIL,
        "videos/websites/foo-background.mp4": StorageObjectKind.WEBSITE_BACKGROUND,
        "videos/assistant/foo.mp4": StorageObjectKind.ASSISTANT_VIDEO,
        "images/assistant/foo.jpg": StorageObjectKind.ASSISTANT_THUMBNAIL,
        "videos/presenter/7.mp4": StorageObjectKind.PRESENTER,
        "images/support/2026/09/abc.png": StorageObjectKind.SUPPORT,
        "images/prospects/29/abc.jpg": StorageObjectKind.PROSPECT_PHOTO,
        "images/assistant-photos/2026/09/abc.jpg": StorageObjectKind.ASSISTANT_PHOTO,
        "documents/assistant/12/abc.pdf": StorageObjectKind.ASSISTANT_DOCUMENT,
        "images/assistant-avatars/12/abc.webp": StorageObjectKind.ASSISTANT_AVATAR,
        "uploads/manual/2026/09/abc.jpg": StorageObjectKind.MANUAL,
        "misc/readme.txt": StorageObjectKind.OTHER,
    }

    assert {key: _classify(key) for key in kind_by_sample_key} == kind_by_sample_key
    assert set(kind_by_sample_key.values()) == set(StorageObjectKind)


def test_the_receptionist_files_have_their_own_kinds_and_slug() -> None:
    assert _classify("videos/assistant/toitures-morel.mp4") == "assistant_video"
    assert _classify("images/assistant/toitures-morel.jpg") == "assistant_thumbnail"
    # A visitor's quote photo shares the start of the thumbnail prefix, not its kind.
    assert _classify("images/assistant-photos/2026/09/abc.jpg") == "assistant_photo"
    assert _slug_from_key("videos/assistant/toitures-morel.mp4") == "toitures-morel"
    assert _slug_from_key("images/assistant/toitures-morel.jpg") == "toitures-morel"
    assert _slug_from_key("images/assistant-photos/2026/09/abc.jpg") is None


def test_a_receptionist_video_expires_with_its_demo_and_a_deleted_one_is_a_leftover(db: Session) -> None:
    """Same rule as the site's: live or unsent demo kept, expired or deleted demo flagged for the purge."""
    live, expired, deleted = (
        ai_assistant_service.create(
            db, user_id=1, business_name=name, prospect_id=prospect_id, country="FR", use_brand_color=False
        )
        for prospect_id, name in ((1, "Toitures Morel"), (2, "Garage Martin"), (3, "Cabinet Meyer"))
    )
    expired.status = AiAssistantStatus.EXPIRED.value
    expired.demo_link_sent_at = _NOW - timedelta(days=30)
    expired.expires_at = _NOW - timedelta(days=9)
    deleted.deleted_at = _NOW
    db.commit()
    objects = [{"key": f"videos/assistant/{assistant.slug}.mp4"} for assistant in (live, expired, deleted)] + [
        {"key": f"images/assistant/{expired.slug}.jpg"},
        {"key": "images/assistant-photos/2026/09/abc.jpg"},
    ]

    stale = _expired_deliverable_keys(db, objects, _NOW)

    assert sorted(stale) == sorted(
        [
            f"videos/assistant/{expired.slug}.mp4",
            f"images/assistant/{expired.slug}.jpg",
            f"videos/assistant/{deleted.slug}.mp4",
        ]
    )
