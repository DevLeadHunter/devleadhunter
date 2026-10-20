"""Undo the human opens the Resend status sync stamped on 2026-10-20.

Opening the « Suivi des e-mails » page used to run the Resend status sync, which wrote
``opened_at = now`` on every delivered email Resend reported as opened, without the webhook's
machine / human split. Six emails of the wave 4 France campaign got the same second,
2026-10-20 13:36:30 UTC, as a « human » open. The sync no longer writes opens; these rows go back
to what the webhook knew: a later real open (``last_open_at``) is kept, otherwise the open is
cleared and the status returns to delivered. Re-runnable: a repaired row no longer matches.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, bindparam, text
from sqlalchemy.engine import Engine
from sqlalchemy.sql.elements import TextClause

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

STAMPED_EMAIL_LOG_IDS = [236, 237, 239, 253, 254, 255]
SYNC_STAMP = datetime(2026, 10, 20, 13, 36, 30)

_KEEP_LATER_HUMAN_OPEN_SQL = """
UPDATE email_logs
SET opened_at = last_open_at
WHERE id IN :ids
  AND opened_at = :stamp
  AND last_open_at IS NOT NULL
"""

_CLEAR_STAMPED_OPEN_SQL = """
UPDATE email_logs
SET opened_at = NULL,
    status = CASE WHEN status = 'opened' THEN 'delivered' ELSE status END
WHERE id IN :ids
  AND opened_at = :stamp
"""


def _stamped_rows_statement(sql: str) -> TextClause:
    """Bind the id list and the typed stamp so the datetime compares the same way on MySQL and SQLite."""
    return text(sql).bindparams(bindparam("ids", expanding=True), bindparam("stamp", type_=DateTime()))


def run_migration(target_engine: Engine = engine) -> None:
    """Reset the stamped opens on the given database (the application's by default)."""
    parameters = {"ids": STAMPED_EMAIL_LOG_IDS, "stamp": SYNC_STAMP}
    with target_engine.connect() as connection:
        connection.execute(_stamped_rows_statement(_KEEP_LATER_HUMAN_OPEN_SQL), parameters)
        connection.execute(_stamped_rows_statement(_CLEAR_STAMPED_OPEN_SQL), parameters)
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("Opens stamped by the Resend sync on 2026-10-20 reset.")
