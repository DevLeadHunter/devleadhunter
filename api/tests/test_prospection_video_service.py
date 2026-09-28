"""The prospection video's shared life, for the site and the receptionist: render, publication, failures, watchdog."""

from __future__ import annotations

import asyncio
import gc
import io
import logging
import weakref
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

import services.prospection_video_service as prospection_module
from enums.demo_video_status import DemoVideoStatus
from models.ai_assistant import AiAssistant
from models.demo_site import DemoSite
from services import video_montage, video_pipeline
from services.ai_assistant.assistant_service import ai_assistant_service
from services.assistant_video_service import AssistantVideoService, assistant_video_service
from services.demo_video_service import DemoVideoService, demo_video_service
from services.prospection_video_service import (
    INTERRUPTED_MESSAGE,
    THUMBNAIL_UPLOAD_FAILED_MESSAGE,
    VIDEO_UPLOAD_FAILED_MESSAGE,
    CapturedSegment,
    ProspectionVideoService,
)
from services.r2_storage_service import r2_storage
from services.video_generation_watchdog import video_generation_watchdog
from services.video_pipeline import GENERATION_OVERRUN_MESSAGE, GenerationRuns, VideoGenerationError

_USER_ID = 1
_PROSPECT_ID = 42


class _FakeBucket:
    """The R2 bucket as the tests see it: uploads and deletions recorded, an upload failing for the keys told to."""

    def __init__(self) -> None:
        self.objects: set[str] = set()
        self.deleted: list[str] = []
        self.failing_keys: set[str] = set()

    async def upload_file_async(self, local_path: Path | str, key: str, content_type: str | None = None) -> str:
        if key in self.failing_keys:
            raise RuntimeError("R2 indisponible")
        assert Path(local_path).is_file()
        self.objects.add(key)
        return f"https://cdn/{key}"

    def delete_many(self, keys: list[str]) -> None:
        self.deleted.extend(keys)
        self.objects.difference_update(keys)


class _FakeClock:
    """A monotonic clock the tests move by hand."""

    def __init__(self) -> None:
        self.now = 10_000.0

    def __call__(self) -> float:
        return self.now


def _presenter() -> SimpleNamespace:
    return SimpleNamespace(
        duration_seconds=30.0, intro_seconds=5.0, outro_seconds=5.0, auto_generate=False, file_path="clip.mp4"
    )


async def _presenter_file(presenter: SimpleNamespace, work_dir: Path) -> Path:
    path = work_dir / "presenter.mp4"
    path.write_bytes(b"presenter")
    return path


async def _no_presenter_photo(db: Session, user_id: int, work_dir: Path) -> None:
    return None


async def _captured_segment(
    service: ProspectionVideoService[Any], subject: Any, middle_seconds: float, work_dir: Path
) -> CapturedSegment:
    recording_path = work_dir / "capture.webm"
    recording_path.write_bytes(b"capture")
    screenshot_path = work_dir / "top.png"
    screenshot_path.write_bytes(b"still")
    return CapturedSegment(recording_path=recording_path, start_seconds=1.5, screenshot_path=screenshot_path)


@pytest.fixture
def videos(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """The video services on the test database, with a fake bucket, capture and montage, and a clock to move."""
    bucket = _FakeBucket()
    clock = _FakeClock()
    montages: list[dict[str, Any]] = []
    reenqueued: list[tuple[int | None, int]] = []

    def compose(**kwargs: Any) -> None:
        montages.append(kwargs)
        Path(kwargs["output_video"]).write_bytes(b"video")
        Path(kwargs["output_thumbnail"]).write_bytes(b"thumbnail")

    monkeypatch.setattr("core.database.SessionLocal", sessionmaker(bind=engine))
    monkeypatch.setattr(video_pipeline, "generation_runs", GenerationRuns(clock=clock))
    monkeypatch.setattr(video_pipeline, "generation_semaphore", asyncio.Semaphore(1))
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user",
        lambda *args, **kwargs: _presenter(),
    )
    monkeypatch.setattr(video_pipeline, "resolve_presenter_file", _presenter_file)
    monkeypatch.setattr(video_pipeline, "resolve_presenter_photo", _no_presenter_photo)
    monkeypatch.setattr(video_pipeline, "resolve_first_name", lambda db, prospect_id: "Claire")
    monkeypatch.setattr(video_pipeline, "available_memory_mb", lambda: None)
    monkeypatch.setattr(video_montage, "compose_final", compose)
    monkeypatch.setattr(DemoVideoService, "_capture_middle", _captured_segment)
    monkeypatch.setattr(AssistantVideoService, "_capture_middle", _captured_segment)
    monkeypatch.setattr(r2_storage, "upload_file_async", bucket.upload_file_async)
    monkeypatch.setattr(r2_storage, "delete_many", bucket.delete_many)
    monkeypatch.setattr(
        prospection_module,
        "reenqueue_campaigns_after_video_ready",
        lambda db, prospect_id, user_id: reenqueued.append((prospect_id, user_id)),
    )
    yield SimpleNamespace(bucket=bucket, clock=clock, montages=montages, reenqueued=reenqueued)


