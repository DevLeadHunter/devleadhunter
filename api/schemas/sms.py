"""SMS API schemas — config, relance candidates, provider callbacks."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SmsConfigResponse(BaseModel):
    """The user's SMS sender configuration."""

    sender: str = ""
    provider_ready: bool = Field(default=False, description="Whether the platform smsmode key is configured")
    cold_sms_enabled: bool = Field(default=False, description="Auto cold-SMS prospects with a mobile but no email")
    auto_relance_enabled: bool = Field(default=False, description="Auto-relance emailed prospects who never reacted")
    auto_relance_after_days: int = Field(default=30, description="Days after the unanswered email before the relance")
    relance_template_key: str = Field(default="rappel-court", description="Library template the J+30 relance renders")


class SmsConfigUpdate(BaseModel):
    """Payload to set the SMS sender (a configured sender turns the channel on)."""

    sender: str = Field(default="", max_length=11)


class SmsAutomationUpdate(BaseModel):
    """Payload to toggle the SMS automations (cold-SMS + auto-relance)."""

    cold_sms_enabled: bool = False
    auto_relance_enabled: bool = False
    auto_relance_after_days: int = Field(default=30, ge=7, le=120)
    relance_template_key: str | None = Field(
        default=None, max_length=64, description="Library template the J+30 relance renders; omitted = unchanged"
    )


class SmsRelanceCandidateResponse(BaseModel):
    """A prospect eligible for an SMS relance."""

    prospect_id: int
    name: str
    city: str | None = None
    phone: str | None = None
    demo_url: str
    emailed_at: datetime


class SmsSendResponse(BaseModel):
    """Outcome of a send (relance or manual), with what it cost when it left."""

    sent: bool
    reason: str | None = None
    segments: int | None = Field(default=None, description="Billed segments, the provider's count when it gave one")
    price_cents: int | None = Field(
        default=None, description="Cost in cents: the provider's, else our country estimate"
    )
    provider_segments: int | None = Field(default=None, description="Segments smsmode counted (messagePartCount)")
    provider_text: str | None = Field(
        default=None, description="Body smsmode acknowledged, its opt-out mention included"
    )


class SmsTemplateResponse(BaseModel):
    """One template of the SMS library."""

    key: str
    name: str
    category: str
    body: str
    variables: list[str]
    is_default: bool = Field(default=False, description="Template the automated first contact sends")
    fallback_key: str | None = Field(
        default=None, description="Template rendered instead when the prospect has no generated video"
    )
    recalls_an_email: bool = Field(
        default=False, description="Relance written as a reminder of an email: it cannot follow a first SMS"
    )
    module: str = Field(default="websites", description="The module the template sells: websites or ai-assistant")


class SmsTemplatePreviewResponse(BaseModel):
    """A library template rendered for one prospect (smsmode appends the opt-out mention at send)."""

    key: str
    body: str
    segments: int = Field(description="Segments the SMS will bill once smsmode appends its opt-out mention")


class SmsSegmentCountRequest(BaseModel):
    """A message typed in the composer, and the prospect it goes to when there is one."""

    text: str = Field(default="", max_length=1000, description="Message as typed")
    prospect_id: int | None = Field(default=None, description="Recipient prospect; none for a French bare number")


class SmsSegmentCountResponse(BaseModel):
    """What a typed message bills once smsmode appends the opt-out mention of its recipient's country."""

    characters: int = Field(description="Characters of the body smsmode receives, GSM-7 transliterated")
    segments: int = Field(description="Billed segments, opt-out mention included")
    maximum_segments: int = Field(description="Most segments a prospecting SMS may bill")
    is_unicode: bool = Field(description="Whether a character forces UCS-2, 70 characters a segment")


class SmsManualSendRequest(BaseModel):
    """Payload to send one free-text SMS (manual composer / self-test)."""

    to: str = Field(
        min_length=1, description="Recipient mobile: national form of the prospect's country, or international (+…)"
    )
    text: str = Field(
        min_length=1, max_length=1000, description="Message body (smsmode appends the opt-out mention itself)"
    )
    prospect_id: int | None = Field(default=None, description="Linked prospect, when the number belongs to one")
    recipient_name: str | None = Field(default=None, max_length=255, description="Display label for a bare number")


class SmsMessageResponse(BaseModel):
    """One sent SMS in the history."""

    id: int
    prospect_id: int | None = None
    recipient_name: str | None = None
    to_e164: str
    sender: str
    body: str
    status: str
    status_detail: str | None = None
    segments: int
    price_cents: int | None = None
    error: str | None = None
    created_at: datetime
    delivered_at: datetime | None = None


class SmsMessagesResponse(BaseModel):
    """A page of the SMS history."""

    total: int
    messages: list[SmsMessageResponse]


class SmsReplyCreateRequest(BaseModel):
    """Payload to consign an SMS reply received on the operator's phone."""

    prospect_id: int | None = Field(default=None, description="Prospect the reply belongs to")
    from_number: str = Field(
        min_length=1, description="Number the prospect wrote from: his country's national form, or international (+…)"
    )
    body: str = Field(min_length=1, max_length=2000, description="Message text as received")
    received_at: datetime | None = Field(default=None, description="When the reply arrived (defaults to now)")


class SmsReplyResponse(BaseModel):
    """One consigned SMS reply."""

    id: int
    prospect_id: int | None = None
    from_number: str
    body: str
    received_at: datetime
    created_at: datetime


class SmsThreadItemResponse(BaseModel):
    """One entry of a prospect's SMS thread — a sent SMS or a consigned reply."""

    kind: str = Field(description="'sent' (our SMS) or 'received' (consigned reply)")
    id: int
    body: str
    at: datetime = Field(description="Send time for 'sent', reception time for 'received'")
    number: str = Field(description="Recipient number for 'sent', sender number for 'received'")
    status: str | None = Field(default=None, description="Delivery status, 'sent' entries only")
    status_detail: str | None = None


class SmsThreadResponse(BaseModel):
    """A prospect's full SMS thread, oldest first."""

    prospect_id: int
    items: list[SmsThreadItemResponse]


class SmsStatsResponse(BaseModel):
    """Aggregate counters of the SMS channel."""

    total: int = 0
    sent: int = 0
    delivered: int = 0
    failed: int = 0
    pending: int = 0
    cost_cents: int = 0


class SmsBulkSendResponse(BaseModel):
    """Outcome of a bulk relance send."""

    sent: int
    skipped: int


class SmsCreditResponse(BaseModel):
    """The platform smsmode account's remaining credit balance (admin-only)."""

    configured: bool = Field(default=False, description="Whether the smsmode key is set")
    credits: float | None = Field(default=None, description="Remaining credits, or null when unreadable")


class SmsDlrCallback(BaseModel):
    """smsmode delivery-receipt callback (subset we use)."""

    messageId: str | None = None
    refClient: str | None = None

    class Status(BaseModel):
        """Nested status object."""

        value: str | None = None

    status: Status | None = None


class SmsAutoQueueRescheduleRequest(BaseModel):
    """Payload for POST /sms/auto-queue/{id}/reschedule."""

    scheduled_at: datetime = Field(..., description="New send time; snapped to the next legal slot when outside it")


class SmsAutoQueueActionResponse(BaseModel):
    """State of a planned automated SMS after a cancel or reschedule."""

    id: int
    status: str
    scheduled_at: datetime
