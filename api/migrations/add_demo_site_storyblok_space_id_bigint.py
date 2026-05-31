"""Widen demo_sites.storyblok_space_id to BIGINT for Storyblok space ids."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def run_migration() -> None:
    """Alter storyblok_space_id so large Storyblok ids fit."""
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE demo_sites
                MODIFY COLUMN storyblok_space_id BIGINT NULL
                """
            )
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("demo_sites.storyblok_space_id widened to BIGINT.")
