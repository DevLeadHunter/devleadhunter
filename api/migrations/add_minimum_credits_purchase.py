"""
Migration script to add minimum_credits_purchase column to credit_settings table.
Run this script once to update existing databases.
"""

import os
import sys

# Add api root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from core.database import engine


def add_minimum_credits_purchase_column():
    """
    Add minimum_credits_purchase column to credit_settings table.

    This script is safe to run multiple times - it checks if the column exists first.
    """
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(
            text("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'credit_settings' 
            AND COLUMN_NAME = 'minimum_credits_purchase'
        """)
        )
        column_exists = result.scalar() > 0

        if column_exists:
            print("[OK] Column 'minimum_credits_purchase' already exists")
        else:
            # Add the column
            conn.execute(
                text("""
                ALTER TABLE credit_settings 
                ADD COLUMN minimum_credits_purchase INT NOT NULL DEFAULT 10 
                COMMENT 'Minimum number of credits that can be purchased'
            """)
            )
            conn.commit()
            print("[OK] Column 'minimum_credits_purchase' added successfully")

        # Update existing rows to have the default value if they don't have it
        conn.execute(
            text("""
            UPDATE credit_settings 
            SET minimum_credits_purchase = 10 
            WHERE minimum_credits_purchase IS NULL OR minimum_credits_purchase = 0
        """)
        )
        conn.commit()
        print("[OK] Existing records updated with default value")


def run_migration() -> None:
    """Add minimum_credits_purchase column to credit_settings."""
    add_minimum_credits_purchase_column()


if __name__ == "__main__":
    print("Running migration: Add minimum_credits_purchase to credit_settings")
    print()
    try:
        run_migration()
        print()
        print("Migration complete!")
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)
