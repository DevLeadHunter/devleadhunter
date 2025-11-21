"""
Campaign routes for API v1.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from core.database import get_db
from services.auth_service import get_current_user
from services.campaign_service import campaign_service
from models.user import User
from schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignResponse,
    CampaignDetailResponse,
    CampaignListResponse,
    CampaignProspectAdd,
    CampaignStats,
    CampaignProspectResponse
)


router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.post(
    "",
    response_model=CampaignDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new campaign"
)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new email campaign.
    
    - **name**: Campaign name (required)
    - **description**: Campaign description (optional)
    - **status**: Campaign status (default: draft)
    - **prospect_ids**: List of prospect IDs to add to campaign (optional)
    """
    campaign = campaign_service.create_campaign(db, current_user.id, campaign_data)
    
    return CampaignDetailResponse(
        id=campaign.id,
        user_id=campaign.user_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        prospects_count=len(campaign.prospects),
        prospects=[
            CampaignProspectResponse(
                id=p.id,
                name=p.name,
                email=p.email,
                phone=p.phone,
                city=p.city,
                category=p.category,
                source=p.source,
                confidence=p.confidence
            ) for p in campaign.prospects
        ]
    )


@router.get(
    "",
    response_model=CampaignListResponse,
    summary="List all campaigns"
)
async def list_campaigns(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all campaigns for the current user.
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by campaign status (draft, active, completed, paused, cancelled)
    """
    campaigns, total = campaign_service.list_campaigns(
        db, current_user.id, skip, limit, status
    )
    
    return CampaignListResponse(
        campaigns=[
            CampaignResponse(
                id=c.id,
                user_id=c.user_id,
                name=c.name,
                description=c.description,
                status=c.status,
                created_at=c.created_at,
                updated_at=c.updated_at,
                prospects_count=len(c.prospects)
            ) for c in campaigns
        ],
        total=total
    )


@router.get(
    "/{campaign_id}",
    response_model=CampaignDetailResponse,
    summary="Get campaign details"
)
async def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific campaign.
    
    Returns campaign information with list of prospects.
    """
    campaign = campaign_service.get_campaign(db, campaign_id, current_user.id)
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    return CampaignDetailResponse(
        id=campaign.id,
        user_id=campaign.user_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        prospects_count=len(campaign.prospects),
        prospects=[
            CampaignProspectResponse(
                id=p.id,
                name=p.name,
                email=p.email,
                phone=p.phone,
                city=p.city,
                category=p.category,
                source=p.source,
                confidence=p.confidence
            ) for p in campaign.prospects
        ]
    )


@router.patch(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update campaign"
)
async def update_campaign(
    campaign_id: int,
    campaign_data: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a campaign's information.
    
    - **name**: Campaign name
    - **description**: Campaign description
    - **status**: Campaign status
    """
    campaign = campaign_service.update_campaign(
        db, campaign_id, current_user.id, campaign_data
    )
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    return CampaignResponse(
        id=campaign.id,
        user_id=campaign.user_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        prospects_count=len(campaign.prospects)
    )


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete campaign"
)
async def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a campaign.
    
    This will also remove all prospect associations but will not delete
    the prospects themselves or email logs.
    """
    deleted = campaign_service.delete_campaign(db, campaign_id, current_user.id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    return None


@router.post(
    "/{campaign_id}/prospects",
    response_model=CampaignDetailResponse,
    summary="Add prospects to campaign"
)
async def add_prospects_to_campaign(
    campaign_id: int,
    data: CampaignProspectAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add prospects to a campaign.
    
    - **prospect_ids**: List of prospect IDs to add
    """
    campaign = campaign_service.add_prospects_to_campaign(
        db, campaign_id, current_user.id, data.prospect_ids
    )
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    return CampaignDetailResponse(
        id=campaign.id,
        user_id=campaign.user_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        prospects_count=len(campaign.prospects),
        prospects=[
            CampaignProspectResponse(
                id=p.id,
                name=p.name,
                email=p.email,
                phone=p.phone,
                city=p.city,
                category=p.category,
                source=p.source,
                confidence=p.confidence
            ) for p in campaign.prospects
        ]
    )


@router.delete(
    "/{campaign_id}/prospects/{prospect_id}",
    response_model=CampaignDetailResponse,
    summary="Remove prospect from campaign"
)
async def remove_prospect_from_campaign(
    campaign_id: int,
    prospect_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a prospect from a campaign.
    
    This does not delete the prospect, only removes it from the campaign.
    """
    campaign = campaign_service.remove_prospect_from_campaign(
        db, campaign_id, current_user.id, prospect_id
    )
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    return CampaignDetailResponse(
        id=campaign.id,
        user_id=campaign.user_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        prospects_count=len(campaign.prospects),
        prospects=[
            CampaignProspectResponse(
                id=p.id,
                name=p.name,
                email=p.email,
                phone=p.phone,
                city=p.city,
                category=p.category,
                source=p.source,
                confidence=p.confidence
            ) for p in campaign.prospects
        ]
    )


@router.get(
    "/{campaign_id}/stats",
    response_model=CampaignStats,
    summary="Get campaign statistics"
)
async def get_campaign_stats(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed statistics for a campaign.
    
    Returns:
    - Total prospects count
    - Total emails sent
    - Emails delivered, opened, clicked, bounced, failed
    - Delivery rate, open rate, click rate
    """
    stats = campaign_service.get_campaign_stats(db, campaign_id, current_user.id)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    return stats

