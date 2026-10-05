"""
Migration: keep several presenter takes per module, one of them in use.

Until now a new recording overwrote the module's only clip. ``presenter_videos`` gains the take number, the in-use
flag and the example video of each take, and loses its uniqueness on ``(user_id, module)``. Every existing row is
the only take of its module, so it becomes « Prise 1 », in use.

Order matters: the plain ``(user_id, module)`` index is added BEFORE the unique ones are dropped, so the foreign key
on ``user_id`` stays covered by an index throughout. Index and column names are read from INFORMATION_SCHEMA: prod
and local schemas diverge.

Run with:
    python migrations/add_presenter_video_takes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Connection

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

_LOOKUP_INDEX = "ix_presenter_user_module"

_NEW_COLUMNS: dict[str, str] = {
    "take_number": "INT NOT NULL DEFAULT 1",
    "is_active": "TINYINT(1) NOT NULL DEFAULT 1",
    "example_video_key": "VARCHAR(512) NULL",
    "example_subject_id": "INT NULL",
    "example_subject_name": "VARCHAR(255) NULL",
    "example_generated_at": "DATETIME NULL",
}


def _column_exists(connection: Connection, column_name: str) -> bool:
    """Whether ``presenter_videos`` already has the column (read on the live schema)."""
    result = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'presenter_videos'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def _index_exists(connection: Connection, index_name: str) -> bool:
    """Whether ``presenter_videos`` already has an index of this name."""
    result = connection.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'presenter_videos'
              AND INDEX_NAME = :index_name
            """
        ),
        {"index_name": index_name},
    )
    return bool(result.scalar())


def _unique_indexes_on_user(connection: Connection) -> list[str]:
    """The unique indexes that start with ``user_id``: they would forbid a second take."""
    rows = connection.execute(
        text(
            """
            SELECT DISTINCT INDEX_NAME
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'presenter_videos'
              AND NON_UNIQUE = 0
              AND INDEX_NAME <> 'PRIMARY'
              AND COLUMN_NAME = 'user_id'
              AND SEQ_IN_INDEX = 1
            """
        )
    ).fetchall()
    return [index_name for (index_name,) in rows]


def run_migration() -> None:
    """Add the take columns, then swap the unique index for a plain one (re-runnable)."""
    print("Running migration: add_presenter_video_takes")
    with engine.connect() as connection:
        for column_name, definition in _NEW_COLUMNS.items():
            if not _column_exists(connection, column_name):
                connection.execute(text(f"ALTER TABLE presenter_videos ADD COLUMN {column_name} {definition}"))
                print(f"  + column {column_name}")

        if not _index_exists(connection, _LOOKUP_INDEX):
            connection.execute(text(f"ALTER TABLE presenter_videos ADD INDEX {_LOOKUP_INDEX} (user_id, module)"))
            print(f"  + index {_LOOKUP_INDEX}")

        for index_name in _unique_indexes_on_user(connection):
            connection.execute(text(f"ALTER TABLE presenter_videos DROP INDEX `{index_name}`"))
            print(f"  - dropped unique index {index_name}")

        connection.commit()
    print("Migration completed successfully.")


if __name__ == "__main__":
    run_migration()
