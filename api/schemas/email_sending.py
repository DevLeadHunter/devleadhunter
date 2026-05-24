"""
Pydantic schemas for email sending.
"""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, EmailStr, Field

from enums.email_status import EmailStatus


class SendEmailRequest(BaseModel):
    """Schema for sending a single email."""
    email_account_id: int
    recipient_email: EmailStr
    recipient_name: Optional[str] = None
    subject: str = Field(..., max_length=500)
    body_html: str
    prospect_id: Optional[str] = None
    template_id: Optional[int] = None
    variables: Optional[Dict[str, str]] = None


class SendCampaignEmailRequest(BaseModel):
    """Schema for sending campaign emails."""
    email_account_id: int
    campaign_id: str
    template_id: int
    prospect_ids: List[str] = Field(..., min_length=1)
    variables_per_prospect: Optional[Dict[str, Dict[str, str]]] = Field(
        None,
        description="Map of prospect_id to variable values"
    )


class SendEmailResponse(BaseModel):
    """Schema for send email response."""
    success: bool
    message_id: Optional[str] = None
    email_log_id: int
    error: Optional[str] = None


class SendCampaignEmailResponse(BaseModel):
    """Schema for send campaign email response."""
    success: bool
    total_emails: int
    sent_count: int
    failed_count: int
    email_log_ids: List[int]
    errors: Optional[List[str]] = None


class EmailLogResponse(BaseModel):
    """Schema for email log response."""
    id: int
    user_id: int
    email_account_id: int
    prospect_id: Optional[str] = None
    campaign_id: Optional[str] = None
    
    recipient_email: str
    recipient_name: Optional[str] = None
    subject: str
    
    status: EmailStatus
    provider: str
    provider_message_id: Optional[str] = None
    
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    
    error_message: Optional[str] = None
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EmailLogListResponse(BaseModel):
    """Schema for email log list response."""
    total: int
    logs: List[EmailLogResponse]


class EmailStatsResponse(BaseModel):
    """Schema for email statistics response."""
    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    total_bounced: int
    total_failed: int
    delivery_rate: float
    open_rate: float
    click_rate: float

