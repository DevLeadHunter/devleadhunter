"""
Presenter takes: a new recording never replaces an older take, one take per module is in use, and the example
video of a take follows its cut points.

The database is an in-memory SQLite; ffmpeg and the storage are replaced by fakes, and the routes are called directly.
"""

import asyncio
import io
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.datastructures import Headers

import api.v1.routes.settings as routes
import services.presenter_video_service as presenter_module
from models.presenter_video import PresenterVideo
from models.user import User
from services.presenter_video_service import PresenterTakeInUseError, presenter_video_service
from services.r2_storage_service import r2_storage

_OWNER = SimpleNamespace(id=7)
_STRANGER = SimpleNamespace(id=8)
_EXAMPLE_SITE_ID = 12


class _FakeStorage:
    """The objects written and deleted, instead of R2."""

    def __init__(self) -> None:
        self.uploaded: list[str] = []
        self.deleted: list[str] = []


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine)()
    session.add(User(id=_OWNER.id, name="Dibodev", email="operateur@dibodev.fr", hashed_password="x"))
    session.add(User(id=_STRANGER.id, name="Autre", email="autre@exemple.fr", hashed_password="x"))
    session.commit()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def storage(monkeypatch: pytest.MonkeyPatch) -> _FakeStorage:
    fake = _FakeStorage()

    async def upload_file(local_path: Path, key: str, content_type: str | None = None) -> str:
        fake.uploaded.append(key)
        return key

    async def upload_bytes(key: str, data: bytes, content_type: str | None = None) -> str:
        fake.uploaded.append(key)
        return key

    monkeypatch.setattr(r2_storage, "upload_file_async", upload_file)
    monkeypatch.setattr(r2_storage, "upload_bytes_async", upload_bytes)
    monkeypatch.setattr(r2_storage, "delete", fake.deleted.append)
    return fake


