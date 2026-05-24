"""
Support ticket business logic service.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Sequence
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload, load_only

from core.config import settings
from enums.support_status import SupportTicketStatus
from enums.support_topic import SupportTicketTopic
from enums.user_role import UserRole
from models.support_attachment import SupportAttachment
from models.support_message import SupportMessage
from models.support_ticket import SupportTicket
from models.user import User
from schemas.support import (
    SupportAttachmentResponse,
    SupportMessageResponse,
    SupportTicketDetailResponse,
    SupportTicketSummaryResponse,
    SupportTopicOption,
)
from services.support_storage_service import StoredAttachment


class SupportService:
    """
    Encapsulates support ticket operations.
    """

    TOPIC_LABELS = {
        SupportTicketTopic.CREDITS_BILLING: (
            "Credits & billing",
            "Unexpected charge or missing credits after an action."
        ),
        SupportTicketTopic.MISSING_RESULTS: (
            "Missing results",
            "Search returned fewer results than expected."
        ),
        SupportTicketTopic.BUG_REPORT: (
            "Bug or anomaly",
            "Something is not working as intended."
        ),
        SupportTicketTopic.REFUND_CREDITS: (
            "Credit refund",
            "Request a refund in credits after an issue."
        ),
        SupportTicketTopic.REFUND_PAYMENT: (
            "Payment refund",
            "Request a card/Stripe payment refund."
        ),
        SupportTicketTopic.FEATURE_REQUEST: (
            "Feature request",
            "Share an idea to improve the experience."
        ),
        SupportTicketTopic.OTHER: (
            "Something else",
            "Any other support need."
        ),
    }

    def list_topics(self) -> List[SupportTopicOption]:
        """
        Return available support topics.
        """
        return [
            SupportTopicOption(value=topic, label=labels[0], description=labels[1])
            for topic, labels in self.TOPIC_LABELS.items()
        ]

    def create_ticket(
        self,
        db: Session,
        user: User,
        subject: str,
        topic: SupportTicketTopic,
        message: str,
        attachments: Optional[List[StoredAttachment]] = None,
    ) -> SupportTicket:
        """
        Create a new ticket with an initial message.
        """
        stored_attachments = attachments or []
        now = datetime.utcnow()

        ticket = SupportTicket(
            user_id=user.id,
            topic=topic.value,
            subject=subject.strip(),
            description=message.strip(),
            status=SupportTicketStatus.OPEN.value,
            last_message_at=now,
        )
        db.add(ticket)
        db.flush()

        initial_message = SupportMessage(
            ticket_id=ticket.id,
            sender_id=user.id,
            sender_role=user.role,
            content=message.strip(),
            created_at=now,
        )
        db.add(initial_message)
        db.flush()

        self._persist_attachments(
            db=db,
            ticket=ticket,
            message=initial_message,
            stored_attachments=stored_attachments,
        )

        db.commit()
        db.refresh(ticket, attribute_names=["attachments", "messages"])
        db.refresh(initial_message, attribute_names=["sender", "attachments"])
        return ticket

    def list_tickets(
        self,
        db: Session,
        current_user: User,
        *,
        scope: str = "mine",
        status_filter: Optional[SupportTicketStatus] = None,
        include_closed: bool = False,
    ) -> List[SupportTicket]:
        """
        Retrieve tickets for the current user or all (admin).
        """
        query = db.query(SupportTicket).options(
            joinedload(SupportTicket.user),
            selectinload(SupportTicket.attachments),
            selectinload(SupportTicket.messages).load_only(SupportMessage.id, SupportMessage.created_at),
        )

        if scope != "all" or current_user.role != UserRole.ADMIN.value:
            query = query.filter(SupportTicket.user_id == current_user.id)
        elif scope == "all":
            query = query.options(joinedload(SupportTicket.assigned_admin))

        if status_filter:
            query = query.filter(SupportTicket.status == status_filter.value)
        elif not include_closed:
            query = query.filter(SupportTicket.status != SupportTicketStatus.CLOSED.value)

        # MariaDB doesn't support NULLS LAST, so we use CASE to handle NULL values
        from sqlalchemy import case
        query = query.order_by(
            case((SupportTicket.last_message_at.is_(None), 1), else_=0),
            SupportTicket.last_message_at.desc(),
            SupportTicket.created_at.desc(),
        )

        return query.all()

    def get_ticket(
        self,
        db: Session,
        ticket_id: int,
        current_user: User,
    ) -> SupportTicket:
        """
        Retrieve a ticket ensuring access rights.
        """
        ticket = (
            db.query(SupportTicket)
            .options(
                joinedload(SupportTicket.user),
                joinedload(SupportTicket.assigned_admin),
                selectinload(SupportTicket.attachments),
                selectinload(SupportTicket.messages)
                .joinedload(SupportMessage.sender),
                selectinload(SupportTicket.messages)
                .selectinload(SupportMessage.attachments),
            )
            .filter(SupportTicket.id == ticket_id)
            .first()
        )
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found."
            )

        if current_user.role != UserRole.ADMIN.value and ticket.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this ticket."
            )

        return ticket

    def add_message(
        self,
        db: Session,
        ticket: SupportTicket,
        sender: User,
        content: str,
        attachments: Optional[List[StoredAttachment]] = None,
    ) -> SupportMessage:
        """
        Append a message to the conversation.
        """
        if ticket.status == SupportTicketStatus.CLOSED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This ticket is closed. Please create a new ticket."
            )

        now = datetime.utcnow()
        message = SupportMessage(
            ticket_id=ticket.id,
            sender_id=sender.id,
            sender_role=sender.role,
            content=content.strip(),
            created_at=now,
        )
        db.add(message)
        if hasattr(ticket, "messages") and ticket.messages is not None:
            ticket.messages.append(message)

        stored_attachments = attachments or []
        self._persist_attachments(
            db=db,
            ticket=ticket,
            message=message,
            stored_attachments=stored_attachments,
        )

        ticket.last_message_at = now
        if sender.role == UserRole.ADMIN.value:
            if ticket.status != SupportTicketStatus.RESOLVED.value:
                ticket.status = SupportTicketStatus.WAITING_USER.value
        else:
            if ticket.status in {
                SupportTicketStatus.RESOLVED.value,
                SupportTicketStatus.CLOSED.value,
            }:
                ticket.status = SupportTicketStatus.OPEN.value
            ticket.status = SupportTicketStatus.WAITING_SUPPORT.value
            ticket.closed_at = None

        db.commit()
        db.refresh(message, attribute_names=["sender", "attachments"])
        db.refresh(ticket, attribute_names=["status", "last_message_at", "attachments"])
        return message

    def update_status(
        self,
        db: Session,
        ticket: SupportTicket,
        status_value: SupportTicketStatus,
    ) -> SupportTicket:
        """
        Update the ticket status.
        """
        ticket.status = status_value.value
        if status_value in {SupportTicketStatus.RESOLVED, SupportTicketStatus.CLOSED}:
            ticket.closed_at = datetime.utcnow()
        else:
            ticket.closed_at = None

        db.commit()
        db.refresh(ticket)
        return ticket

    def to_summary_response(
        self,
        ticket: SupportTicket,
    ) -> SupportTicketSummaryResponse:
        """
        Serialize a ticket to summary schema.
        """
        messages_count = len(ticket.messages) if hasattr(ticket, "messages") else 0
        attachments_count = len(ticket.attachments) if hasattr(ticket, "attachments") else 0
        return SupportTicketSummaryResponse(
            id=ticket.id,
            user_id=ticket.user_id,
            user_name=ticket.user.name if ticket.user else "",
            topic=SupportTicketTopic(ticket.topic),
            subject=ticket.subject,
            description=ticket.description,
            status=SupportTicketStatus(ticket.status),
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            last_message_at=ticket.last_message_at,
            closed_at=ticket.closed_at,
            messages_count=messages_count,
            attachments_count=attachments_count,
        )

    def to_detail_response(
        self,
        ticket: SupportTicket,
    ) -> SupportTicketDetailResponse:
        """
        Serialize a ticket with conversation.
        """
        messages = [
            self.to_message_response(message)
            for message in sorted(ticket.messages, key=lambda msg: msg.created_at)
        ]
        return SupportTicketDetailResponse(
            id=ticket.id,
            user_id=ticket.user_id,
            user_name=ticket.user.name if ticket.user else "",
            topic=SupportTicketTopic(ticket.topic),
            subject=ticket.subject,
            description=ticket.description,
            status=SupportTicketStatus(ticket.status),
            created_at=ticket.created_at,
            updated_at=ticket.updated_at,
            last_message_at=ticket.last_message_at,
            closed_at=ticket.closed_at,
            attachments=[self._to_attachment_response(att) for att in ticket.attachments],
            messages=messages,
        )

    def to_message_response(self, message: SupportMessage) -> SupportMessageResponse:
        """
        Serialize a support message to schema.
        """
        sender_name = message.sender.name if message.sender else "Support"
        return SupportMessageResponse(
            id=message.id,
            ticket_id=message.ticket_id,
            sender_id=message.sender_id,
            sender_name=sender_name,
            sender_role=message.sender_role,
            content=message.content,
            attachments=[self._to_attachment_response(att) for att in message.attachments],
            created_at=message.created_at,
        )

    def _to_attachment_response(self, attachment: SupportAttachment) -> SupportAttachmentResponse:
        """
        Convert a DB attachment into API response.
        """
        return SupportAttachmentResponse(
            id=attachment.id,
            url=self._build_attachment_url(attachment.object_key),
            original_filename=attachment.original_filename,
            content_type=attachment.content_type,
            created_at=attachment.created_at,
        )

    def _persist_attachments(
        self,
        db: Session,
        ticket: SupportTicket,
        message: Optional[SupportMessage],
        stored_attachments: Sequence[StoredAttachment],
    ) -> None:
        """
        Persist stored attachment metadata into the database.
        """
        if not stored_attachments:
            return

        for stored in stored_attachments:
            attachment = SupportAttachment(
                ticket_id=ticket.id,
                message_id=message.id if message else None,
                object_key=stored.object_key,
                storage_backend=stored.backend,
                original_filename=stored.original_filename,
                content_type=stored.content_type,
            )
            db.add(attachment)
            if hasattr(ticket, "attachments") and ticket.attachments is not None:
                ticket.attachments.append(attachment)
            if message and hasattr(message, "attachments") and message.attachments is not None:
                message.attachments.append(attachment)
        db.flush()

    def _build_attachment_url(self, path: Optional[str]) -> Optional[str]:
        """
        Build a publicly accessible URL for an attachment.
        """
        if not path:
            return None

        if path.lower().startswith(("http://", "https://")):
            return path

        if settings.is_production and settings.support_ftp_public_base_url:
            base = settings.support_ftp_public_base_url.rstrip("/")
            return f"{base}/{path.lstrip('/')}"

        encoded = quote(path.strip("/"))
        base_url = settings.api_base_url.rstrip("/")
        return f"{base_url}{settings.api_prefix}/support/attachments/{encoded}"


support_service = SupportService()


