"""
Pydantic schemas for email sending.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

from enums.email_status import EmailStatus
from services.email_failure_explainer import EmailFailureExplainer


class EmailFailureInfo(BaseModel):
    """A send failure explained in French for the operator."""

    category: str
    reason: str
    is_expected: bool | None = None


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
    machine_opened_at: datetime | None = None
    open_count: int = 0
    last_open_at: datetime | None = None
    clicked_at: datetime | None = None
    replied_at: datetime | None = None
    bounced_at: datetime | None = None
    complained_at: datetime | None = None
    suppressed_at: datetime | None = None
    failed_at: datetime | None = None

    error_message: str | None = None

    created_at: datetime
    updated_at: datetime | None = None

    @computed_field
    @property
    def failure(self) -> EmailFailureInfo | None:
        """French explanation of why the email did not go out, or None when it did not fail."""
        explanation = EmailFailureExplainer.explain(self.status.value, self.error_message)
        if explanation is None:
            return None
        return EmailFailureInfo(
            category=explanation.category,
            reason=explanation.reason,
            is_expected=explanation.is_expected,
        )

    @field_validator("prospect_id", "campaign_id", mode="before")
    @classmethod
    def _coerce_id_to_str(cls, value: Any) -> Any:
        """DB stores these FK ids as integers; the API exposes them as strings."""
        return str(value) if value is not None else None


class EmailLogListResponse(BaseModel):
    """Schema for email log list response."""

    total: int
    logs: list[EmailLogResponse]


class ConversationItem(BaseModel):
    """One message of the user↔prospect exchange (outbound send or captured reply)."""

    direction: str  # outbound | inbound
    id: int
    subject: str | None = None
    body_text: str | None = None  # inbound replies: safe plain text (untrusted HTML stripped server-side)
    body_html: str | None = None  # outbound sends only (authored by the user)
    counterpart: str
    timestamp: str | None = None
    is_auto_reply: bool = False
    is_conversation_reply: bool = False
    pending: bool = False
    status: str | None = None
    # LLM verdict on inbound replies (interested / not_interested / later / question / unsubscribe / other).
    intent: str | None = None
    # The EmailReply id behind an inbound item (action targets: handle, unsubscribe).
    reply_id: int | None = None
    # Planned answers (not sent yet): id, time, status and whether the prospect wrote since.
    scheduled_id: int | None = None
    scheduled_at: str | None = None
    scheduled_status: str | None = None
    scheduled_created_at: str | None = None
    scheduled_error: str | None = None
    signature_html: str | None = None
    has_newer_reply: bool = False


class ConversationResponse(BaseModel):
    """The full exchange around a send, oldest first."""

    items: list[ConversationItem]


class PendingReplyItem(BaseModel):
    """A human reply still awaiting an answer."""

    source: str = "email_reply"
    id: int
    email_log_id: int | None = None
    demo_lead_id: int | None = None
    prospect_id: int | None = None
    prospect_name: str | None = None
    from_email: str
    subject: str | None = None
    preview: str
    intent: str | None = None
    received_at: str | None = None


class PendingRepliesResponse(BaseModel):
    """The « à traiter » queue."""

    count: int
    items: list[PendingReplyItem]


class ReplySendRequest(BaseModel):
    """Payload to answer a prospect's reply from the app."""

    body_html: str


class ReplyScheduleRequest(BaseModel):
    """Payload to plan an answer to a prospect's reply."""

    body_html: str
    scheduled_at: datetime


class ScheduledEmailUpdateRequest(BaseModel):
    """Change the text and/or the time of a planned email."""

    body_html: str | None = None
    scheduled_at: datetime | None = None


class ScheduledEmailResponse(BaseModel):
    """A planned email."""

    id: int
    status: str
    scheduled_at: str
    recipient_email: str


class EmailStatsResponse(BaseModel):
    """Schema for email statistics response."""

    total_sent: int
    total_delivered: int
    total_opened: int
    total_clicked: int
    total_replied: int
    total_bounced: int
    total_failed: int
    delivery_rate: float
    open_rate: float
    click_rate: float
    reply_rate: float
