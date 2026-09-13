"""
Migration: create the ``sms_auto_queue`` table.

The automated SMS (relance J+30 + cold) are now PLANNED: one row per upcoming send with
its exact slot, so the forecast shows real times and the operator can cancel or move a
send. The worker dispatches due rows instead of picking candidates live on each pass.

Run with:
    python migrations/add_sms_auto_queue.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def run_migration() -> None:
    print("Running migration: add_sms_auto_queue")
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS sms_auto_queue (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    prospect_id INT NOT NULL,
                    demo_site_id INT NULL,
                    kind VARCHAR(16) NOT NULL,
                    status VARCHAR(16) NOT NULL DEFAULT 'pending',
                    scheduled_at DATETIME NOT NULL,
                    emailed_at DATETIME NULL,
                    skip_reason VARCHAR(255) NULL,
                    sent_at DATETIME NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NULL,
                    INDEX idx_sms_auto_queue_user (user_id),
                    INDEX idx_sms_auto_queue_prospect (prospect_id),
                    INDEX idx_sms_auto_queue_status (status),
                    INDEX idx_sms_auto_queue_scheduled (scheduled_at)
                )
                """
            )
        )
        conn.commit()
    print("  + sms_auto_queue")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Create sms_auto_queue table")
    print("=" * 60)
    run_migration()
