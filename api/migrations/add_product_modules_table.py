"""Create the product_modules table (the super admin's module switches) and store the first two switches.

The receptionist is on (its widget answers on dibodev.fr); the Apple Wallet cards are off until they are finished.
Re-runnable: an existing switch is never overwritten.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from sqlalchemy import text

from core.clock import naive_utc_now
from core.database import engine
from models.product_module_state import ProductModuleState

_INITIAL_SWITCHES: tuple[tuple[str, bool], ...] = (("ai-assistant", True), ("apple-wallet", False))


def run_migration() -> None:
    """Create the table if needed, then insert each missing switch."""
    ProductModuleState.__table__.create(engine, checkfirst=True)
    with engine.begin() as conn:
        for module_key, is_enabled in _INITIAL_SWITCHES:
            already_stored = conn.execute(
                text("SELECT 1 FROM product_modules WHERE module_key = :module_key"), {"module_key": module_key}
            ).first()
            if already_stored is not None:
                continue
            conn.execute(
                text(
                    "INSERT INTO product_modules (module_key, is_enabled, updated_at) "
                    "VALUES (:module_key, :is_enabled, :updated_at)"
                ),
                {"module_key": module_key, "is_enabled": is_enabled, "updated_at": naive_utc_now()},
            )


if __name__ == "__main__":
    run_migration()
    print("product_modules ensured.")
