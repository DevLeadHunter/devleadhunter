"""
Migration: add ``prospects.sms_relance_excluded``.

An operator opt-out for the J+30 SMS relance of ONE prospect (e.g. already handled by
hand), without blocking every channel like « ne plus contacter ». Drops the prospect
from the SMS relance selection (worker + forecast projection); cold SMS and email stay.

Run with:
    python migrations/add_prospect_sms_relance_excluded.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_prospect_sms_relance_excluded")
    with engine.connect() as conn:
        conn.execute(
            text("ALTER TABLE prospects ADD COLUMN IF NOT EXISTS sms_relance_excluded TINYINT(1) NOT NULL DEFAULT 0")
        )
        conn.commit()
    print("  + prospects.sms_relance_excluded")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add prospects sms_relance_excluded column")
    print("=" * 60)
    run_migration()
