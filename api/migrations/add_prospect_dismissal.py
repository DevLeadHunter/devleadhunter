"""
Migration: add the « écarté » columns to prospects.

An « écarté » prospect stays in the base, so no search finds it again, but leaves every list,
campaign and enrichment until someone takes it back from the « Écartés » tab.

Run with:
    python migrations/add_prospect_dismissal.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    """Add ``dismissed_at``, ``dismissal_reason`` and ``dismissed_by_user_id`` to prospects."""
    print("Running migration: add_prospect_dismissal")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE prospects ADD COLUMN IF NOT EXISTS dismissed_at DATETIME NULL"))
        conn.execute(text("ALTER TABLE prospects ADD COLUMN IF NOT EXISTS dismissal_reason VARCHAR(500) NULL"))
        conn.execute(text("ALTER TABLE prospects ADD COLUMN IF NOT EXISTS dismissed_by_user_id INT NULL"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_prospects_dismissed_at ON prospects (dismissed_at)"))
        conn.commit()
    print("  + prospects.dismissed_at / dismissal_reason / dismissed_by_user_id")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add prospects « écarté » columns")
    print("=" * 60)
    run_migration()
