"""Add ``presenter_videos.in_use_since``: when each module's take in use was chosen.

A video published before that moment was made with an older take. The takes already in use get their creation date:
the day they were chosen is not known, and an earlier date never shows a video made with them as outdated.
Re-runnable.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def run_migration() -> None:
    """Add the column if it is missing, then date the takes in use that have no date yet."""
    columns = {column["name"] for column in inspect(engine).get_columns("presenter_videos")}
    with engine.connect() as conn:
        if "in_use_since" not in columns:
            conn.execute(text("ALTER TABLE presenter_videos ADD COLUMN in_use_since DATETIME NULL"))
        conn.execute(
            text("UPDATE presenter_videos SET in_use_since = created_at WHERE is_active = 1 AND in_use_since IS NULL")
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
