"""
Pydantic schemas for email templates.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmailTemplateBase(BaseModel):
    """Base schema for email template."""

    name: str = Field(..., max_length=255)
    subject: str = Field(..., max_length=500)
    body_html: str
    body_text: str | None = None
    variables: list[str] | None = None
    signature_id: int | None = None


class EmailTemplateCreate(EmailTemplateBase):
    """Schema for creating an email template."""

    email_account_id: int | None = None


class EmailTemplateUpdate(BaseModel):
    """Schema for updating an email template."""

    name: str | None = Field(None, max_length=255)
    subject: str | None = Field(None, max_length=500)
    body_html: str | None = None
    body_text: str | None = None
    email_account_id: int | None = None
    variables: list[str] | None = None
    is_active: bool | None = None
    # ``signature_id`` is nullable on purpose: an explicit ``null`` detaches the
    # signature (switch turned off), so it must be part of the update payload.
    signature_id: int | None = None


class EmailTemplateResponse(BaseModel):
    """Schema for email template response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    email_account_id: int | None = None
    name: str
    subject: str
    body_html: str
    body_text: str | None = None
    variables: list[str] | None = None
    signature_id: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None


class EmailTemplatePreviewRequest(BaseModel):
    """Schema for email template preview request."""

    template_id: int
    variables: dict = Field(default_factory=dict, description="Variable values to substitute in template")


class EmailTemplatePreviewResponse(BaseModel):
    """Schema for email template preview response."""

    subject: str
    body_html: str