def _site(db: Session, slug: str = "garage-martin", video_status: str | None = None) -> DemoSite:
    site = DemoSite(
        user_id=_USER_ID,
        prospect_id=_PROSPECT_ID,
        slug=slug,
        business_name="Garage Martin",
        status="active",
        demo_url=f"https://demo.dibodev.fr/{slug}",
        expires_at=datetime.now(UTC) + timedelta(days=21),
        video_status=video_status,
    )
    db.add(site)
    db.commit()
    return site


def _assistant(db: Session, video_status: str | None = None) -> AiAssistant:
    assistant = ai_assistant_service.create(
        db,
        user_id=_USER_ID,
        business_name="Toitures Morel",
        prospect_id=_PROSPECT_ID,
        country="FR",
        use_brand_color=False,
    )
    assistant.video_status = video_status
    db.commit()
    return assistant


_SERVICES: dict[str, tuple[ProspectionVideoService[Any], Any]] = {
    "site": (demo_video_service, _site),
    "assistant": (assistant_video_service, _assistant),
}


def _generate(service: ProspectionVideoService[Any], db: Session, subject: Any) -> None:
    """Request a generation and wait until its task ends, as the dashboard's polling would."""

    async def request_and_wait() -> None:
        service.request_generation(db, subject, user_id=_USER_ID)
        while video_pipeline.generation_runs.is_in_progress((service.kind, subject.id)):
            await asyncio.sleep(0.01)

    asyncio.run(asyncio.wait_for(request_and_wait(), timeout=10))
    db.expire_all()


def _is_recent_naive_utc(moment: datetime | None) -> bool:
    now = datetime.now(UTC).replace(tzinfo=None)
    return moment is not None and moment.tzinfo is None and now - timedelta(minutes=1) <= moment <= now


@pytest.mark.parametrize("kind", ["site", "assistant"])
def test_both_videos_go_through_the_same_generation(videos: SimpleNamespace, db: Session, kind: str) -> None:
    service, make_subject = _SERVICES[kind]
    subject = make_subject(db)

    _generate(service, db, subject)

    assert subject.video_status == DemoVideoStatus.READY.value
    assert subject.video_error is None
    assert _is_recent_naive_utc(subject.video_generated_at)
    assert videos.bucket.objects == {service._video_key(subject.slug), service._thumbnail_key(subject.slug)}
    [montage] = videos.montages
    assert (montage["thumbnail_label"], montage["pip_corner"]) == (service.thumbnail_label, service.pip_corner)
    assert (montage["scroll_offset"], montage["scroll_seconds"], montage["first_name"]) == (1.5, 20.0, "Claire")
    assert videos.reenqueued == [(_PROSPECT_ID, _USER_ID)]


