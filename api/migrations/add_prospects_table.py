"""
Migration to add prospects table to database.

Run this migration to create the prospects table.
"""
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import engine, Base
from models.prospect_db import ProspectDB
from models.user import User

def run_migration():
    """
    Run the migration to create prospects table.
    
    This migration will:
    1. Create the prospects table if it doesn't exist
    2. Leave existing data untouched
    """
    print("🔄 Running migration: add_prospects_table")
    
    try:
        # Create only the prospects table
        ProspectDB.__table__.create(engine, checkfirst=True)
        
        print("✅ Migration completed successfully")
        print("   - Created prospects table")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add Prospects Table")
    print("=" * 60)
    
    run_migration()
    
    print("\n" + "=" * 60)
    print("Migration completed!")
    print("=" * 60)

