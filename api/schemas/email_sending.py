"""
Pydantic schemas for email sending.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from enums.email_status import EmailStatus


class SendEmailRequest(BaseModel):
    """Schema for sending a single email."""

    email_account_id: int
    recipient_email: EmailStr
    recipient_name: str | None = None
    subject: str = Field(..., max_length=500)
    body_html: str
    prospect_id: str | None = None
    template_id: int | None = None
    variables: dict[str, str] | None = None


class SendCampaignEmailRequest(BaseModel):
    """Schema for sending campaign emails."""

    email_account_id: int
    campaign_id: str
    template_id: int
    prospect_ids: list[str] = Field(..., min_length=1)
    variables_per_prospect: dict[str, dict[str, str]] | None = Field(
        None, description="Map of prospect_id to variable values"
    )


class SendEmailResponse(BaseModel):
    """Schema for send email response."""

    success: bool
    message_id: str | None = None
    email_log_id: int
    error: str | None = None


class SendCampaignEmailResponse(BaseModel):
    """Schema for send campaign email response."""

    success: bool
    total_emails: int
    sent_count: int
    failed_count: int
    email_log_ids: list[int]
    errors: list[str] | None = None


class EmailLogResponse(BaseModel):
    """Schema for email log response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    email_account_id: int | None = None
    prospect_id: str | None = None
    campaign_id: str | None = None

    recipient_email: str
    recipient_name: str | None = None
    subject: str
    body_html: str | None = None

    status: EmailStatus
    provider: str
    provider_message_id: str | None = None
    ab_variant: str | None = None

    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    opened_at: datetime | None = None
    clicked_at: datetime | None = None
    bounced_at: datetime | None = None
    complained_at: datetime | None = None
    suppressed_at: datetime | None = None
    failed_at: datetime | None = None

    error_message: str | None = None

    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("prospect_id", "campaign_id", mode="before")
    @classmethod
    def _coerce_id_to_str(cls, value: Any) -> Any:
        """DB stores these FK ids as integers; the API exposes them as strings."""
        return str(value) if value is not None else None


class EmailLogListResponse(BaseModel):
    """Schema for email log list response."""

    total: int
    logs: list[EmailLogResponse]


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
