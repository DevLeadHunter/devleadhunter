"""
Migration: create the ``resend_config`` table.

Run with:
    python migrations/add_resend_config.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine
from models.resend_config import ResendConfig


def run_migration() -> None:
    """Create the resend_config table if it does not already exist."""
    print("Running migration: add_resend_config")
    ResendConfig.__table__.create(engine, checkfirst=True)
    print("  + resend_config table")
    print("Migration completed successfully.")


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add Resend Config")
    print("=" * 60)
    run_migration()
