"""Reliability guards for demo-video generation: startup reconciliation + memory floor."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from enums.demo_video_status import DemoVideoStatus
from services import video_pipeline
from services.demo_video_service import DemoVideoGenerationError, DemoVideoService


class _FakeQuery:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def filter(self, *args: object, **kwargs: object) -> _FakeQuery:
        return self

    def all(self) -> list[SimpleNamespace]:
        return self._rows


class _FakeDB:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows
        self.committed = False

    def query(self, *args: object, **kwargs: object) -> _FakeQuery:
        return _FakeQuery(self._rows)

    def commit(self) -> None:
        self.committed = True


def _site(site_id: int, video_status: str) -> SimpleNamespace:
    return SimpleNamespace(id=site_id, slug=f"site-{site_id}", video_status=video_status, video_error=None)


def test_reconcile_marks_orphaned_generations_failed() -> None:
    rows = [
        _site(1, DemoVideoStatus.GENERATING.value),
        _site(2, DemoVideoStatus.PENDING.value),
    ]
    db = _FakeDB(rows)

    count = DemoVideoService().reconcile_orphaned(db)

    assert count == 2
    assert db.committed is True
    for site in rows:
        assert site.video_status == DemoVideoStatus.FAILED.value
        assert site.video_error  # a user-facing reason is set


def test_reconcile_without_orphans_does_not_commit() -> None:
    db = _FakeDB([])

    count = DemoVideoService().reconcile_orphaned(db)

    assert count == 0
    assert db.committed is False


def test_capture_memory_guard_refuses_when_low(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_pipeline, "available_memory_mb", lambda: 500.0)
    with pytest.raises(DemoVideoGenerationError):
        DemoVideoService._guard_capture_memory()


def test_capture_memory_guard_allows_when_high(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_pipeline, "available_memory_mb", lambda: 3000.0)
    DemoVideoService._guard_capture_memory()  # must not raise


def test_capture_memory_guard_allows_when_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    # None = /proc/meminfo unreadable (e.g. non-Linux) → never block generation.
    monkeypatch.setattr(video_pipeline, "available_memory_mb", lambda: None)
    DemoVideoService._guard_capture_memory()  # must not raise


def test_montage_memory_guard_refuses_when_low(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(video_pipeline, "available_memory_mb", lambda: 300.0)
    with pytest.raises(DemoVideoGenerationError):
        DemoVideoService._guard_montage_memory()


def test_montage_memory_guard_allows_with_headroom(monkeypatch: pytest.MonkeyPatch) -> None:
    # Lower floor than capture: 700 Mo is enough to montage but not to capture.
    monkeypatch.setattr(video_pipeline, "available_memory_mb", lambda: 700.0)
    DemoVideoService._guard_montage_memory()  # must not raise
