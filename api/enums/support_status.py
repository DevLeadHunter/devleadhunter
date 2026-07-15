"""
Support ticket status enumeration.
"""
from enum import Enum


class SupportTicketStatus(str, Enum):
    """
    Enumeration of possible statuses for a support ticket.
    """

    OPEN = "open"
    WAITING_USER = "waiting_user"
    WAITING_SUPPORT = "waiting_support"
    RESOLVED = "resolved"
    CLOSED = "closed"


__all__ = ["SupportTicketStatus"]


