"""
Migration: add ``suppressed_at`` column to ``email_logs``.

Resend fires ``email.suppressed`` when a recipient is on the suppression
list (previous hard bounce or spam complaint).  A dedicated timestamp
column lets the timeline display this event distinctly.

Run with:
    python migrations/add_suppressed_at.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.database import engine


def run_migration() -> None:
    print("Running migration: add_suppressed_at")
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE email_logs "
            "ADD COLUMN IF NOT EXISTS suppressed_at DATETIME NULL "
            "AFTER complained_at"
        ))
        conn.commit()
    print("  + email_logs.suppressed_at")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add suppressed_at to email_logs")
    print("=" * 60)
    run_migration()
