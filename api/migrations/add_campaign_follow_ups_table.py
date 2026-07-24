"""
Migration: create the campaign_follow_ups table + add ab_variant/follow_up_index
to email_queue and ab_variant to email_logs.

Run with:
    python migrations/add_campaign_follow_ups_table.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine
from models.campaign_follow_up import CampaignFollowUp


def run_migration() -> None:
    print("Running migration: add_campaign_follow_ups_table")

    # 1. Create campaign_follow_ups table
    CampaignFollowUp.__table__.create(engine, checkfirst=True)
    print("  + campaign_follow_ups table")

    # 2. Extend email_queue with ab_variant + follow_up_index
    with engine.connect() as conn:
        conn.execute(
            text(
                "ALTER TABLE email_queue "
                "ADD COLUMN IF NOT EXISTS ab_variant VARCHAR(1) NULL AFTER queue_type, "
                "ADD COLUMN IF NOT EXISTS follow_up_index INT NOT NULL DEFAULT 0 AFTER ab_variant"
            )
        )
        # 3. Extend email_logs with ab_variant
        conn.execute(
            text("ALTER TABLE email_logs ADD COLUMN IF NOT EXISTS ab_variant VARCHAR(1) NULL AFTER campaign_id")
        )
        conn.commit()

    print("  + email_queue.ab_variant")
    print("  + email_queue.follow_up_index")
    print("  + email_logs.ab_variant")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Campaign follow-ups + A/B variant fields")
    print("=" * 60)
    run_migration()
