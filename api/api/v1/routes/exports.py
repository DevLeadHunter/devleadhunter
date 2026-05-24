"""
Export routes for generating CSV/Excel exports.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from services.auth_service import get_current_user
from services.export_service import export_service
from services.campaign_service import campaign_service
from models.user import User
from models.prospect_db import ProspectDB


router = APIRouter(prefix="/exports", tags=["exports"])


@router.get(
    "/prospects/csv",
    response_class=Response,
    summary="Export prospects to CSV"
)
async def export_prospects_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000)
):
    """
    Export all prospects to CSV format.
    
    Returns a CSV file with all prospects for the current user.
    """
    # Get prospects
    prospects = db.query(ProspectDB).filter(
        ProspectDB.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    if not prospects:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No prospects found"
        )
    
    # Generate CSV
    csv_data = export_service.export_prospects_to_csv(prospects)
    
    # Return CSV response
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=prospects_{current_user.id}.csv"
        }
    )


@router.get(
    "/campaigns/{campaign_id}/csv",
    response_class=Response,
    summary="Export campaign to CSV"
)
async def export_campaign_csv(
    campaign_id: int,
    include_prospects: bool = Query(True, description="Include prospect details"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export a campaign to CSV format.
    
    Returns a CSV file with campaign information and optionally prospect details.
    """
    # Get campaign
    campaign = campaign_service.get_campaign(db, campaign_id, current_user.id)
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found"
        )
    
    # Generate CSV
    csv_data = export_service.export_campaign_to_csv(campaign, include_prospects)
    
    # Return CSV response
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=campaign_{campaign_id}_{campaign.name.replace(' ', '_')}.csv"
        }
    )


@router.get(
    "/campaigns/csv",
    response_class=Response,
    summary="Export all campaigns to CSV"
)
async def export_campaigns_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export all campaigns summary to CSV format.
    
    Returns a CSV file with a summary of all campaigns.
    """
    # Get campaigns
    campaigns, _ = campaign_service.list_campaigns(db, current_user.id, skip=0, limit=10000)
    
    if not campaigns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No campaigns found"
        )
    
    # Generate CSV
    csv_data = export_service.export_campaigns_summary_to_csv(campaigns)
    
    # Return CSV response
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=campaigns_{current_user.id}.csv"
        }
    )

