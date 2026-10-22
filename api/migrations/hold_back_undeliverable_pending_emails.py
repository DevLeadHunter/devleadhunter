"""Hold back the pending campaign emails of prospects whose every address already bounced.

Before 2026-10-22 the dispatch never read ``prospects.email_undeliverable``: a follow-up planned when the
first email left still went out after that email bounced (Resend suppressed one, a soft bounce could have
bounced again). The dispatch now skips them and a new bounce holds them back at once; this catches the rows
planned before that change. Only email campaigns are touched: the prospect stays reachable by SMS.
Re-runnable: a held-back row is no longer pending.
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

SKIP_REASON = "Adresse en échec (rebond)"

_HOLD_BACK_SQL = """
UPDATE email_queue
SET status = 'skipped', skip_reason = :reason
WHERE status = 'pending'
  AND prospect_id IN (SELECT id FROM prospects WHERE email_undeliverable = 1)
  AND campaign_id IN (SELECT id FROM campaigns WHERE channel = 'email')
"""


def run_migration(target_engine: Engine = engine) -> None:
    """Skip the pending email rows of undeliverable prospects on the given database (the application's by default)."""
    with target_engine.connect() as connection:
        connection.execute(text(_HOLD_BACK_SQL), {"reason": SKIP_REASON})
        connection.commit()


if __name__ == "__main__":
    run_migration()
    print("Pending emails of undeliverable prospects held back.")
