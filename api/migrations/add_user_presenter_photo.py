"""Add ``presenter_photo_path`` to users (photo bubble on video thumbnails).

R2 key of the presenter photo drawn as a round bubble on the prospection-video
email thumbnail — a human face is the strongest inbox trust cue. Nullable, no
backfill needed.
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
        if not _column_exists(conn, "presenter_photo_path"):
            conn.execute(
                text(
                    """
                    ALTER TABLE users
                    ADD COLUMN presenter_photo_path VARCHAR(512) NULL
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("users.presenter_photo_path ensured.")
