"""The migrations of the videos built by the PC: a server render left unfinished fails, the new columns come once."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import migrations.add_ai_assistant_video_desktop_requested_at as assistant_request_migration
import migrations.add_presenter_video_in_use_since as clip_in_use_migration
import migrations.fail_unfinished_server_videos as unfinished_videos_migration
from models.ai_assistant import AiAssistant
from models.demo_site import DemoSite


def _bare_engine() -> Engine:
    return create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)


def _site(db: Session, slug: str, video_status: str | None) -> DemoSite:
    site = DemoSite(
        user_id=1,
        slug=slug,
        business_name=slug,
        status="active",
        expires_at=datetime.now(UTC) + timedelta(days=21),
        video_status=video_status,
        video_error="Une ancienne erreur" if video_status == "failed" else None,
    )
    db.add(site)
    return site


def test_the_videos_a_server_render_left_unfinished_end_failed_once(
    db: Session, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    pending = _site(db, "en-attente", "pending")
    generating = _site(db, "en-cours", "generating")
    ready = _site(db, "prete", "ready")
    failed = _site(db, "echec", "failed")
    never = _site(db, "jamais", None)
    assistant = AiAssistant(user_id=1, slug="toitures-morel", business_name="Toitures Morel", video_status="generating")
    db.add(assistant)
    db.commit()
    monkeypatch.setattr(unfinished_videos_migration, "engine", engine)

    unfinished_videos_migration.run_migration()
    unfinished_videos_migration.run_migration()

    db.expire_all()
    for unfinished in (pending, generating, assistant):
        assert unfinished.video_status == "failed"
        assert unfinished.video_error.startswith("La génération sur le serveur n'existe plus")
    assert (ready.video_status, ready.video_error) == ("ready", None)
    assert (failed.video_status, failed.video_error) == ("failed", "Une ancienne erreur")
    assert never.video_status is None


def test_the_receptionist_request_column_is_added_once(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _bare_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE ai_assistants (id INTEGER PRIMARY KEY, slug VARCHAR(120))"))
        conn.execute(text("INSERT INTO ai_assistants (id, slug) VALUES (1, 'toitures-morel')"))
        conn.commit()
    monkeypatch.setattr(assistant_request_migration, "engine", engine)

    assistant_request_migration.run_migration()
    assistant_request_migration.run_migration()

    columns = {column["name"] for column in inspect(engine).get_columns("ai_assistants")}
    with engine.connect() as conn:
        requested_at = conn.execute(text("SELECT video_desktop_requested_at FROM ai_assistants")).scalar_one()
    assert "video_desktop_requested_at" in columns
    assert requested_at is None


def test_the_takes_in_use_get_their_creation_date_once(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = _bare_engine()
    with engine.connect() as conn:
        conn.execute(
            text("CREATE TABLE presenter_videos (id INTEGER PRIMARY KEY, is_active BOOLEAN, created_at DATETIME)")
        )
        conn.execute(
            text(
                "INSERT INTO presenter_videos (id, is_active, created_at) VALUES "
                "(1, 1, '2026-09-01 10:00:00'), (2, 0, '2026-09-20 10:00:00')"
            )
        )
        conn.commit()
    monkeypatch.setattr(clip_in_use_migration, "engine", engine)

    clip_in_use_migration.run_migration()
    with engine.connect() as conn:
        first_run = dict(conn.execute(text("SELECT id, in_use_since FROM presenter_videos")).all())
        conn.execute(text("UPDATE presenter_videos SET in_use_since = '2026-10-09 08:00:00' WHERE id = 1"))
        conn.commit()
    clip_in_use_migration.run_migration()

    with engine.connect() as conn:
        second_run = dict(conn.execute(text("SELECT id, in_use_since FROM presenter_videos")).all())
    assert first_run == {1: "2026-09-01 10:00:00", 2: None}
    assert second_run == {1: "2026-10-09 08:00:00", 2: None}
