"""
Migration: system-campaign columns for the planned J+30 SMS relances.

``campaigns.system_kind`` marks product-managed campaigns (the per-user always-alive
« Relances SMS J+30 »), and ``sms_auto_queue.campaign_id`` links each planned relance
to that campaign so the campaign page shows a real, self-updating queue.

Run with:
    python migrations/add_sms_auto_relance_campaign.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_sms_auto_relance_campaign")
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS system_kind VARCHAR(32) NULL"))
        conn.execute(text("ALTER TABLE sms_auto_queue ADD COLUMN IF NOT EXISTS campaign_id INT NULL"))
        conn.commit()
    print("  + campaigns.system_kind / sms_auto_queue.campaign_id")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add system-campaign columns for planned SMS relances")
    print("=" * 60)
    run_migration()
