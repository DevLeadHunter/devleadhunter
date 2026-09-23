"""
Migration: make the presenter clip per-module.

A user now keeps one webcam clip *per sellable module* (a website pitch and an assistant pitch are
different speeches), so ``presenter_videos`` gains a ``module`` column and its uniqueness moves from
``user_id`` to ``(user_id, module)``. Existing rows become the ``websites`` clip.

Order matters: add the composite unique BEFORE dropping the old single-column unique, so the foreign
key on ``user_id`` stays covered by an index throughout. The old index name varies with how it was
created, so it is discovered from INFORMATION_SCHEMA rather than assumed.

Run with:
    python migrations/add_presenter_video_module.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine

_COMPOSITE = "uq_presenter_user_module"


def run_migration() -> None:
    print("Running migration: add_presenter_video_module")
    with engine.connect() as conn:
        conn.execute(
            text("ALTER TABLE presenter_videos ADD COLUMN IF NOT EXISTS module VARCHAR(32) NOT NULL DEFAULT 'websites'")
        )

        composite_exists = conn.execute(
            text(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'presenter_videos' "
                "AND INDEX_NAME = :name"
            ),
            {"name": _COMPOSITE},
        ).scalar()
        if not composite_exists:
            conn.execute(text(f"ALTER TABLE presenter_videos ADD CONSTRAINT {_COMPOSITE} UNIQUE (user_id, module)"))
            print(f"  + composite unique ({_COMPOSITE})")

        # Drop every single-column UNIQUE index that covers only user_id (its name varies).
        stale = conn.execute(
            text(
                "SELECT s.INDEX_NAME FROM INFORMATION_SCHEMA.STATISTICS s "
                "WHERE s.TABLE_SCHEMA = DATABASE() AND s.TABLE_NAME = 'presenter_videos' "
                "AND s.NON_UNIQUE = 0 AND s.INDEX_NAME NOT IN ('PRIMARY', :name) AND s.COLUMN_NAME = 'user_id' "
                "GROUP BY s.INDEX_NAME HAVING COUNT(*) = 1"
            ),
            {"name": _COMPOSITE},
        ).fetchall()
        for (index_name,) in stale:
            conn.execute(text(f"ALTER TABLE presenter_videos DROP INDEX `{index_name}`"))
            print(f"  - dropped stale unique index {index_name}")

        conn.commit()
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: presenter_videos per-module")
    print("=" * 60)
    run_migration()