@pytest.mark.parametrize("kind", ["site", "assistant"])
def test_a_failed_capture_ends_failed_with_its_reason(
    videos: SimpleNamespace, db: Session, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    service, make_subject = _SERVICES[kind]

    async def failing_capture(*args: Any) -> CapturedSegment:
        raise VideoGenerationError("L'exemple ne s'est pas joué pendant la capture.")

    monkeypatch.setattr(type(service), "_capture_middle", failing_capture)
    subject = make_subject(db)

    _generate(service, db, subject)

    assert (subject.video_status, subject.video_error) == (
        DemoVideoStatus.FAILED.value,
        "L'exemple ne s'est pas joué pendant la capture.",
    )
    assert videos.bucket.objects == set()
    assert videos.reenqueued == []


def test_an_error_right_after_the_render_starts_still_ends_failed(
    videos: SimpleNamespace, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolving the first name used to run outside the try: its failure left the video « generating » forever."""

    def broken_first_name(db: Session, prospect_id: int | None) -> str:
        raise RuntimeError("base injoignable")

    monkeypatch.setattr(video_pipeline, "resolve_first_name", broken_first_name)
    site = _site(db)

    _generate(demo_video_service, db, site)

    assert site.video_status == DemoVideoStatus.FAILED.value
    assert site.video_error == "Erreur inattendue : base injoignable"


@pytest.mark.parametrize("kind", ["site", "assistant"])
def test_a_failing_thumbnail_upload_leaves_no_orphan_video(videos: SimpleNamespace, db: Session, kind: str) -> None:
    service, make_subject = _SERVICES[kind]
    subject = make_subject(db)
    video_key, thumbnail_key = service._video_key(subject.slug), service._thumbnail_key(subject.slug)
    videos.bucket.failing_keys = {thumbnail_key}

    _generate(service, db, subject)

    assert (subject.video_status, subject.video_error) == (
        DemoVideoStatus.FAILED.value,
        THUMBNAIL_UPLOAD_FAILED_MESSAGE,
    )
    assert videos.bucket.objects == set()
    assert set(videos.bucket.deleted) == {video_key, thumbnail_key}


def test_a_failing_video_upload_ends_failed_without_a_thumbnail(videos: SimpleNamespace, db: Session) -> None:
    assistant = _assistant(db)
    videos.bucket.failing_keys = {assistant_video_service._video_key(assistant.slug)}

    _generate(assistant_video_service, db, assistant)

    assert (assistant.video_status, assistant.video_error) == (
        DemoVideoStatus.FAILED.value,
        VIDEO_UPLOAD_FAILED_MESSAGE,
    )
    assert videos.bucket.objects == set()


def test_a_video_reset_while_it_renders_is_never_published(
    videos: SimpleNamespace, db: Session, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An expiry or a deletion during the render must not bring the video back online."""
    assistant = _assistant(db)

    async def capture_while_the_demo_expires(*args: Any) -> CapturedSegment:
        other_session = sessionmaker(bind=engine)()
        other_session.get(AiAssistant, assistant.id).video_status = None
        other_session.commit()
        other_session.close()
        return await _captured_segment(*args)

    monkeypatch.setattr(AssistantVideoService, "_capture_middle", capture_while_the_demo_expires)

    _generate(assistant_video_service, db, assistant)

    assert assistant.video_status is None
    assert videos.bucket.objects == set()


def test_a_new_generation_is_refused_while_one_is_under_way(videos: SimpleNamespace, db: Session) -> None:
    """The dashboard can show « ready » (a desktop upload) while a server render still runs: both would publish."""
    site = _site(db, video_status=DemoVideoStatus.READY.value)

    async def request_twice() -> None:
        video_pipeline.generation_runs.start(("site", site.id), asyncio.sleep(3600))
        with pytest.raises(ValueError, match="déjà en cours"):
            demo_video_service.request_generation(db, site, user_id=_USER_ID)
        video_pipeline.generation_runs.cancel(("site", site.id))

    asyncio.run(request_twice())


@pytest.mark.parametrize("kind", ["site", "assistant"])
def test_the_desktop_video_is_published_and_dated_in_naive_utc(videos: SimpleNamespace, db: Session, kind: str) -> None:
    service, make_subject = _SERVICES[kind]
    subject = make_subject(db)

    asyncio.run(service.store_desktop_video(db, subject, _desktop_archive()))

    assert subject.video_status == DemoVideoStatus.READY.value
    assert _is_recent_naive_utc(subject.video_generated_at)
    assert videos.bucket.objects == {service._video_key(subject.slug), service._thumbnail_key(subject.slug)}
    assert videos.reenqueued == [(_PROSPECT_ID, _USER_ID)]


@pytest.mark.parametrize("kind", ["site", "assistant"])
def test_a_desktop_video_whose_thumbnail_fails_is_taken_back_down(
    videos: SimpleNamespace, db: Session, kind: str
) -> None:
    service, make_subject = _SERVICES[kind]
    subject = make_subject(db, video_status=DemoVideoStatus.READY.value)
    videos.bucket.failing_keys = {service._thumbnail_key(subject.slug)}

    with pytest.raises(VideoGenerationError):
        asyncio.run(service.store_desktop_video(db, subject, _desktop_archive()))

    db.expire_all()
    assert (subject.video_status, subject.video_error) == (
        DemoVideoStatus.FAILED.value,
        THUMBNAIL_UPLOAD_FAILED_MESSAGE,
    )
    assert videos.bucket.objects == set()
    assert service._video_key(subject.slug) in videos.bucket.deleted


def test_a_desktop_archive_without_its_thumbnail_changes_nothing(videos: SimpleNamespace, db: Session) -> None:
    site = _site(db, video_status=DemoVideoStatus.READY.value)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("video.mp4", b"video")
    archive.seek(0)

    with pytest.raises(ValueError, match="Archive vidéo invalide"):
        asyncio.run(demo_video_service.store_desktop_video(db, site, archive))

    assert site.video_status == DemoVideoStatus.READY.value
    assert videos.bucket.objects == set()


def _desktop_archive() -> io.BytesIO:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("video.mp4", b"video")
        bundle.writestr("thumbnail.jpg", b"thumbnail")
    archive.seek(0)
    return archive


def test_a_generation_is_held_until_it_ends() -> None:
    """asyncio keeps only a weak reference to a task: a render waiting on an unreferenced future could be collected."""
    runs = GenerationRuns()

    async def wait_forever() -> None:
        await asyncio.get_running_loop().create_future()

    async def scenario() -> None:
        task_reference = weakref.ref(runs.start(("site", 1), wait_forever()))
        await asyncio.sleep(0)
        gc.collect()
        task = task_reference()
        assert task is not None and not task.done()
        runs.cancel(("site", 1))
        await asyncio.sleep(0.01)
        assert not runs.is_in_progress(("site", 1))

    asyncio.run(scenario())


def test_a_generation_that_dies_is_logged_and_forgotten(caplog: pytest.LogCaptureFixture) -> None:
    runs = GenerationRuns()

    async def crash() -> None:
        raise RuntimeError("boom")

    async def scenario() -> None:
        runs.start(("assistant", 7), crash())
        await asyncio.sleep(0.01)

    with caplog.at_level(logging.ERROR, logger="services.video_pipeline"):
        asyncio.run(scenario())

    assert not runs.is_in_progress(("assistant", 7))
    [record] = [record for record in caplog.records if "died" in record.getMessage()]
    assert record.exc_info is not None and str(record.exc_info[1]) == "boom"


def test_the_watchdog_fails_orphans_and_overruns_but_spares_live_renders(videos: SimpleNamespace, db: Session) -> None:
    orphan = _site(db, slug="orphan", video_status=DemoVideoStatus.GENERATING.value)
    recent = _site(db, slug="recent", video_status=DemoVideoStatus.GENERATING.value)
    queued = _assistant(db, video_status=DemoVideoStatus.PENDING.value)
    stuck = _assistant(db, video_status=DemoVideoStatus.GENERATING.value)
    runs = video_pipeline.generation_runs
    maximum = video_pipeline.MAXIMUM_GENERATION_SECONDS

    async def scenario() -> tuple[int, bool, bool]:
        waiting = asyncio.Event()
        stuck_task = runs.start(("assistant", stuck.id), waiting.wait())
        recent_task = runs.start(("site", recent.id), waiting.wait())
        runs.start(("assistant", queued.id), waiting.wait())
        runs.mark_rendering(("assistant", stuck.id))
        videos.clock.now += maximum - 60
        runs.mark_rendering(("site", recent.id))
        videos.clock.now += 120

        failed_count = video_generation_watchdog.check(db)
        await asyncio.sleep(0.01)
        was_stuck_cancelled, was_recent_cancelled = stuck_task.cancelled(), recent_task.cancelled()
        waiting.set()
        await asyncio.sleep(0.01)
        return failed_count, was_stuck_cancelled, was_recent_cancelled

    failed_count, was_stuck_cancelled, was_recent_cancelled = asyncio.run(scenario())

    db.expire_all()
    assert failed_count == 2
    assert (orphan.video_status, orphan.video_error) == (DemoVideoStatus.FAILED.value, INTERRUPTED_MESSAGE)
    assert (stuck.video_status, stuck.video_error) == (DemoVideoStatus.FAILED.value, GENERATION_OVERRUN_MESSAGE)
    assert was_stuck_cancelled and not was_recent_cancelled
    assert recent.video_status == DemoVideoStatus.GENERATING.value
    assert queued.video_status == DemoVideoStatus.PENDING.value


def test_clearing_a_video_stops_its_generation(videos: SimpleNamespace, db: Session) -> None:
    assistant = _assistant(db, video_status=DemoVideoStatus.GENERATING.value)

    async def scenario() -> bool:
        task = video_pipeline.generation_runs.start(("assistant", assistant.id), asyncio.sleep(3600))
        assistant_video_service.clear_video(db, assistant)
        await asyncio.sleep(0.01)
        return task.cancelled()

    assert asyncio.run(scenario())
    assert (assistant.video_status, assistant.video_generated_at) == (None, None)
    assert set(videos.bucket.deleted) == {
        assistant_video_service._video_key(assistant.slug),
        assistant_video_service._thumbnail_key(assistant.slug),
    }
