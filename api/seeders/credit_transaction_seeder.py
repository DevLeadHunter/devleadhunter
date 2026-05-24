"""
Credit transaction seeder to create initial credit transactions for users.
"""
from datetime import datetime, timedelta
import random
from sqlalchemy.orm import Session

from core.database import get_db, init_db
from models.user import User
from models.credit_settings import CreditSettings
from models.credit_transaction import CreditTransaction
from services.credit_service import credit_service, TransactionType


def seed_credit_transactions() -> None:
    """
    Create credit transactions for existing users.
    
    This function:
    1. Gives free credits on signup to all users (based on credit_settings)
    2. Adds some sample purchase transactions for test users
    3. Adds fake usage transactions spread over the last 30 days for graph visualization
    """
    # Initialize database tables
    init_db()
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        # Get credit settings to know how many free credits to give
        credit_settings = db.query(CreditSettings).filter(CreditSettings.id == 1).first()
        free_credits = credit_settings.free_credits_on_signup if credit_settings else 15
        
        # Get all users
        users = db.query(User).all()
        
        if not users:
            print("[INFO] No users found. Please run user seeder first.")
            return
        
        transactions_created = 0
        
        for user in users:
            # Skip admin users (they have unlimited credits)
            if user.role == "ADMIN":
                print(f"[SKIP] Admin user {user.email} has unlimited credits")
                continue
            
            # Check if user already has transactions
            existing_transactions = credit_service.get_user_transactions(db, user.id, limit=1)
            if existing_transactions:
                print(f"[SKIP] User {user.email} already has transactions")
                continue
            
            # Give free credits on signup
            credit_service.add_credits(
                db=db,
                user_id=user.id,
                amount=free_credits,
                description=f"Free credits on signup ({free_credits} credits)",
                transaction_type=TransactionType.FREE_GIFT
            )
            transactions_created += 1
            print(f"[OK] Added {free_credits} free credits to {user.email}")
            
            # Add a sample purchase for some users (randomly)
            # Ensure users have enough credits before creating usage transactions
            base_credits = free_credits
            if user.id % 2 == 0:  # Every other user gets a purchase
                purchase_amount = 200
                credit_service.add_credits(
                    db=db,
                    user_id=user.id,
                    amount=purchase_amount,
                    description=f"Credit purchase ({purchase_amount} credits for €{purchase_amount * 0.10:.2f})",
                    transaction_type=TransactionType.PURCHASE
                )
                transactions_created += 1
                base_credits += purchase_amount
                print(f"[OK] Added {purchase_amount} purchased credits to {user.email}")
            
            # Calculate total credits available before creating usage
            total_available_credits = base_credits
            
            # Add fake usage transactions for graph visualization
            # Create usage transactions over the last 30 days
            # But ensure total usage doesn't exceed available credits
            usage_transactions = _generate_fake_usage_transactions(
                user.id, 
                max_total_usage=int(total_available_credits * 0.7)  # Use max 70% of available credits
            )
            
            # Track total usage to ensure we don't exceed available credits
            total_usage = 0
            created_usage = 0
            
            for transaction_data in usage_transactions:
                usage_amount = abs(transaction_data['amount'])  # Get positive value
                
                # Only create if we won't exceed 70% of available credits
                if total_usage + usage_amount <= int(total_available_credits * 0.7):
                    transaction = CreditTransaction(
                        user_id=user.id,
                        transaction_type=TransactionType.USAGE,
                        amount=transaction_data['amount'],
                        description=transaction_data['description'],
                        transaction_metadata=transaction_data.get('metadata'),
                        created_at=transaction_data['created_at']
                    )
                    db.add(transaction)
                    db.commit()
                    db.refresh(transaction)
                    transactions_created += 1
                    created_usage += 1
                    total_usage += usage_amount
                else:
                    # Skip this transaction to avoid negative balance
                    break
            
            print(f"[OK] Added {created_usage} usage transactions ({total_usage} credits used) to {user.email}")
        
        if transactions_created > 0:
            print(f"[OK] Created {transactions_created} credit transactions")
        else:
            print("[OK] Credit transactions already exist for all users")
    
    except Exception as e:
        print(f"[ERROR] Failed to seed credit transactions: {e}")
        db.rollback()
    finally:
        db.close()


def _generate_fake_usage_transactions(user_id: int, max_total_usage: int = 300) -> list[dict]:
    """
    Generate fake credit usage transactions spread over the last 30 days.
    
    Args:
        user_id: User ID (not used but kept for consistency)
        max_total_usage: Maximum total credits that can be used (default: 300)
        
    Returns:
        List of transaction data dictionaries sorted by date (oldest first)
    """
    transactions = []
    now = datetime.utcnow()
    total_usage = 0
    
    # Usage scenarios with descriptions
    usage_scenarios = [
        {"description": "Prospect search - Restaurant in Paris", "amount_range": (5, 15)},
        {"description": "Prospect search - Plumber in Lyon", "amount_range": (3, 10)},
        {"description": "Email campaign sent to 25 prospects", "amount_range": (25, 50)},
        {"description": "Prospect search - Electrician in Marseille", "amount_range": (4, 12)},
        {"description": "Email campaign sent to 15 prospects", "amount_range": (15, 30)},
        {"description": "Prospect search - Hair salon in Bordeaux", "amount_range": (5, 15)},
        {"description": "Email campaign sent to 40 prospects", "amount_range": (40, 80)},
        {"description": "Prospect search - Garage in Toulouse", "amount_range": (4, 10)},
    ]
    
    # Generate transactions over the last 30 days
    # Create 15-25 usage transactions randomly distributed, but respect max_total_usage
    num_transactions = random.randint(15, 25)
    
    for i in range(num_transactions):
        # Check if we've reached the max usage
        if total_usage >= max_total_usage:
            break
        
        # Random date within the last 30 days
        days_ago = random.randint(0, 30)
        transaction_date = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        # Pick a random usage scenario
        scenario = random.choice(usage_scenarios)
        max_amount = min(
            scenario["amount_range"][1],
            max_total_usage - total_usage  # Don't exceed remaining budget
        )
        min_amount = min(scenario["amount_range"][0], max_amount)
        
        if max_amount <= 0:
            break
        
        amount_value = random.randint(min_amount, max_amount)
        amount = -amount_value
        total_usage += amount_value
        
        transactions.append({
            "amount": amount,
            "description": scenario["description"],
            "metadata": f'{{"created_at": "{transaction_date.isoformat()}"}}',
            "created_at": transaction_date
        })
    
    # Sort by date (oldest first)
    transactions.sort(key=lambda x: x["created_at"])
    
    return transactions


if __name__ == "__main__":
    seed_credit_transactions()

