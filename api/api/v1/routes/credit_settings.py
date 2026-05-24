"""
Credit settings management routes (admin only).
"""
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.credit_settings import CreditSettingsResponse, CreditSettingsUpdate
from services.auth_service import require_admin
from models.credit_settings import CreditSettings

router = APIRouter(prefix="/credit-settings", tags=["credit-settings"])


@router.get("", response_model=CreditSettingsResponse)
async def get_credit_settings(
    db: Session = Depends(get_db)
) -> CreditSettingsResponse:
    """
    Get current credit settings (public read access).
    
    Args:
        db: Database session
        
    Returns:
        Current credit settings
        
    Raises:
        HTTPException: If settings not found
    """
    settings: CreditSettings | None = db.query(CreditSettings).filter(CreditSettings.id == 1).first()
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit settings not found. Please run the seeder to initialize settings."
        )
    return settings


@router.put("", response_model=CreditSettingsResponse)
async def update_credit_settings(
    settings_data: CreditSettingsUpdate,
    current_user: Any = Depends(require_admin),
    db: Session = Depends(get_db)
) -> CreditSettingsResponse:
    """
    Update credit settings (admin only).
    
    Args:
        settings_data: Updated credit settings data
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        Updated credit settings
        
    Raises:
        HTTPException: If settings not found or validation fails
    """
    # Get existing settings
    settings: CreditSettings | None = db.query(CreditSettings).filter(CreditSettings.id == 1).first()
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit settings not found. Please run the seeder to initialize settings."
        )
    
    # Update fields if provided
    if settings_data.price_per_credit is not None:
        settings.price_per_credit = settings_data.price_per_credit
    if settings_data.credits_per_search is not None:
        settings.credits_per_search = settings_data.credits_per_search
    if settings_data.credits_per_result is not None:
        settings.credits_per_result = settings_data.credits_per_result
    if settings_data.credits_per_email is not None:
        settings.credits_per_email = settings_data.credits_per_email
    if settings_data.free_credits_on_signup is not None:
        settings.free_credits_on_signup = settings_data.free_credits_on_signup
    if settings_data.minimum_credits_purchase is not None:
        settings.minimum_credits_purchase = settings_data.minimum_credits_purchase
    
    db.commit()
    db.refresh(settings)
    
    return settings

