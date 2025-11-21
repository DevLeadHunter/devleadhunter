"""
Pydantic schemas for campaign management.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class CampaignBase(BaseModel):
    """Base schema for campaign."""
    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")
    status: str = Field(default="draft", description="Campaign status")


class CampaignCreate(CampaignBase):
    """Schema for creating a new campaign."""
    prospect_ids: Optional[List[int]] = Field(default=[], description="List of prospect IDs to add to campaign")


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Campaign name")
    description: Optional[str] = Field(None, description="Campaign description")
    status: Optional[str] = Field(None, description="Campaign status")


class CampaignProspectAdd(BaseModel):
    """Schema for adding prospects to a campaign."""
    prospect_ids: List[int] = Field(..., min_length=1, description="List of prospect IDs to add")


class CampaignProspectRemove(BaseModel):
    """Schema for removing a prospect from a campaign."""
    prospect_id: int = Field(..., description="Prospect ID to remove")


class CampaignStats(BaseModel):
    """Schema for campaign statistics."""
    campaign_id: int
    total_prospects: int
    total_emails_sent: int
    emails_delivered: int
    emails_opened: int
    emails_clicked: int
    emails_bounced: int
    emails_failed: int
    delivery_rate: float
    open_rate: float
    click_rate: float
    
    model_config = ConfigDict(from_attributes=True)


class CampaignProspectResponse(BaseModel):
    """Schema for prospect in campaign response."""
    id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    city: Optional[str]
    category: str
    source: str
    confidence: int
    
    model_config = ConfigDict(from_attributes=True)


class CampaignResponse(CampaignBase):
    """Schema for campaign response."""
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    prospects_count: int = Field(default=0, description="Number of prospects in campaign")
    
    model_config = ConfigDict(from_attributes=True)


class CampaignDetailResponse(CampaignResponse):
    """Schema for detailed campaign response with prospects."""
    prospects: List[CampaignProspectResponse] = Field(default=[], description="List of prospects in campaign")
    
    model_config = ConfigDict(from_attributes=True)


class CampaignListResponse(BaseModel):
    """Schema for campaign list response."""
    campaigns: List[CampaignResponse]
    total: int
    
    model_config = ConfigDict(from_attributes=True)

