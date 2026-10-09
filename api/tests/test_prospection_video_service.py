"""The prospection video's shared life, for the site and the receptionist: checks, publication, reset, older clips."""

from __future__ import annotations

import asyncio
import io
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.orm import Session

import services.prospection_video_service as prospection_module
from enums.ai_assistant_status import AiAssistantStatus
from enums.demo_video_status import DemoVideoStatus
from models.ai_assistant import AiAssistant
from models.demo_site import DemoSite
from models.presenter_video import PresenterVideo
from services import video_pipeline
from services.ai_assistant.assistant_service import ai_assistant_service
from services.assistant_video_service import assistant_video_service
from services.demo_video_service import demo_video_service
from services.prospection_video_service import (
    ALREADY_BUILDING_MESSAGE,
    THUMBNAIL_UPLOAD_FAILED_MESSAGE,
    VIDEO_UPLOAD_FAILED_MESSAGE,
    ProspectionVideoService,
)
from services.r2_storage_service import r2_storage
from services.video_pipeline import DesktopVideoBuilds, VideoGenerationError

_USER_ID = 1
_PROSPECT_ID = 42
_CLIP_CHOSEN_AT = datetime(2026, 10, 9, 8, 0)


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


def _presenter(*, duration: float = 30.0, intro: float = 5.0, outro: float = 5.0) -> SimpleNamespace:
    return SimpleNamespace(
        duration_seconds=duration, intro_seconds=intro, outro_seconds=outro, auto_generate=False, in_use_since=None
    )


