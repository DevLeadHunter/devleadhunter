"""
Credit settings seeder to create initial credit configuration.
"""
from decimal import Decimal
from sqlalchemy.orm import Session

from core.database import get_db, init_db
from models.credit_settings import CreditSettings


def seed_credit_settings() -> None:
    """
    Create credit settings if they don't exist.
    
    This function creates the default credit settings with the following values:
    - Price per credit: 0.10 EUR
    - Credits per search: 5
    - Credits per result: 1
    - Credits per email: 3
    - Free credits on signup: 15
    - Minimum credits purchase: 10
    """
    # Initialize database tables
    init_db()
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        # Check if credit settings already exist
        existing_settings = db.query(CreditSettings).filter(CreditSettings.id == 1).first()
        if existing_settings:
            print("[OK] Credit settings already exist")
        else:
            # Create default credit settings
            credit_settings = CreditSettings(
                id=1,
                price_per_credit=Decimal("0.10"),
                credits_per_search=5,
                credits_per_result=1,
                credits_per_email=3,
                free_credits_on_signup=15,
                minimum_credits_purchase=10
            )
            
            db.add(credit_settings)
            db.commit()
            db.refresh(credit_settings)
            
            print("[OK] Credit settings created successfully")
            print(f"  - Price per credit: {credit_settings.price_per_credit} EUR")
            print(f"  - Credits per search: {credit_settings.credits_per_search}")
            print(f"  - Credits per result: {credit_settings.credits_per_result}")
            print(f"  - Credits per email: {credit_settings.credits_per_email}")
            print(f"  - Free credits on signup: {credit_settings.free_credits_on_signup}")
            print(f"  - Minimum credits purchase: {credit_settings.minimum_credits_purchase}")
    
    except Exception as e:
        print(f"[ERROR] Failed to seed credit settings: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_credit_settings()

