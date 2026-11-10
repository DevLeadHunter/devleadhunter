"""The prospection video's shared life, as the site lives it: checks, publication, reset, older clips."""

from __future__ import annotations

import asyncio
import io
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

import services.prospection_video_service as prospection_module
from enums.demo_video_status import DemoVideoStatus
from models.demo_site import DemoSite
from models.presenter_video import PresenterVideo
from services import video_pipeline
from services.demo_video_service import demo_video_service
from services.prospection_video_service import (
    ALREADY_BUILDING_MESSAGE,
    THUMBNAIL_UPLOAD_FAILED_MESSAGE,
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
    """The video service with a fake bucket, a presenter clip per module and no build under way."""
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


def test_a_video_is_asked_with_the_presenter_clip_of_its_module(videos: SimpleNamespace, db: Session) -> None:
    site = _site(db)
    videos.presenter_modules.clear()

    demo_video_service.ensure_generation_can_start(db, site, _USER_ID)

    assert videos.presenter_modules == [demo_video_service.presenter_module]


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


def test_a_video_is_refused_without_a_presenter_clip(
    videos: SimpleNamespace, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = _site(db)
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user", lambda *args, **kwargs: None
    )

    with pytest.raises(ValueError, match="clip de présentation"):
        demo_video_service.ensure_generation_can_start(db, site, _USER_ID)


def test_a_clip_leaving_too_little_for_the_middle_is_refused(
    videos: SimpleNamespace, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    site = _site(db)
    monkeypatch.setattr(
        "services.presenter_video_service.presenter_video_service.get_for_user",
        lambda *args, **kwargs: _presenter(duration=10.0, intro=5.0, outro=4.0),
    )

    with pytest.raises(ValueError, match="trop longues"):
        demo_video_service.ensure_generation_can_start(db, site, _USER_ID)


def test_a_video_the_pc_is_building_is_refused(videos: SimpleNamespace, db: Session) -> None:
    site = _site(db, video_status=DemoVideoStatus.READY.value)
    site.video_desktop_requested_at = datetime(2026, 10, 9, 9, 0)
    demo_video_service.mark_desktop_build_started(site)

    with pytest.raises(ValueError, match=ALREADY_BUILDING_MESSAGE):
        demo_video_service.ensure_generation_can_start(db, site, _USER_ID)


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


def test_the_desktop_video_is_published_and_dated_in_naive_utc(videos: SimpleNamespace, db: Session) -> None:
    site = _site(db)

    asyncio.run(demo_video_service.store_desktop_video(db, site, _desktop_archive()))

    assert site.video_status == DemoVideoStatus.READY.value
    assert _is_recent_naive_utc(site.video_generated_at)
    assert videos.bucket.objects == {
        demo_video_service._video_key(site.slug),
        demo_video_service._thumbnail_key(site.slug),
    }
    assert videos.reenqueued == [(_PROSPECT_ID, _USER_ID)]


def test_a_desktop_video_whose_thumbnail_fails_is_taken_back_down(videos: SimpleNamespace, db: Session) -> None:
    site = _site(db, video_status=DemoVideoStatus.READY.value)
    videos.bucket.failing_keys = {demo_video_service._thumbnail_key(site.slug)}

    with pytest.raises(VideoGenerationError):
        asyncio.run(demo_video_service.store_desktop_video(db, site, _desktop_archive()))

    db.expire_all()
    assert (site.video_status, site.video_error) == (
        DemoVideoStatus.FAILED.value,
        THUMBNAIL_UPLOAD_FAILED_MESSAGE,
    )
    assert videos.bucket.objects == set()
    assert demo_video_service._video_key(site.slug) in videos.bucket.deleted


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
    from api.v1.routes.demo_sites import get_demo_site

    monkeypatch.setattr(r2_storage, "public_url", lambda key: f"https://cdn/{key}")
    _clip_in_use(db, "websites", _CLIP_CHOSEN_AT)
    site = _site(db, video_status=DemoVideoStatus.READY.value)
    site.video_generated_at = _CLIP_CHOSEN_AT - timedelta(hours=1)
    db.commit()
    owner = SimpleNamespace(id=_USER_ID)

    site_response = asyncio.run(get_demo_site(site.id, owner, db))

    assert site_response.is_video_made_with_older_clip is True
