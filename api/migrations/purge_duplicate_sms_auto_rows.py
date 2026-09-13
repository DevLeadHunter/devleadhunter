"""
Migration: keep one planned-SMS row per (user, prospect, kind).

The first planner builds re-planned a prospect whose pending row had just been skipped
(reply detected at send time but not at selection time), stacking one skipped duplicate
per worker pass. The selection and the planner are fixed; this cleans the piles up,
keeping the most useful row per prospect (pending > sent > skipped > cancelled, newest).

Run with:
    python migrations/purge_duplicate_sms_auto_rows.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine

_STATUS_PRIORITY = {"pending": 0, "sent": 1, "skipped": 2, "cancelled": 3}


def run_migration() -> None:
    print("Running migration: purge_duplicate_sms_auto_rows")
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, user_id, prospect_id, kind, status FROM sms_auto_queue")).all()
        best_by_group: dict[tuple[int, int, str], tuple[tuple[int, int], int]] = {}
        for row_id, user_id, prospect_id, kind, row_status in rows:
            group = (user_id, prospect_id, kind)
            rank = (_STATUS_PRIORITY.get(row_status, 9), -row_id)
            current = best_by_group.get(group)
            if current is None or rank < current[0]:
                best_by_group[group] = (rank, row_id)
        keeper_ids = {entry[1] for entry in best_by_group.values()}
        duplicate_ids = [row[0] for row in rows if row[0] not in keeper_ids]
        for duplicate_id in duplicate_ids:
            conn.execute(text("DELETE FROM sms_auto_queue WHERE id = :id"), {"id": duplicate_id})
        conn.commit()
    print(f"  - removed {len(duplicate_ids)} duplicate row(s)")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Purge duplicate planned-SMS rows")
    print("=" * 60)
    run_migration()
