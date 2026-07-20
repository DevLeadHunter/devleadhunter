"""Add ``source`` to presenter_videos (imported file vs recorded in-app).

Clips recorded in-app are cut take by take, so their intro/outro seconds are
measured rather than guessed — the settings page hides the manual segment
fields for them. Existing rows predate the recorder and were all imported.
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
              AND TABLE_NAME = 'presenter_videos'
              AND COLUMN_NAME = :column_name
            """
        ),
        {"column_name": column_name},
    )
    return bool(result.scalar())


def run_migration() -> None:
    with engine.connect() as conn:
        if not _column_exists(conn, "source"):
            conn.execute(
                text(
                    """
                    ALTER TABLE presenter_videos
                    ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'upload'
                    """
                )
            )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("presenter_videos.source ensured.")