@pytest.fixture
def videos(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """The video services with a fake bucket, a presenter clip per module and no build under way."""
    bucket = _FakeBucket()
    reenqueued: list[tuple[int | None, int]] = []
    presenter_modules: list[str] = []

    def presenter_of(db: Session, user_id: int, module: str = "websites") -> SimpleNamespace:
        presenter_modules.append(module)
        return _presenter()

    monkeypatch.setattr("services.presenter_video_service.presenter_video_service.get_for_user", presenter_of)
    monkeypatch.setattr(video_pipeline, "desktop_video_builds", DesktopVideoBuilds())
    monkeypatch.setattr(r2_storage, "upload_file_async", bucket.upload_file_async)
    monkeypatch.setattr(r2_storage, "delete_many", bucket.delete_many)
    monkeypatch.setattr(
        prospection_module,
        "reenqueue_campaigns_after_video_ready",
        lambda db, prospect_id, user_id: reenqueued.append((prospect_id, user_id)),
    )
    yield SimpleNamespace(bucket=bucket, reenqueued=reenqueued, presenter_modules=presenter_modules)


def _site(db: Session, slug: str = "garage-martin", video_status: str | None = None) -> DemoSite:
    site = DemoSite(
        user_id=_USER_ID,
        prospect_id=_PROSPECT_ID,
        slug=slug,
        business_name="Garage Martin",
        status="active",
        demo_url=f"https://demo.dibodev.fr/{slug}",
        storyblok_space_id=287465,
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


def _is_recent_naive_utc(moment: datetime | None) -> bool:
    now = datetime.now(UTC).replace(tzinfo=None)
    return moment is not None and moment.tzinfo is None and now - timedelta(minutes=1) <= moment <= now


def _desktop_archive() -> io.BytesIO:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("video.mp4", b"video")
        bundle.writestr("thumbnail.jpg", b"thumbnail")
    archive.seek(0)
    return archive


@pytest.mark.parametrize("kind", ["site", "assistant"])
def test_a_video_is_asked_with_the_presenter_clip_of_its_module(
    videos: SimpleNamespace, db: Session, kind: str
) -> None:
    service, make_subject = _SERVICES[kind]
    subject = make_subject(db)
    videos.presenter_modules.clear()

    service.ensure_generation_can_start(db, subject, _USER_ID)

    assert videos.presenter_modules == [service.presenter_module]


def test_a_site_that_cannot_be_filmed_is_refused(videos: SimpleNamespace, db: Session) -> None:
    expired = _site(db, slug="expire")
    expired.status = "expired"
    offline = _site(db, slug="hors-ligne")
    offline.demo_url = None
    db.commit()

    with pytest.raises(ValueError, match="site démo actif"):
        demo_video_service.ensure_generation_can_start(db, expired, _USER_ID)
    with pytest.raises(ValueError, match="pas d'URL publique"):
        demo_video_service.ensure_generation_can_start(db, offline, _USER_ID)


def test_a_receptionist_that_is_not_active_is_refused(videos: SimpleNamespace, db: Session) -> None:
    assistant = _assistant(db)
    assistant.status = AiAssistantStatus.EXPIRED.value

    with pytest.raises(ValueError, match="réceptionniste active"):
        assistant_video_service.ensure_generation_can_start(db, assistant, _USER_ID)


@pytest.mark.parametrize("kind", ["site", "assistant"])
def test_a_video_is_refused_without_a_presenter_clip(
    videos: SimpleNamespace, db: Session, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    service, make_subject = _SERVICES[kind]
    subject = make_subject(db)
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user", lambda *args, **kwargs: None
    )

    with pytest.raises(ValueError, match="clip de présentation"):
        service.ensure_generation_can_start(db, subject, _USER_ID)


@pytest.mark.parametrize("kind", ["site", "assistant"])
def test_a_clip_leaving_too_little_for_the_middle_is_refused(
    videos: SimpleNamespace, db: Session, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    service, make_subject = _SERVICES[kind]
    subject = make_subject(db)
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user",
        lambda *args, **kwargs: _presenter(duration=10.0, intro=5.0, outro=4.0),
    )

    with pytest.raises(ValueError, match="trop longues"):
        service.ensure_generation_can_start(db, subject, _USER_ID)


@pytest.mark.parametrize("kind", ["site", "assistant"])
def test_a_video_the_pc_is_building_is_refused(videos: SimpleNamespace, db: Session, kind: str) -> None:
    service, make_subject = _SERVICES[kind]
    subject = make_subject(db, video_status=DemoVideoStatus.READY.value)
    subject.video_desktop_requested_at = datetime(2026, 10, 9, 9, 0)
    service.mark_desktop_build_started(subject)

    with pytest.raises(ValueError, match=ALREADY_BUILDING_MESSAGE):
        service.ensure_generation_can_start(db, subject, _USER_ID)


def test_a_site_without_its_storyblok_space_can_be_asked_but_is_not_filmed_yet(
    videos: SimpleNamespace, db: Session
) -> None:
    site = _site(db)
    site.storyblok_space_id = None
    db.commit()

    demo_video_service.ensure_generation_can_start(db, site, _USER_ID)

    assert demo_video_service.is_ready_to_film(site) is False
    assert demo_video_service.is_waiting_for_storyblok_space(site) is False
    site.video_desktop_requested_at = datetime(2026, 10, 9, 9, 0)
    assert demo_video_service.is_waiting_for_storyblok_space(site) is True


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


def test_a_desktop_video_whose_upload_fails_ends_failed_without_a_thumbnail(
    videos: SimpleNamespace, db: Session
) -> None:
    assistant = _assistant(db)
    videos.bucket.failing_keys = {assistant_video_service._video_key(assistant.slug)}

    with pytest.raises(VideoGenerationError):
        asyncio.run(assistant_video_service.store_desktop_video(db, assistant, _desktop_archive()))

    db.expire_all()
    assert (assistant.video_status, assistant.video_error) == (
        DemoVideoStatus.FAILED.value,
        VIDEO_UPLOAD_FAILED_MESSAGE,
    )
    assert videos.bucket.objects == set()
    assert videos.reenqueued == []


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


def test_clearing_a_video_deletes_its_files_and_resets_it(videos: SimpleNamespace, db: Session) -> None:
    assistant = _assistant(db, video_status=DemoVideoStatus.READY.value)
    assistant.video_generated_at = datetime(2026, 10, 1, 9, 0)

    assistant_video_service.clear_video(db, assistant)

    assert (assistant.video_status, assistant.video_generated_at) == (None, None)
    assert set(videos.bucket.deleted) == {
        assistant_video_service._video_key(assistant.slug),
        assistant_video_service._thumbnail_key(assistant.slug),
    }


def _clip_in_use(db: Session, module: str, in_use_since: datetime | None) -> PresenterVideo:
    take = PresenterVideo(
        user_id=_USER_ID,
        module=module,
        is_active=True,
        file_path=f"videos/presenter/{module}.mp4",
        in_use_since=in_use_since,
    )
    db.add(take)
    db.commit()
    return take


def test_the_clip_in_use_is_dated_per_module(db: Session) -> None:
    _clip_in_use(db, "websites", _CLIP_CHOSEN_AT)
    _clip_in_use(db, "ai-assistant", _CLIP_CHOSEN_AT - timedelta(days=3))

    assert demo_video_service.clip_in_use_since(db, _USER_ID) == _CLIP_CHOSEN_AT
    assert assistant_video_service.clip_in_use_since(db, _USER_ID) == _CLIP_CHOSEN_AT - timedelta(days=3)
    assert demo_video_service.clip_in_use_since(db, _USER_ID + 1) is None


def test_a_video_published_before_the_clip_in_use_was_chosen_is_made_with_an_older_clip(db: Session) -> None:
    older = _site(db, slug="ancien", video_status=DemoVideoStatus.READY.value)
    older.video_generated_at = _CLIP_CHOSEN_AT - timedelta(minutes=1)
    newer = _site(db, slug="recent", video_status=DemoVideoStatus.READY.value)
    newer.video_generated_at = _CLIP_CHOSEN_AT + timedelta(minutes=1)
    failed = _site(db, slug="echec", video_status=DemoVideoStatus.FAILED.value)
    failed.video_generated_at = _CLIP_CHOSEN_AT - timedelta(days=1)

    assert demo_video_service.is_made_with_older_clip(older, _CLIP_CHOSEN_AT) is True
    assert demo_video_service.is_made_with_older_clip(newer, _CLIP_CHOSEN_AT) is False
    assert demo_video_service.is_made_with_older_clip(failed, _CLIP_CHOSEN_AT) is False
    assert demo_video_service.is_made_with_older_clip(older, None) is False


def test_the_dashboard_shows_a_video_made_with_an_older_clip(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from api.v1.routes.ai_assistants import get_assistant
    from api.v1.routes.demo_sites import get_demo_site

    monkeypatch.setattr(r2_storage, "public_url", lambda key: f"https://cdn/{key}")
    _clip_in_use(db, "websites", _CLIP_CHOSEN_AT)
    _clip_in_use(db, "ai-assistant", _CLIP_CHOSEN_AT)
    site = _site(db, video_status=DemoVideoStatus.READY.value)
    site.video_generated_at = _CLIP_CHOSEN_AT - timedelta(hours=1)
    assistant = _assistant(db, video_status=DemoVideoStatus.READY.value)
    assistant.video_generated_at = _CLIP_CHOSEN_AT + timedelta(hours=1)
    db.commit()
    owner = SimpleNamespace(id=_USER_ID)

    site_response = asyncio.run(get_demo_site(site.id, owner, db))
    assistant_response = asyncio.run(get_assistant(assistant.id, owner, db))

    assert site_response.is_video_made_with_older_clip is True
    assert assistant_response.is_video_made_with_older_clip is False
