"""Clear the delivery time the Resend webhook stamped on emails that were only delayed.

Until 2026-11-13 an ``email.delivery_delayed`` event wrote ``delivered_at = now``. The campaign figures
and the evening recap count an email as delivered from that column, so an email still held by the
recipient's host (the Microsoft outage of 2026-11-13) was counted as arrived. The webhook no longer
writes it; this resets the rows still waiting, and a real delivery will write the time again.
Re-runnable: a cleared row no longer matches.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine

_CLEAR_DELAYED_DELIVERY_TIME_SQL = """
UPDATE email_logs
SET delivered_at = NULL
WHERE status = 'delivery_delayed'
  AND delivered_at IS NOT NULL
"""


def run_migration(target_engine: Engine = engine) -> None:
    """Clear ``delivered_at`` on the delayed emails of the given database (the application's by default)."""
    with target_engine.connect() as connection:
        connection.execute(text(_CLEAR_DELAYED_DELIVERY_TIME_SQL))
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("Delivery time cleared on the emails that were only delayed.")
