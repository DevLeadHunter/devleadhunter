"""Backfill ``contacted`` for prospects reached by SMS.

Until now only email sends flagged a prospect as contacted: a prospect reached by
a manual SMS (e.g. no email address, so the campaign skipped him) still showed as
« non contacté ». Flag every prospect with at least one SMS that left (sent or
delivered). Idempotent by construction.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine


def run_migration() -> None:
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                UPDATE prospects
                SET contacted = 1
                WHERE contacted = 0
                  AND id IN (
                    SELECT DISTINCT prospect_id
                    FROM sms_messages
                    WHERE prospect_id IS NOT NULL
                      AND status IN ('sent', 'delivered')
                  )
                """
            )
        )
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("prospects.contacted backfilled from sent SMS.")
