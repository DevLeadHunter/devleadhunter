"""
Migration — create the acquisition orchestrator tables.

Idempotent: uses ``checkfirst=True`` so re-running on an existing DB is a no-op.
Parent table (``acquisition_runs``) is created before the child
(``acquisition_run_items``) to satisfy the foreign key.
"""

import os
import sys

# Allow running as a standalone module (mirror add_scraper_diagnostics.py).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import engine
from models.acquisition_run import AcquisitionRun
from models.acquisition_run_item import AcquisitionRunItem


def run_migration() -> None:
    """Create ``acquisition_runs`` then ``acquisition_run_items`` (idempotent)."""
    AcquisitionRun.__table__.create(engine, checkfirst=True)
    AcquisitionRunItem.__table__.create(engine, checkfirst=True)


if __name__ == "__main__":
    run_migration()
    print("✓ acquisition tables ready")
