"""Undo every human open the Resend status sync stamped on 2026-10-20, whatever the campaign.

``fix_sync_stamped_opens`` listed the six rows of the France campaign; the same page load had
stamped five more rows of the Switzerland and Quebec campaigns. The stamp is the exact second
2026-10-20 13:36:30 UTC with no human open counted (the webhook alone increments
``open_count``), so the repair now matches on that instead of a list of ids. Re-runnable.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.engine import Engine

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

SYNC_STAMP = datetime(2026, 10, 20, 13, 36, 30)

_CLEAR_STAMPED_OPEN_SQL = """
UPDATE email_logs
SET opened_at = NULL,
    status = CASE WHEN status = 'opened' THEN 'delivered' ELSE status END
WHERE opened_at = :stamp
  AND open_count = 0
"""


def run_migration(target_engine: Engine = engine) -> None:
    """Reset the stamped opens on the given database (the application's by default)."""
    statement = text(_CLEAR_STAMPED_OPEN_SQL).bindparams(bindparam("stamp", type_=DateTime()))
    with target_engine.connect() as connection:
        connection.execute(statement, {"stamp": SYNC_STAMP})
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("Opens stamped by the Resend sync on 2026-10-20 reset on every campaign.")
