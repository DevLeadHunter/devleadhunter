"""
User seeder to create initial admin user and sample users.
"""
from sqlalchemy.orm import Session
from faker import Faker

from core.config import settings
from core.database import get_db, init_db
from models.user import User
from services.auth_service import get_password_hash, get_user_by_email
from enums.user_role import UserRole

# Initialize Faker
fake = Faker()


def seed_admin_user() -> None:
    """
    Create admin user if it doesn't exist.
    
    This function creates an admin user with credentials from environment variables.
    """
    # Initialize database tables
    init_db()
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if admin user already exists
        existing_admin = get_user_by_email(db, settings.admin_email)
        if existing_admin:
            print(f"[OK] Admin user already exists: {settings.admin_email}")
        else:
            # Create admin user
            admin_user = User(
                name="Léo Guillaume",
                email=settings.admin_email,
                hashed_password=get_password_hash(settings.admin_password),
                role=UserRole.ADMIN.value,
                is_active=True
            )
            
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            
            print(f"[OK] Admin user created: {settings.admin_email}")
        
        # Create 10 random users
        users_created = 0
        for i in range(10):
            random_name = fake.name()
            random_email = fake.email()
            
            # Check if user already exists
            existing_user = get_user_by_email(db, random_email)
            if existing_user:
                continue
            
            # Create random user
            random_user = User(
                name=random_name,
                email=random_email,
                hashed_password=get_password_hash("password123"),  # Default password for random users
                role=UserRole.USER.value,
                is_active=True
            )
            
            db.add(random_user)
            users_created += 1
        
        if users_created > 0:
            db.commit()
            print(f"[OK] Created {users_created} random users")
        else:
            print(f"[OK] Random users already exist")
        
    except Exception as e:
        print(f"[ERROR] Failed to seed users: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin_user()

