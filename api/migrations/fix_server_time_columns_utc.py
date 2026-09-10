"""
Migration: shift every MySQL-clock datetime column to UTC.

All ``created_at`` / ``updated_at`` / ``added_at`` columns were filled by MySQL
(``server_default=func.now()`` / ``onupdate=func.now()``) — the server clock,
which is not UTC in prod — while the web assumes naive UTC and adds the local
offset on display, so every one of these dates showed two hours late. The
models now write them in UTC from Python; this shifts the existing rows by the
server's UTC offset, measured at run time (prod and local do not share a
timezone, per the schema-divergence rule). Every row predates the model change
and postdates 2026-03-29, so the whole dataset sits in one DST period and one
uniform offset is correct. ``sms_messages`` is excluded: fix_sms_created_at_utc
already shifted it. Columns are checked against INFORMATION_SCHEMA first — a
missing column is skipped, and a TIMESTAMP-typed one (session-tz converted, so
shifting would corrupt it) is skipped with a warning. No-op on a UTC server.

Run with:
    python migrations/fix_server_time_columns_utc.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine

# Snapshot of every (table, column) that MySQL used to fill, at the time of the fix.
_SERVER_TIME_COLUMNS: list[tuple[str, str]] = [
    ("acquisition_runs", "created_at"),
    ("acquisition_runs", "updated_at"),
    ("acquisition_run_items", "created_at"),
    ("acquisition_run_items", "updated_at"),
    ("activity_logs", "created_at"),
    ("campaigns", "created_at"),
    ("campaigns", "updated_at"),
    ("campaign_prospects", "added_at"),
    ("campaign_follow_ups", "created_at"),
    ("credit_settings", "created_at"),
    ("credit_settings", "updated_at"),
    ("credit_transactions", "created_at"),
    ("demo_sites", "created_at"),
    ("demo_sites", "updated_at"),
    ("demo_site_leads", "created_at"),
    ("email_accounts", "created_at"),
    ("email_accounts", "updated_at"),
    ("email_logs", "created_at"),
    ("email_logs", "updated_at"),
    ("email_queue", "created_at"),
    ("email_queue", "updated_at"),
    ("email_replies", "created_at"),
    ("email_signatures", "created_at"),
    ("email_signatures", "updated_at"),
    ("email_templates", "created_at"),
    ("email_templates", "updated_at"),
    ("email_template_library_hides", "created_at"),
    ("email_unsubscribes", "created_at"),
    ("facebook_page_exclusions", "created_at"),
    ("notifications", "created_at"),
    ("orders", "created_at"),
    ("orders", "updated_at"),
    ("organizations", "created_at"),
    ("organizations", "updated_at"),
    ("organization_members", "created_at"),
    ("payment_accounts", "created_at"),
    ("payment_accounts", "updated_at"),
    ("presenter_videos", "created_at"),
    ("presenter_videos", "updated_at"),
    ("prospects", "created_at"),
    ("prospects", "updated_at"),
    ("prospect_enrichments", "created_at"),
    ("prospect_enrichments", "updated_at"),
    ("prospect_interactions", "created_at"),
    ("push_subscriptions", "created_at"),
    ("resend_config", "created_at"),
    ("resend_config", "updated_at"),
    ("scraper_diagnostics", "created_at"),
    ("send_policies", "created_at"),
    ("send_policies", "updated_at"),
    ("sms_configs", "created_at"),
    ("sms_configs", "updated_at"),
    ("sms_suppressions", "created_at"),
    ("support_attachments", "created_at"),
    ("support_messages", "created_at"),
    ("support_tickets", "created_at"),
    ("support_tickets", "updated_at"),
    ("users", "created_at"),
    ("users", "updated_at"),
]


def run_migration() -> None:
    print("Running migration: fix_server_time_columns_utc")
    with engine.connect() as conn:
        offset_minutes = conn.execute(text("SELECT TIMESTAMPDIFF(MINUTE, UTC_TIMESTAMP(), NOW())")).scalar() or 0
        if offset_minutes == 0:
            print("  = MySQL clock already on UTC, nothing to shift")
            return
        shifted = 0
        for table, column in _SERVER_TIME_COLUMNS:
            data_type = conn.execute(
                text(
                    "SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND COLUMN_NAME = :column"
                ),
                {"table": table, "column": column},
            ).scalar()
            if data_type is None:
                print(f"  ? {table}.{column} absent, skipped")
                continue
            if data_type.lower() != "datetime":
                print(f"  ! {table}.{column} is {data_type} (session-tz converted), skipped — fix it separately")
                continue
            result = conn.execute(
                text(
                    f"UPDATE {table} SET {column} = DATE_SUB({column}, INTERVAL :offset MINUTE) "
                    f"WHERE {column} IS NOT NULL"
                ),
                {"offset": offset_minutes},
            )
            shifted += result.rowcount
            print(f"  + {table}.{column}: {result.rowcount} rows")
        conn.commit()
    print(f"  = shifted {shifted} values by -{offset_minutes} min")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Shift MySQL-clock datetime columns to UTC")
    print("=" * 60)
    run_migration()
