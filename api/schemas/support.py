"""
Pydantic schemas for support tickets and conversations.
"""
from datetime import datetime
from typing import Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from enums.support_status import SupportTicketStatus
from enums.support_topic import SupportTicketTopic


class SupportTopicOption(BaseModel):
    """
    Support topic metadata for UI presentation.
    """

    value: SupportTicketTopic
    label: str
    description: str


class SupportAttachmentResponse(BaseModel):
    """
    Representation of a stored attachment.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    original_filename: str
    content_type: str
    created_at: datetime


class SupportTicketCreate(BaseModel):
    """
    Payload for creating a new support ticket.
    """

    topic: SupportTicketTopic
    subject: str = Field(..., min_length=4, max_length=255)
    message: str = Field(..., min_length=10, max_length=5000)


class SupportTicketStatusUpdate(BaseModel):
    """
    Payload for updating a ticket status.
    """

    status: SupportTicketStatus


class SupportTicketUpdate(BaseModel):
    """
    Payload for updating a support ticket.
    """

    topic: Optional[SupportTicketTopic] = None
    subject: Optional[str] = Field(None, min_length=4, max_length=255)
    status: Optional[SupportTicketStatus] = None


class SupportMessageCreate(BaseModel):
    """
    Payload for posting a new support message.
    """

    message: str = Field(..., min_length=1, max_length=5000)


class SupportMessageResponse(BaseModel):
    """
    Support message representation.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    sender_id: int
    sender_name: str
    sender_role: str
    content: str
    attachments: Sequence[SupportAttachmentResponse]
    created_at: datetime


class SupportTicketBaseResponse(BaseModel):
    """
    Common fields for support ticket responses.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_name: str
    topic: SupportTicketTopic
    subject: str
    description: str
    status: SupportTicketStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class SupportTicketResponse(SupportTicketBaseResponse):
    """
    Basic representation of a support ticket.
    """

    pass


class SupportTicketSummaryResponse(SupportTicketBaseResponse):
    """
    Summary representation of a support ticket.
    """

    messages_count: int
    attachments_count: int


class SupportTicketDetailResponse(SupportTicketBaseResponse):
    """
    Detailed representation containing the full conversation.
    """

    attachments: Sequence[SupportAttachmentResponse]
    messages: Sequence[SupportMessageResponse]