@pytest.fixture(autouse=True)
def instant_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every imported clip lasts 30 s and normalises at once."""

    async def probe(file_path: str) -> float:
        return 30.0

    async def normalize(self: object, source_path: Path, output_path: Path) -> None:
        output_path.write_bytes(b"mp4")

    monkeypatch.setattr(presenter_module, "probe_media_duration", probe)
    monkeypatch.setattr(presenter_module.PresenterVideoService, "_normalize_clip", normalize)


def _video_file(filename: str = "clip.mp4", content_type: str = "video/mp4") -> UploadFile:
    return UploadFile(file=io.BytesIO(b"video"), filename=filename, headers=Headers({"content-type": content_type}))


def _import_take(db: Session, *, module: str = "websites", auto_generate: bool = True) -> PresenterVideo:
    return asyncio.run(
        presenter_video_service.store_upload(db, _OWNER.id, _video_file(), 4.0, 5.0, auto_generate, module)
    )


def _keep_example(db: Session, take: PresenterVideo, subject_name: str = "Plomberie Dubois") -> PresenterVideo:
    return asyncio.run(
        presenter_video_service.store_example(db, take, _video_file("example.mp4"), _EXAMPLE_SITE_ID, subject_name)
    )


def test_the_first_take_is_used_and_a_new_one_waits_to_be_chosen(db: Session, storage: _FakeStorage) -> None:
    first = _import_take(db)
    second = _import_take(db)

    assert (first.take_number, first.is_active) == (1, True)
    assert (second.take_number, second.is_active) == (2, False)
    assert first.file_path != second.file_path
    assert storage.uploaded == [first.file_path, second.file_path]
    assert presenter_video_service.get_for_user(db, _OWNER.id).id == first.id


def test_each_module_keeps_its_own_takes(db: Session, storage: _FakeStorage) -> None:
    site_take = _import_take(db)
    receptionist_take = _import_take(db, module="ai-assistant")

    assert (receptionist_take.take_number, receptionist_take.is_active) == (1, True)
    assert presenter_video_service.get_for_user(db, _OWNER.id, "ai-assistant").id == receptionist_take.id
    assert presenter_video_service.get_for_user(db, _OWNER.id).id == site_take.id


def test_choosing_a_take_moves_the_next_videos_to_it(db: Session, storage: _FakeStorage) -> None:
    first = _import_take(db)
    second = _import_take(db)

    presenter_video_service.activate_take(db, second)

    db.refresh(first)
    assert not first.is_active
    assert second.is_active
    assert presenter_video_service.get_for_user(db, _OWNER.id).id == second.id


def test_the_take_in_use_goes_only_once_it_is_the_last_one(db: Session, storage: _FakeStorage) -> None:
    first = _import_take(db)
    second = _import_take(db)
    second_clip = second.file_path

    with pytest.raises(PresenterTakeInUseError):
        presenter_video_service.delete_take(db, first)

    presenter_video_service.delete_take(db, second)
    assert storage.deleted == [second_clip]

    presenter_video_service.delete_take(db, first)
    assert presenter_video_service.get_for_user(db, _OWNER.id) is None


def test_a_new_take_follows_the_highest_number_kept(db: Session, storage: _FakeStorage) -> None:
    _import_take(db)
    middle = _import_take(db)
    _import_take(db)

    presenter_video_service.delete_take(db, middle)

    assert _import_take(db).take_number == 4


def test_moving_a_cut_point_drops_the_example_built_with_the_old_one(db: Session, storage: _FakeStorage) -> None:
    take = _keep_example(db, _import_take(db))
    example_key = take.example_video_key

    presenter_video_service.update_take_timings(db, take, take.intro_seconds, take.outro_seconds, None)
    assert take.example_video_key == example_key

    presenter_video_service.update_take_timings(db, take, 6.0, take.outro_seconds, None)
    assert take.example_video_key is None
    assert take.example_subject_name is None
    assert example_key in storage.deleted


def test_a_cut_point_read_back_with_float_noise_has_not_moved(db: Session, storage: _FakeStorage) -> None:
    take = _keep_example(db, _import_take(db))
    take.intro_seconds = 4.300000190734863
    db.commit()

    presenter_video_service.update_take_timings(db, take, 4.3, take.outro_seconds, None)

    assert take.example_video_key is not None


def test_a_new_example_replaces_the_previous_one(db: Session, storage: _FakeStorage) -> None:
    take = _keep_example(db, _import_take(db))
    first_example_key = take.example_video_key

    _keep_example(db, take, "Garage Morel")

    assert take.example_subject_name == "Garage Morel"
    assert take.example_subject_id == _EXAMPLE_SITE_ID
    assert take.example_video_key != first_example_key
    assert storage.deleted == [first_example_key]


def test_an_example_must_be_an_mp4(db: Session, storage: _FakeStorage) -> None:
    take = _import_take(db)

    with pytest.raises(HTTPException) as caught:
        asyncio.run(
            presenter_video_service.store_example(
                db, take, _video_file("example.webm", "video/webm"), _EXAMPLE_SITE_ID, "Plomberie Dubois"
            )
        )

    assert caught.value.status_code == 400


def test_auto_generation_is_a_setting_of_the_module(db: Session, storage: _FakeStorage) -> None:
    first = _import_take(db, auto_generate=False)
    second = _import_take(db, auto_generate=True)

    assert second.auto_generate is False

    presenter_video_service.set_auto_generate(db, _OWNER.id, "websites", True)

    db.refresh(first)
    db.refresh(second)
    assert first.auto_generate and second.auto_generate
    assert presenter_video_service.is_module_auto_generating(db, _OWNER.id, "websites")


def test_the_routes_list_the_takes_and_refuse_to_delete_the_one_in_use(db: Session, storage: _FakeStorage) -> None:
    first = _import_take(db)
    second = _import_take(db)

    listing = asyncio.run(routes.list_presenter_video_takes(module="websites", current_user=_OWNER, db=db))
    assert [(take.take_number, take.is_active) for take in listing.takes] == [(1, True), (2, False)]
    assert listing.auto_generate is True

    with pytest.raises(HTTPException) as caught:
        asyncio.run(routes.delete_presenter_video_take(first.id, current_user=_OWNER, db=db))
    assert caught.value.status_code == 409

    with pytest.raises(HTTPException) as caught:
        asyncio.run(routes.activate_presenter_video_take(second.id, current_user=_STRANGER, db=db))
    assert caught.value.status_code == 404
