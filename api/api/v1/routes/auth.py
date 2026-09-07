"""
Authentication routes for user signup and login.
"""

import asyncio
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.rate_limiter import limiter
from enums.user_role import UserRole
from models.credit_settings import CreditSettings
from models.user import User
from schemas.user import ProfilePhotoResponse, Token, UserLogin, UserResponse, UserSignup, UserUpdate
from services.activity_log_service import CATEGORY_AUTH, STATUS_INFO, activity_log_service
from services.auth_service import AuthService, get_current_active_user
from services.credit_service import TransactionType, credit_service
from services.profile_photo_service import profile_photo_service
from services.r2_storage_service import r2_storage

router = APIRouter(prefix="/auth", tags=["authentication"])


def _build_user_response(db: Session, user: User) -> UserResponse:
    """
    Serialize a user with their live credit figures.

    Single place where the ``/auth`` payload is shaped, so every route that
    returns a user (signup, me, profile update, onboarding) stays in sync.

    Args:
        db: Database session.
        user: The user to serialize.

    Returns:
        The user response, credit balance included.
    """
    balance = credit_service.get_user_balance(db, user.id)
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        company_name=user.company_name,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        onboarding_completed=user.onboarding_completed,
        site_sale_price_cents=user.site_sale_price_cents,
        credit_balance=balance,
        credits_available=balance,
        credits_consumed=credit_service.get_user_credits_consumed(db, user.id),
    )


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")  # Limit signup attempts to prevent abuse
async def signup(request: Request, user_data: UserSignup, db: Session = Depends(get_db)) -> Any:
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
    existing_user = AuthService.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create new user — role is always USER on public signup.
    hashed_password = AuthService.hash_password(user_data.password)
    db_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        role=UserRole.USER.value,
        company_name=user_data.company_name.strip() if user_data.company_name else None,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    credit_settings = db.query(CreditSettings).filter(CreditSettings.id == 1).first()
    if credit_settings and credit_settings.free_credits_on_signup > 0:
        credit_service.add_credits(
            db=db,
            user_id=db_user.id,
            amount=credit_settings.free_credits_on_signup,
            description=f"Free credits on signup ({credit_settings.free_credits_on_signup} credits)",
            transaction_type=TransactionType.FREE_GIFT,
        )

    activity_log_service.record(
        category=CATEGORY_AUTH,
        action="user_signup",
        status=STATUS_INFO,
        title=f"Inscription · {db_user.name}",
        detail=db_user.email,
        user_id=db_user.id,
    )

    return _build_user_response(db, db_user)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")  # Limit login attempts to prevent brute force
async def login(request: Request, user_credentials: UserLogin, db: Session = Depends(get_db)) -> Any:
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
    user = AuthService.authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = AuthService.create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)

    activity_log_service.record(
        category=CATEGORY_AUTH,
        action="user_login",
        status=STATUS_INFO,
        title=f"Connexion · {user.name}",
        user_id=user.id,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> Any:
    """
    Get current user information.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Current user information with credit balance
    """
    return _build_user_response(db, current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user_info(
    user_data: UserUpdate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> Any:
    """
    Update the current user's own profile (name and/or email).

    Self-service counterpart of the admin ``PUT /users/{id}``: a user can only edit
    their own account. When the email changes it must not collide with another
    account; note that the email is the JWT subject, so after an email change the
    current token becomes stale and the user must re-authenticate.

    Args:
        user_data: Partial update (name and/or email).
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        The updated user, with credit balance.

    Raises:
        HTTPException: If the new email is already registered to another account.
    """
    if user_data.email and user_data.email != current_user.email:
        existing_user = AuthService.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    if user_data.name is not None:
        current_user.name = user_data.name
    if user_data.email is not None:
        current_user.email = user_data.email
    if user_data.site_sale_price_cents is not None:
        current_user.site_sale_price_cents = user_data.site_sale_price_cents
    if user_data.company_name is not None:
        current_user.company_name = user_data.company_name.strip() or None
    if user_data.company_website_url is not None:
        current_user.company_website_url = user_data.company_website_url.strip() or None

    db.commit()
    db.refresh(current_user)

    return _build_user_response(db, current_user)


@router.get("/me/photo", response_model=ProfilePhotoResponse)
async def get_profile_photo(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Return whether the current user has a profile photo."""
    return {"has_photo": bool(current_user.profile_photo_path)}


@router.put("/me/photo", response_model=ProfilePhotoResponse)
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Upload (or replace) the profile photo (today: the video-thumbnail bubble)."""
    await profile_photo_service.store_photo(db, current_user, file)
    return {"has_photo": True}


@router.delete("/me/photo", response_model=ProfilePhotoResponse)
async def delete_profile_photo(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Any:
    """Delete the profile photo (file + user column)."""
    profile_photo_service.delete_photo(db, current_user)
    return {"has_photo": False}


@router.get("/me/photo/file")
async def stream_profile_photo_file(
    current_user: User = Depends(get_current_active_user),
) -> StreamingResponse:
    """Stream the user's own profile photo from R2 (profile preview + desktop build)."""
    stored = str(current_user.profile_photo_path or "")
    if not stored:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune photo de profil.")
    try:
        body, content_type, size = await asyncio.to_thread(r2_storage.open_stream, stored)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Le fichier de la photo est introuvable."
        ) from error
    headers = {"Content-Length": str(size)} if size else None
    return StreamingResponse(body.iter_chunks(), media_type=content_type, headers=headers)


@router.post("/me/complete-onboarding", response_model=UserResponse)
async def complete_onboarding(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
) -> Any:
    """
    Mark the post-signup setup wizard as completed for the current user.

    Called by the last step of ``/configuration``. Idempotent: replaying it on an
    already-onboarded account is a no-op that still returns the user.

    Args:
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        The updated user.
    """
    if not current_user.onboarding_completed:
        current_user.onboarding_completed = True
        db.commit()
        db.refresh(current_user)

    return _build_user_response(db, current_user)
