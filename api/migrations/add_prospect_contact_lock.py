"""
Migration: add the cross-module contact-lock columns to ``prospects``.

Once a prospect is contacted for one sellable module (a website campaign, an AI-assistant
campaign, a cold SMS…), the *other* module must leave him alone for a while, so the same
prospect is never approached for two different offers at once. We stamp which module last
engaged him and when; the lock window lives in ``services/contact_lock_service.py``.

Run with:
    python migrations/add_prospect_contact_lock.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_prospect_contact_lock")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE prospects ADD COLUMN IF NOT EXISTS contacted_by_module VARCHAR(32) NULL"))
        conn.execute(text("ALTER TABLE prospects ADD COLUMN IF NOT EXISTS contacted_by_module_at DATETIME NULL"))
        conn.commit()
    print("  + prospects.contacted_by_module / contacted_by_module_at")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add prospects cross-module contact-lock columns")
    print("=" * 60)
    run_migration()
