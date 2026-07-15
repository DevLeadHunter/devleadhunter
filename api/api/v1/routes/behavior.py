"""Prospect behaviour routes — lead scoring, timeline, AI summary, personalised relance."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.prospect_db import ProspectDB
from models.user import User
from schemas.behavior import (
    BehaviorSummaryResponse,
    PersonalizedFollowupResponse,
    ProspectBehaviorResponse,
)
from services.auth_service import get_current_active_user
from services.behavior_service import behavior_service

router = APIRouter(prefix="/prospects", tags=["behavior"])

# Default base relance used when drafting a personalised follow-up on demand.
_DEFAULT_BASE_SUBJECT = "Votre site web — on en parle ?"
_DEFAULT_BASE_BODY = (
    "<p>Bonjour,</p><p>Je reviens vers vous au sujet de la démo de site web que je vous ai préparée. "
    "Je serais ravi d'avoir votre retour et de répondre à vos questions.</p>"
    "<p>Bien à vous,</p>"
)


def _get_prospect(db: Session, user_id: int, prospect_id: int) -> ProspectDB:
    """Fetch a prospect owned by the user, or 404."""
    prospect = (
        db.query(ProspectDB)
        .filter(ProspectDB.id == prospect_id, ProspectDB.user_id == user_id)
        .first()
    )
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    return prospect


@router.get("/{prospect_id}/behavior", response_model=ProspectBehaviorResponse)
async def get_prospect_behavior(
    prospect_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProspectBehaviorResponse:
    """Return the lead score, signals and behaviour timeline for a prospect."""
    _get_prospect(db, current_user.id, prospect_id)
    data = await behavior_service.get_behavior(db, current_user.id, prospect_id)
    return ProspectBehaviorResponse(**data)


@router.post("/{prospect_id}/behavior/summary", response_model=BehaviorSummaryResponse)
async def summarize_prospect_behavior(
    prospect_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> BehaviorSummaryResponse:
    """Generate an AI (or rule-based) read of the prospect's demo behaviour."""
    prospect = _get_prospect(db, current_user.id, prospect_id)
    summary = await behavior_service.get_summary(db, current_user.id, prospect)
    return BehaviorSummaryResponse(summary=summary)


@router.post("/{prospect_id}/personalized-followup", response_model=PersonalizedFollowupResponse)
async def draft_personalized_followup(
    prospect_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PersonalizedFollowupResponse:
    """Draft a behaviour-personalised follow-up email (to review before sending)."""
    prospect = _get_prospect(db, current_user.id, prospect_id)
    draft = await behavior_service.draft_personalized_followup(
        db,
        current_user.id,
        prospect,
        base_subject=_DEFAULT_BASE_SUBJECT,
        base_body_html=_DEFAULT_BASE_BODY,
    )
    return PersonalizedFollowupResponse(**draft)
