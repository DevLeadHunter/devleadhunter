"""Create the scraper_diagnostics table (admin monitoring of source health)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import engine
from models.scraper_diagnostic import ScraperDiagnostic


def run_migration() -> None:
    """Create the ``scraper_diagnostics`` table if it does not exist (idempotent)."""
    ScraperDiagnostic.__table__.create(engine, checkfirst=True)


if __name__ == "__main__":
    run_migration()
    print("scraper_diagnostics table ensured.")
