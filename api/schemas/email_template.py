"""
Pydantic schemas for email templates.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class EmailTemplateBase(BaseModel):
    """Base schema for email template."""
    name: str = Field(..., max_length=255)
    subject: str = Field(..., max_length=500)
    body_html: str
    body_text: Optional[str] = None
    variables: Optional[List[str]] = None


class EmailTemplateCreate(EmailTemplateBase):
    """Schema for creating an email template."""
    email_account_id: Optional[int] = None


class EmailTemplateUpdate(BaseModel):
    """Schema for updating an email template."""
    name: Optional[str] = Field(None, max_length=255)
    subject: Optional[str] = Field(None, max_length=500)
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    email_account_id: Optional[int] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None


class EmailTemplateResponse(BaseModel):
    """Schema for email template response."""
    id: int
    user_id: int
    email_account_id: Optional[int] = None
    name: str
    subject: str
    body_html: str
    body_text: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EmailTemplatePreviewRequest(BaseModel):
    """Schema for email template preview request."""
    template_id: int
    variables: dict = Field(
        default_factory=dict,
        description="Variable values to substitute in template"
    )


class EmailTemplatePreviewResponse(BaseModel):
    """Schema for email template preview response."""
    subject: str
    body_html: str

