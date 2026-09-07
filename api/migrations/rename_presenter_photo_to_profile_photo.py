"""Rename ``users.presenter_photo_path`` to ``profile_photo_path``.

The photo is a profile-level asset (today the thumbnail bubble, reusable
elsewhere later) — the column must not carry its first use as a name. Data is
preserved; a fresh install already gets ``profile_photo_path`` from the model.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def _column_exists(conn, column_name: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'users'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if _column_exists(conn, "presenter_photo_path") and not _column_exists(conn, "profile_photo_path"):
            conn.execute(
                text(
                    """
                    ALTER TABLE users
                    CHANGE COLUMN presenter_photo_path profile_photo_path VARCHAR(512) NULL
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("users.profile_photo_path ensured.")
