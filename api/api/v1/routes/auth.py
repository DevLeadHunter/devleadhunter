"""
Authentication routes for user signup and login.
"""
from typing import Any
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import settings
from core.database import get_db
from schemas.user import UserCreate, UserResponse, Token, UserLogin
from services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_password_hash,
    get_user_by_email,
    get_user_by_id
)
from services.credit_service import credit_service
from models.user import User

router = APIRouter(prefix="/auth", tags=["authentication"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Limit signup attempts to prevent abuse
async def signup(
    request: Request,
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Create a new user account.
    
    Args:
        user_data: User creation data
        db: Database session
        
    Returns:
        Created user
        
    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    existing_user = get_user_by_email(db, user_data.email)
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
    
    # Add credit balance, available, and consumed
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


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")  # Limit login attempts to prevent brute force
async def login(
    request: Request,
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
) -> Any:
    """
    Login with email and password.
    
    Args:
        user_credentials: User login credentials
        db: Database session
        
    Returns:
        Access token
        
    Raises:
        HTTPException: If credentials are invalid
    """
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Current user information with credit balance
    """
    # Add credit balance, available, and consumed
    balance = credit_service.get_user_balance(db, current_user.id)
    credits_available = balance
    credits_consumed = credit_service.get_user_credits_consumed(db, current_user.id)
    
    user_dict = {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
        "credit_balance": balance,
        "credits_available": credits_available,
        "credits_consumed": credits_consumed
    }
    return UserResponse(**user_dict)

