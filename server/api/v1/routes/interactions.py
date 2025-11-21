"""
Interaction routes for prospect interaction history.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from core.database import get_db
from services.auth_service import get_current_user
from services.interaction_service import interaction_service
from models.user import User
from models.prospect_db import ProspectDB
from schemas.interaction import InteractionCreate, InteractionResponse, InteractionListResponse


router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post(
    "/prospects/{prospect_id}",
    response_model=InteractionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add interaction to prospect"
)
async def create_interaction(
    prospect_id: int,
    interaction_data: InteractionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a new interaction to a prospect.
    
    Interaction types:
    - email_sent: Email was sent
    - email_opened: Email was opened
    - email_clicked: Link in email was clicked
    - call: Phone call made
    - meeting: Meeting held
    - note: General note
    - converted: Prospect converted to client
    - lost: Lost opportunity
    """
    # Verify prospect belongs to user
    prospect = db.query(ProspectDB).filter(
        ProspectDB.id == prospect_id,
        ProspectDB.user_id == current_user.id
    ).first()
    
    if not prospect:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prospect not found"
        )
    
    # Create interaction
    interaction = interaction_service.create_interaction(
        db=db,
        prospect_id=prospect_id,
        user_id=current_user.id,
        interaction_type=interaction_data.interaction_type,
        description=interaction_data.description,
        metadata=interaction_data.metadata
    )
    
    return interaction


@router.get(
    "/prospects/{prospect_id}",
    response_model=InteractionListResponse,
    summary="Get prospect interactions"
)
async def get_prospect_interactions(
    prospect_id: int,
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of interactions to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all interactions for a prospect.
    
    Returns a list of interactions ordered by date (most recent first).
    """
    # Verify prospect belongs to user
    prospect = db.query(ProspectDB).filter(
        ProspectDB.id == prospect_id,
        ProspectDB.user_id == current_user.id
    ).first()
    
    if not prospect:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prospect not found"
        )
    
    # Get interactions
    interactions = interaction_service.get_prospect_interactions(
        db=db,
        prospect_id=prospect_id,
        user_id=current_user.id,
        limit=limit
    )
    
    return InteractionListResponse(
        interactions=interactions,
        total=len(interactions)
    )

