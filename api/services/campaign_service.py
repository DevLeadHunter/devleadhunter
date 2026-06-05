"""
Campaign service for managing email campaigns.
"""
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case
from fastapi import HTTPException, status

from models.campaign import Campaign, CampaignStatus
from models.campaign_follow_up import CampaignFollowUp
from models.prospect_db import ProspectDB
from models.email_log import EmailLog
from enums.email_status import EmailStatus
from schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CampaignStats,
    CampaignVariantStats,
)


class CampaignService:
    """Service for campaign management."""
    
    def create_campaign(
        self,
        db: Session,
        user_id: int,
        campaign_data: CampaignCreate
    ) -> Campaign:
        """
        Create a new campaign.
        
        Args:
            db: Database session
            user_id: ID of the user creating the campaign
            campaign_data: Campaign creation data
            
        Returns:
            Created campaign
        """
        # Create campaign
        campaign = Campaign(
            user_id=user_id,
            name=campaign_data.name,
            description=campaign_data.description,
            status=campaign_data.status or CampaignStatus.DRAFT.value,
            template_id=campaign_data.template_id,
            ab_template_id_b=campaign_data.ab_template_id_b,
            send_delay_minutes=campaign_data.send_delay_minutes,
        )
        
        # Add prospects if provided
        if campaign_data.prospect_ids:
            prospects = db.query(ProspectDB).filter(
                ProspectDB.id.in_(campaign_data.prospect_ids),
                ProspectDB.user_id == user_id
            ).all()
            campaign.prospects = prospects
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        return campaign
    
    def get_campaign(
        self,
        db: Session,
        campaign_id: int,
        user_id: int
    ) -> Optional[Campaign]:
        """
        Get a campaign by ID.
        
        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user requesting the campaign
            
        Returns:
            Campaign if found and owned by user, None otherwise
        """
        campaign = db.query(Campaign).options(
            joinedload(Campaign.prospects),
            joinedload(Campaign.follow_ups),
        ).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == user_id
        ).first()
        
        return campaign
    
    def list_campaigns(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None
    ) -> tuple[List[Campaign], int]:
        """
        List campaigns for a user.
        
        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status (optional)
            
        Returns:
            Tuple of (campaigns list, total count)
        """
        query = db.query(Campaign).filter(Campaign.user_id == user_id)
        
        if status:
            query = query.filter(Campaign.status == status)
        
        total = query.count()
        campaigns = query.order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()
        
        return campaigns, total
    
    def update_campaign(
        self,
        db: Session,
        campaign_id: int,
        user_id: int,
        campaign_data: CampaignUpdate
    ) -> Optional[Campaign]:
        """
        Update a campaign.
        
        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user updating the campaign
            campaign_data: Campaign update data
            
        Returns:
            Updated campaign if found and owned by user, None otherwise
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None
        
        # Update fields
        update_data = campaign_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(campaign, field, value)
        
        db.commit()
        db.refresh(campaign)
        
        return campaign
    
    def delete_campaign(
        self,
        db: Session,
        campaign_id: int,
        user_id: int
    ) -> bool:
        """
        Delete a campaign.
        
        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user deleting the campaign
            
        Returns:
            True if deleted, False if not found
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return False
        
        db.delete(campaign)
        db.commit()
        
        return True
    
    def add_prospects_to_campaign(
        self,
        db: Session,
        campaign_id: int,
        user_id: int,
        prospect_ids: List[int]
    ) -> Optional[Campaign]:
        """
        Add prospects to a campaign.
        
        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user
            prospect_ids: List of prospect IDs to add
            
        Returns:
            Updated campaign if found, None otherwise
            
        Raises:
            HTTPException: If prospects not found or not owned by user
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None
        
        # Get prospects
        prospects = db.query(ProspectDB).filter(
            ProspectDB.id.in_(prospect_ids),
            ProspectDB.user_id == user_id
        ).all()
        
        if len(prospects) != len(prospect_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Some prospects not found or not owned by user"
            )
        
        # Get existing prospect IDs
        existing_ids = {p.id for p in campaign.prospects}
        
        # Add only new prospects
        for prospect in prospects:
            if prospect.id not in existing_ids:
                campaign.prospects.append(prospect)
        
        db.commit()
        db.refresh(campaign)
        
        return campaign
    
    def remove_prospect_from_campaign(
        self,
        db: Session,
        campaign_id: int,
        user_id: int,
        prospect_id: int
    ) -> Optional[Campaign]:
        """
        Remove a prospect from a campaign.
        
        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user
            prospect_id: Prospect ID to remove
            
        Returns:
            Updated campaign if found, None otherwise
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None
        
        # Find and remove prospect
        for i, prospect in enumerate(campaign.prospects):
            if prospect.id == prospect_id:
                campaign.prospects.pop(i)
                break
        
        db.commit()
        db.refresh(campaign)
        
        return campaign
    
    def get_campaign_stats(
        self,
        db: Session,
        campaign_id: int,
        user_id: int
    ) -> Optional[CampaignStats]:
        """
        Get statistics for a campaign.
        
        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user
            
        Returns:
            Campaign statistics if campaign found, None otherwise
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None
        
        # Count prospects
        total_prospects = len(campaign.prospects)
        
        # Get email statistics
        email_stats = db.query(
            func.count(EmailLog.id).label('total_sent'),
            func.sum(case((EmailLog.status == EmailStatus.DELIVERED.value, 1), else_=0)).label('delivered'),
            func.sum(case((EmailLog.status == EmailStatus.OPENED.value, 1), else_=0)).label('opened'),
            func.sum(case((EmailLog.clicked_at.isnot(None), 1), else_=0)).label('clicked'),
            func.sum(case((EmailLog.status == EmailStatus.BOUNCED.value, 1), else_=0)).label('bounced'),
            func.sum(case((EmailLog.status == EmailStatus.FAILED.value, 1), else_=0)).label('failed')
        ).filter(
            EmailLog.campaign_id == campaign_id,
            EmailLog.user_id == user_id
        ).first()
        
        total_sent = email_stats.total_sent or 0
        delivered = email_stats.delivered or 0
        opened = email_stats.opened or 0
        clicked = email_stats.clicked or 0
        bounced = email_stats.bounced or 0
        failed = email_stats.failed or 0
        
        # Calculate rates
        delivery_rate = (delivered / total_sent * 100) if total_sent > 0 else 0
        open_rate = (opened / delivered * 100) if delivered > 0 else 0
        click_rate = (clicked / opened * 100) if opened > 0 else 0
        
        # A/B breakdown (only when campaign has a B variant)
        ab_stats: list[CampaignVariantStats] | None = None
        if campaign.ab_template_id_b:
            ab_stats = []
            for variant in ("A", "B"):
                row = db.query(
                    func.count(EmailLog.id).label('sent'),
                    func.sum(case((EmailLog.status == EmailStatus.DELIVERED.value, 1), else_=0)).label('delivered'),
                    func.sum(case((EmailLog.status == EmailStatus.OPENED.value, 1), else_=0)).label('opened'),
                    func.sum(case((EmailLog.clicked_at.isnot(None), 1), else_=0)).label('clicked'),
                ).filter(
                    EmailLog.campaign_id == campaign_id,
                    EmailLog.user_id == user_id,
                    EmailLog.ab_variant == variant,
                ).first()
                v_sent = row.sent or 0
                v_delivered = row.delivered or 0
                v_opened = row.opened or 0
                v_clicked = row.clicked or 0
                ab_stats.append(CampaignVariantStats(
                    variant=variant,
                    sent=v_sent,
                    delivered=v_delivered,
                    opened=v_opened,
                    clicked=v_clicked,
                    open_rate=round((v_opened / v_delivered * 100) if v_delivered else 0, 2),
                    click_rate=round((v_clicked / v_opened * 100) if v_opened else 0, 2),
                ))

        return CampaignStats(
            campaign_id=campaign_id,
            total_prospects=total_prospects,
            total_emails_sent=total_sent,
            emails_delivered=delivered,
            emails_opened=opened,
            emails_clicked=clicked,
            emails_bounced=bounced,
            emails_failed=failed,
            delivery_rate=round(delivery_rate, 2),
            open_rate=round(open_rate, 2),
            click_rate=round(click_rate, 2),
            ab_stats=ab_stats,
        )


# Singleton instance
campaign_service = CampaignService()

