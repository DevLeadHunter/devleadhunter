"""Drop ``sms_configs.cold_sms_enabled``: no SMS leaves for a prospect before the user launches a campaign.

The switch « Prospection SMS des prospects sans email » texted a prospect with a mobile and no email
as soon as his demo site existed. A first-contact SMS now only goes out through an SMS campaign; the
J+30 relance (``auto_relance_enabled``) stays the one automated SMS.
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
    """Drop the retired switch (``IF EXISTS`` keeps it idempotent)."""
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE sms_configs DROP COLUMN IF EXISTS cold_sms_enabled"))
        conn.commit()


if __name__ == "__main__":
    run_migration()
    print("sms_configs.cold_sms_enabled dropped.")
