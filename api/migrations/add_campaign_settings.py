"""
Migration: add campaign configuration columns.

Adds template_id, email_account_id, ab_template_id_b to campaigns so that
the configuration is stored persistently on the campaign rather than only at
launch time.

Run with:
    python migrations/add_campaign_settings.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.database import engine


def run_migration() -> None:
    print("Running migration: add_campaign_settings")
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE campaigns "
            "ADD COLUMN IF NOT EXISTS template_id INT NULL, "
            "ADD COLUMN IF NOT EXISTS email_account_id INT NULL, "
            "ADD COLUMN IF NOT EXISTS ab_template_id_b INT NULL"
        ))
        conn.commit()
    print("  + campaigns.template_id")
    print("  + campaigns.email_account_id")
    print("  + campaigns.ab_template_id_b")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add campaign settings columns")
    print("=" * 60)
    run_migration()
