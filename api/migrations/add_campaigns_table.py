"""
Migration script to add campaigns and campaign_prospects tables.

This migration creates:
1. campaigns table for storing email campaigns
2. campaign_prospects table for many-to-many relationship
3. Updates email_logs to use campaign foreign key

Run this script to apply the migration:
    python migrations/add_campaigns_table.py
"""
from sqlalchemy import create_engine, text
from core.config import settings


def run_migration():
    """Run the migration to add campaigns tables."""
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        print("Starting migration: add_campaigns_table")
        
        # Create campaigns table
        print("Creating campaigns table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'draft',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
                
                INDEX idx_campaigns_user_id (user_id),
                INDEX idx_campaigns_status (status),
                
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """))
        conn.commit()
        print("✓ campaigns table created")
        
        # Create campaign_prospects junction table
        print("Creating campaign_prospects table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS campaign_prospects (
                campaign_id INT NOT NULL,
                prospect_id INT NOT NULL,
                added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                
                PRIMARY KEY (campaign_id, prospect_id),
                INDEX idx_campaign_prospects_campaign (campaign_id),
                INDEX idx_campaign_prospects_prospect (prospect_id),
                
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
                FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """))
        conn.commit()
        print("✓ campaign_prospects table created")
        
        # Check if email_logs table exists and needs updating
        print("Checking email_logs table...")
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'email_logs'
            AND COLUMN_NAME = 'campaign_id';
        """))
        
        column_exists = result.fetchone()[0] > 0
        
        if not column_exists:
            print("Adding campaign_id column to email_logs...")
            
            # First, add the column as INT
            conn.execute(text("""
                ALTER TABLE email_logs 
                ADD COLUMN campaign_id INT DEFAULT NULL AFTER prospect_id;
            """))
            conn.commit()
            
            # Add index
            conn.execute(text("""
                ALTER TABLE email_logs 
                ADD INDEX idx_email_logs_campaign_id (campaign_id);
            """))
            conn.commit()
            
            # Add foreign key
            conn.execute(text("""
                ALTER TABLE email_logs 
                ADD CONSTRAINT fk_email_logs_campaign
                FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL;
            """))
            conn.commit()
            
            print("✓ email_logs table updated with campaign_id")
        else:
            print("✓ email_logs table already has campaign_id column")
        
        # Also update prospect_id in email_logs to be INT if it's not already
        print("Checking prospect_id column type in email_logs...")
        result = conn.execute(text("""
            SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'email_logs'
            AND COLUMN_NAME = 'prospect_id';
        """))
        
        col_info = result.fetchone()
        if col_info and col_info[0] == 'varchar':
            print("Converting prospect_id from VARCHAR to INT...")
            
            # Clear non-numeric values first (set to NULL)
            conn.execute(text("""
                UPDATE email_logs 
                SET prospect_id = NULL 
                WHERE prospect_id IS NOT NULL 
                AND prospect_id REGEXP '^[0-9]+$' = 0;
            """))
            conn.commit()
            
            # Modify column type
            conn.execute(text("""
                ALTER TABLE email_logs 
                MODIFY COLUMN prospect_id INT DEFAULT NULL;
            """))
            conn.commit()
            
            print("✓ prospect_id column converted to INT")
        else:
            print("✓ prospect_id column is already INT")
        
        print("\n✅ Migration completed successfully!")
        print("\nNew tables:")
        print("  - campaigns")
        print("  - campaign_prospects")
        print("\nUpdated tables:")
        print("  - email_logs (added campaign_id foreign key)")


def rollback_migration():
    """Rollback the migration (drop tables)."""
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        print("Rolling back migration: add_campaigns_table")
        
        # Drop foreign key from email_logs first
        try:
            print("Removing foreign key from email_logs...")
            conn.execute(text("""
                ALTER TABLE email_logs 
                DROP FOREIGN KEY IF EXISTS fk_email_logs_campaign;
            """))
            conn.commit()
            
            # Drop campaign_id column
            conn.execute(text("""
                ALTER TABLE email_logs 
                DROP COLUMN IF EXISTS campaign_id;
            """))
            conn.commit()
            print("✓ Removed campaign_id from email_logs")
        except Exception as e:
            print(f"Note: {e}")
        
        # Drop campaign_prospects table
        print("Dropping campaign_prospects table...")
        conn.execute(text("DROP TABLE IF EXISTS campaign_prospects;"))
        conn.commit()
        print("✓ campaign_prospects table dropped")
        
        # Drop campaigns table
        print("Dropping campaigns table...")
        conn.execute(text("DROP TABLE IF EXISTS campaigns;"))
        conn.commit()
        print("✓ campaigns table dropped")
        
        print("\n✅ Rollback completed successfully!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()

