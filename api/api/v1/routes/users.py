"""
User management routes (admin only).
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.user import UserCreate, UserResponse, UserUpdate
from services.auth_service import require_admin, get_password_hash
from services.credit_service import credit_service, TransactionType
from models.user import User
from models.credit_settings import CreditSettings

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get all users (admin only).
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        List of users with credit balances
    """
    users = db.query(User).offset(skip).limit(limit).all()
    
    # Add credit balance, available, and consumed to each user
    result = []
    for user in users:
        balance = credit_service.get_user_balance(db, user.id)
        credits_available = balance
        credits_consumed = credit_service.get_user_credits_consumed(db, user.id)
        
        user_dict = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "credit_balance": balance,
            "credits_available": credits_available,
            "credits_consumed": credits_consumed
        }
        result.append(UserResponse(**user_dict))
    
    return result


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get a specific user by ID (admin only).
    
    Args:
        user_id: User ID
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        User information with credit balance
        
    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Add credit balance, available, and consumed
    balance = credit_service.get_user_balance(db, user.id)
    credits_available = balance
    credits_consumed = credit_service.get_user_credits_consumed(db, user.id)
    
    user_dict = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "credit_balance": balance,
        "credits_available": credits_available,
        "credits_consumed": credits_consumed
    }
    return UserResponse(**user_dict)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new user (admin only).
    
    Args:
        user_data: User creation data
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        Created user
        
    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        role=user_data.role.value if hasattr(user_data.role, 'value') else user_data.role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Give free credits on signup (only for regular users, not admins)
    if db_user.role != "ADMIN":
        credit_settings = db.query(CreditSettings).filter(CreditSettings.id == 1).first()
        if credit_settings and credit_settings.free_credits_on_signup > 0:
            credit_service.add_credits(
                db=db,
                user_id=db_user.id,
                amount=credit_settings.free_credits_on_signup,
                description=f"Free credits on signup ({credit_settings.free_credits_on_signup} credits)",
                transaction_type=TransactionType.FREE_GIFT
            )
    
    # Return user with credit balance, available, and consumed
    balance = credit_service.get_user_balance(db, db_user.id)
    credits_available = balance
    credits_consumed = credit_service.get_user_credits_consumed(db, db_user.id)
    
    user_dict = {
        "id": db_user.id,
        "name": db_user.name,
        "email": db_user.email,
        "role": db_user.role,
        "is_active": db_user.is_active,
        "created_at": db_user.created_at,
        "updated_at": db_user.updated_at,
        "credit_balance": balance,
        "credits_available": credits_available,
        "credits_consumed": credits_consumed
    }
    return UserResponse(**user_dict)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Any:
    """
    Update a user (admin only).
    
    Args:
        user_id: User ID
        user_data: Updated user data
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        Updated user
        
    Raises:
        HTTPException: If user not found or email already exists
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if email is being changed and if it's already taken
    if user_data.email and user_data.email != user.email:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Update user fields
    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        user.email = user_data.email
    
    db.commit()
    db.refresh(user)
    
    # Return user with credit balance, available, and consumed
    balance = credit_service.get_user_balance(db, user.id)
    credits_available = balance
    credits_consumed = credit_service.get_user_credits_consumed(db, user.id)
    
    user_dict = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "credit_balance": balance,
        "credits_available": credits_available,
        "credits_consumed": credits_consumed
    }
    return UserResponse(**user_dict)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> None:
    """
    Delete a user (admin only).
    
    Args:
        user_id: User ID
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        No content
        
    Raises:
        HTTPException: If user not found or trying to delete own account
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting own account
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()

