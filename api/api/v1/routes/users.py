"""
User management routes (super-admin only).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from enums.user_role import UserRole, has_unlimited_credits
from models.credit_settings import CreditSettings
from models.user import User
from schemas.user import AdminUserUpdate, UserCreate, UserResponse
from services.auth_service import AuthService, require_super_admin
from services.credit_service import TransactionType, credit_service

router = APIRouter(prefix="/users", tags=["users"])

_ASSIGNABLE_ROLES: frozenset[str] = frozenset({UserRole.USER.value, UserRole.ADMIN.value})


def _serialize_user(db: Session, user: User) -> UserResponse:
    """Build a :class:`UserResponse` with live credit figures."""
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


def _normalize_assignable_role(role: UserRole | str) -> str:
    """Return a role value that may be assigned by a super-admin."""
    value = role.value if hasattr(role, "value") else str(role)
    if value not in _ASSIGNABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only USER and ADMIN roles can be assigned",
        )
    return value


@router.get("", response_model=list[UserResponse])
async def get_users(
    skip: int = 0, limit: int = 100, current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)
) -> Any:
    """List every user (super-admin only)."""
    users = db.query(User).offset(skip).limit(limit).all()
    return [_serialize_user(db, user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int, current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)
) -> Any:
    """Return one user by id (super-admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _serialize_user(db, user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate, current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)
) -> Any:
    """Create a user (super-admin only)."""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    role = _normalize_assignable_role(user_data.role)
    hashed_password = AuthService.hash_password(user_data.password)
    db_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        role=role,
        company_name=user_data.company_name.strip() if user_data.company_name else None,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    if not has_unlimited_credits(db_user.role):
        credit_settings = db.query(CreditSettings).filter(CreditSettings.id == 1).first()
        if credit_settings and credit_settings.free_credits_on_signup > 0:
            credit_service.add_credits(
                db=db,
                user_id=db_user.id,
                amount=credit_settings.free_credits_on_signup,
                description=f"Free credits on signup ({credit_settings.free_credits_on_signup} credits)",
                transaction_type=TransactionType.FREE_GIFT,
            )

    return _serialize_user(db, db_user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: AdminUserUpdate,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> Any:
    """Update a user, including role promotion to ADMIN (super-admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user_data.email and user_data.email != user.email:
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    if user_data.name is not None:
        user.name = user_data.name
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.company_name is not None:
        user.company_name = user_data.company_name.strip() or None
    if user_data.is_active is not None:
        user.is_active = user_data.is_active
    if user_data.role is not None:
        if user.id == current_user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role")
        if user.role == UserRole.SUPER_ADMIN.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change a super-admin role")
        user.role = _normalize_assignable_role(user_data.role)

    db.commit()
    db.refresh(user)
    return _serialize_user(db, user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, current_user: User = Depends(require_super_admin), db: Session = Depends(get_db)
) -> None:
    """Delete a user (super-admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")
    if user.role == UserRole.SUPER_ADMIN.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete a super-admin account")

    db.delete(user)
    db.commit()
