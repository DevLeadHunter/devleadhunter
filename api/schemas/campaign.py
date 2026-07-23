"""
Pydantic schemas for campaign management.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class CampaignFollowUpCreate(BaseModel):
    """Schema for adding a follow-up step to a campaign."""
    template_id: int = Field(..., description="Template to use for this follow-up")
    delay_days: int = Field(5, ge=1, le=365, description="Days after previous send")
    position: int = Field(1, ge=1, description="1-based order in the sequence")


class CampaignFollowUpUpdate(BaseModel):
    """Schema for updating a follow-up step."""
    template_id: Optional[int] = None
    delay_days: Optional[int] = Field(None, ge=1, le=365)
    position: Optional[int] = Field(None, ge=1)


class CampaignFollowUpResponse(BaseModel):
    """Schema for a follow-up step in API responses."""
    id: int
    campaign_id: int
    template_id: int
    template_name: Optional[str] = None
    template_subject: Optional[str] = None
    delay_days: int
    position: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignBase(BaseModel):
    """Base schema for campaign."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    status: str = Field(default="draft")


class CampaignCreate(CampaignBase):
    """Schema for creating a new campaign."""
    prospect_ids: Optional[List[int]] = Field(default_factory=list)
    # Optional initial configuration (can be set later via PATCH /settings)
    template_id: Optional[int] = None
    ab_template_id_b: Optional[int] = None
    send_delay_minutes: int = Field(20, ge=1, le=1440)


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign's metadata."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None


class CampaignSettingsUpdate(BaseModel):
    """Schema for updating a campaign's send configuration (editable at any time)."""
    template_id: Optional[int] = None
    ab_template_id_b: Optional[int] = None
    # Explicit flag to disable A/B (since None means "unchanged")
    disable_ab: bool = False
    send_delay_minutes: Optional[int] = Field(None, ge=1, le=1440)
    # Personalise follow-up bodies from demo behaviour (additive — falls back to template)
    behavior_personalized_followups: Optional[bool] = None
    # Full replacement of the follow-up sequence (if provided)
    follow_ups: Optional[List[CampaignFollowUpCreate]] = None


class CampaignProspectAdd(BaseModel):
    """Schema for adding prospects to a campaign."""
    prospect_ids: List[int] = Field(..., min_length=1)


class CampaignProspectRemove(BaseModel):
    """Schema for removing a prospect from a campaign."""
    prospect_id: int


class CampaignVariantStats(BaseModel):
    """Stats broken down for a single A/B variant."""
    variant: str
    sent: int
    delivered: int
    opened: int
    clicked: int
    open_rate: float
    click_rate: float


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
    # A/B breakdown (only populated when campaign uses ab_template_id_b)
    ab_stats: Optional[List[CampaignVariantStats]] = None

    model_config = ConfigDict(from_attributes=True)


class CampaignProspectResponse(BaseModel):
    """Prospect embedded inside a campaign response."""
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    category: str
    source: str
    confidence: int
    # A/B variant pre-assigned when the campaign was launched (if known)
    ab_variant: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CampaignResponse(CampaignBase):
    """Summary campaign response (list view)."""
    id: int
    user_id: int
    template_id: Optional[int] = None
    ab_template_id_b: Optional[int] = None
    send_delay_minutes: int = 20
    follow_up_delay_days: int = 5
    behavior_personalized_followups: bool = False
    started_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    prospects_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CampaignDetailResponse(CampaignResponse):
    """Full campaign response with prospects and follow-up sequence."""
    prospects: List[CampaignProspectResponse] = Field(default_factory=list)
    follow_ups: List[CampaignFollowUpResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CampaignListResponse(BaseModel):
    """Paginated campaign list."""
    campaigns: List[CampaignResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)
