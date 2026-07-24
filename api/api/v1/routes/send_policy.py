"""
Send policy routes — the user's global cold-email cadence (Paramètres → Envoi).

Governs the whole email queue: daily cap, allowed weekdays and hours, spacing.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from services.auth_service import get_current_user
from services.send_policy_service import send_policy_service

router = APIRouter(prefix="/send-policy", tags=["send-policy"])


class SendPolicyResponse(BaseModel):
    """Effective send policy (a saved row, or the defaults)."""

    daily_cap: int
    days_of_week: list[int]
    window_start_hour: int
    window_end_hour: int
    spacing_minutes: int


class SendPolicyUpdate(BaseModel):
    """Payload to update the send policy."""

    daily_cap: int = Field(..., ge=1, le=500)
    days_of_week: list[int] = Field(..., min_length=1)
    window_start_hour: int = Field(..., ge=0, le=23)
    window_end_hour: int = Field(..., ge=1, le=24)
    spacing_minutes: int = Field(..., ge=1, le=1440)


def _resolved(db: Session, user_id: int) -> SendPolicyResponse:
    """Build a response from the resolved policy."""
    r = send_policy_service.resolve(db, user_id)
    return SendPolicyResponse(
        daily_cap=r.daily_cap,
        days_of_week=r.days_of_week,
        window_start_hour=r.window_start_hour,
        window_end_hour=r.window_end_hour,
        spacing_minutes=r.spacing_minutes,
    )


@router.get("", response_model=SendPolicyResponse)
async def get_send_policy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SendPolicyResponse:
    """Return the user's effective send policy (defaults when unset)."""
    return _resolved(db, current_user.id)


@router.put("", response_model=SendPolicyResponse)
async def update_send_policy(
    data: SendPolicyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SendPolicyResponse:
    """Create or update the user's send policy."""
    send_policy_service.upsert(
        db,
        current_user.id,
        daily_cap=data.daily_cap,
        days_of_week=data.days_of_week,
        window_start_hour=data.window_start_hour,
        window_end_hour=data.window_end_hour,
        spacing_minutes=data.spacing_minutes,
    )
    return _resolved(db, current_user.id)
