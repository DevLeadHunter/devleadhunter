"""
Migration: add cold-email queue fields to campaigns + create email_queue table.

Changes:
  campaigns   — 4 new nullable columns for cold-email scheduling
  email_queue — new table driving the rate-limited send queue and J+5 follow-up

Run with:
    python migrations/add_campaign_queue.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.database import engine


def run_migration() -> None:
    """Apply schema changes for the cold-email queue system."""
    print("Running migration: add_campaign_queue")

    with engine.connect() as conn:
        # ── campaigns: follow-up template + scheduling config ─────────────────
        for col_def in (
            "follow_up_template_id INT NULL REFERENCES email_templates(id) ON DELETE SET NULL",
            "follow_up_delay_days  INT NOT NULL DEFAULT 5",
            "send_delay_minutes    INT NOT NULL DEFAULT 20",
            "started_at            DATETIME NULL",
        ):
            col_name = col_def.split()[0]
            exists = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = DATABASE() "
                "AND table_name = 'campaigns' "
                f"AND column_name = '{col_name}'"
            )).scalar()
            if not exists:
                conn.execute(text(f"ALTER TABLE campaigns ADD COLUMN {col_def}"))
                print(f"  + campaigns.{col_name}")
            else:
                print(f"  ~ campaigns.{col_name} already exists")

        # ── email_queue table ─────────────────────────────────────────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS email_queue (
                id              INT          NOT NULL AUTO_INCREMENT PRIMARY KEY,
                user_id         INT          NOT NULL,
                campaign_id     INT          NOT NULL,
                prospect_id     INT          NOT NULL,
                template_id     INT          NOT NULL,
                email_account_id INT         NOT NULL,
                -- 'initial' = J1 mail, 'followup' = J+N relance
                queue_type      VARCHAR(20)  NOT NULL DEFAULT 'initial',
                -- when this item becomes eligible for sending
                scheduled_at    DATETIME     NOT NULL,
                -- NULL until sent; links to email_logs row
                email_log_id    INT          NULL,
                -- pending | sent | skipped | failed
                status          VARCHAR(20)  NOT NULL DEFAULT 'pending',
                created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at      DATETIME     NULL ON UPDATE CURRENT_TIMESTAMP,

                INDEX idx_eq_campaign (campaign_id),
                INDEX idx_eq_user_status (user_id, status),
                INDEX idx_eq_scheduled (scheduled_at, status),

                FOREIGN KEY (user_id)          REFERENCES users(id)            ON DELETE CASCADE,
                FOREIGN KEY (campaign_id)      REFERENCES campaigns(id)        ON DELETE CASCADE,
                FOREIGN KEY (prospect_id)      REFERENCES prospects(id)        ON DELETE CASCADE,
                FOREIGN KEY (template_id)      REFERENCES email_templates(id)  ON DELETE RESTRICT,
                FOREIGN KEY (email_account_id) REFERENCES email_accounts(id)   ON DELETE RESTRICT,
                FOREIGN KEY (email_log_id)     REFERENCES email_logs(id)       ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))
        print("  + email_queue table")

        conn.commit()

    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add Campaign Queue")
    print("=" * 60)
    run_migration()
