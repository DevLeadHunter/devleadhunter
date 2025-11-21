"""
Email sending routes for sending individual and campaign emails.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from core.database import get_db
from models.user import User
from models.email_log import EmailLog
from schemas.email_sending import (
    SendEmailRequest,
    SendCampaignEmailRequest,
    SendEmailResponse,
    SendCampaignEmailResponse,
    EmailLogResponse,
    EmailLogListResponse,
    EmailStatsResponse
)
from services.auth_service import get_current_user
from services.email_sending_service import EmailSendingService
from enums.email_status import EmailStatus

router = APIRouter(prefix="/emails", tags=["emails"])


@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    email_data: SendEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send a single email to a prospect.
    """
    email_service = EmailSendingService(db)
    
    try:
        # Handle template variables if provided
        subject = email_data.subject
        body_html = email_data.body_html
        
        if email_data.variables:
            subject = email_service.replace_variables(subject, email_data.variables)
            body_html = email_service.replace_variables(body_html, email_data.variables)
        
        result = await email_service.send_email(
            user_id=current_user.id,
            email_account_id=email_data.email_account_id,
            recipient_email=email_data.recipient_email,
            recipient_name=email_data.recipient_name,
            subject=subject,
            body_html=body_html,
            prospect_id=email_data.prospect_id
        )
        
        return SendEmailResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/send-campaign", response_model=SendCampaignEmailResponse)
async def send_campaign_emails(
    campaign_data: SendCampaignEmailRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Send emails to multiple prospects in a campaign.
    """
    email_service = EmailSendingService(db)
    
    try:
        result = await email_service.send_campaign_emails(
            user_id=current_user.id,
            email_account_id=campaign_data.email_account_id,
            campaign_id=campaign_data.campaign_id,
            template_id=campaign_data.template_id,
            prospect_ids=campaign_data.prospect_ids,
            variables_per_prospect=campaign_data.variables_per_prospect
        )
        
        return SendCampaignEmailResponse(**result)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/logs", response_model=EmailLogListResponse)
async def get_email_logs(
    campaign_id: str = Query(None, description="Filter by campaign ID"),
    prospect_id: str = Query(None, description="Filter by prospect ID"),
    status_filter: EmailStatus = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get email logs for the current user.
    """
    # Build query
    stmt = select(EmailLog).where(
        EmailLog.user_id == current_user.id
    )
    
    if campaign_id:
        stmt = stmt.where(EmailLog.campaign_id == campaign_id)
    if prospect_id:
        stmt = stmt.where(EmailLog.prospect_id == prospect_id)
    if status_filter:
        stmt = stmt.where(EmailLog.status == status_filter.value)
    
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar()
    
    # Get logs with pagination
    stmt = stmt.order_by(EmailLog.created_at.desc()).limit(limit).offset(offset)
    result = db.execute(stmt)
    logs = result.scalars().all()
    
    return EmailLogListResponse(
        total=total,
        logs=logs
    )


@router.get("/logs/{log_id}", response_model=EmailLogResponse)
async def get_email_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific email log by ID.
    """
    stmt = select(EmailLog).where(
        EmailLog.id == log_id,
        EmailLog.user_id == current_user.id
    )
    
    result = db.execute(stmt)
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email log not found"
        )
    
    return log


@router.get("/stats", response_model=EmailStatsResponse)
async def get_email_stats(
    campaign_id: str = Query(None, description="Filter by campaign ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get email statistics for the current user.
    """
    # Build base query
    base_stmt = select(EmailLog).where(
        EmailLog.user_id == current_user.id
    )
    
    if campaign_id:
        base_stmt = base_stmt.where(EmailLog.campaign_id == campaign_id)
    
    # Count by status
    total_sent = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.SENT.value).subquery()
        )
    ).scalar()
    
    total_delivered = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.DELIVERED.value).subquery()
        )
    ).scalar()
    
    total_opened = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.OPENED.value).subquery()
        )
    ).scalar()
    
    total_clicked = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.CLICKED.value).subquery()
        )
    ).scalar()
    
    total_bounced = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.BOUNCED.value).subquery()
        )
    ).scalar()
    
    total_failed = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.FAILED.value).subquery()
        )
    ).scalar()
    
    # Calculate rates
    delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0.0
    open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0.0
    click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0.0
    
    return EmailStatsResponse(
        total_sent=total_sent,
        total_delivered=total_delivered,
        total_opened=total_opened,
        total_clicked=total_clicked,
        total_bounced=total_bounced,
        total_failed=total_failed,
        delivery_rate=round(delivery_rate, 2),
        open_rate=round(open_rate, 2),
        click_rate=round(click_rate, 2)
    )

