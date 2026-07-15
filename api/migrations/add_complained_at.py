"""
Migration: add ``complained_at`` column to ``email_logs``.

Previously, spam-complaint events shared ``bounced_at`` which made it
impossible to distinguish bounces from complaints in the timeline.

Run with:
    python migrations/add_complained_at.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.database import engine


def run_migration() -> None:
    print("Running migration: add_complained_at")
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE email_logs "
            "ADD COLUMN IF NOT EXISTS complained_at DATETIME NULL "
            "AFTER bounced_at"
        ))
        conn.commit()
    print("  + email_logs.complained_at")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add complained_at to email_logs")
    print("=" * 60)
    run_migration()
