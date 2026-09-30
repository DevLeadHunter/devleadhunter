"""
Scheduled email status enumeration.
"""

from enum import Enum


class ScheduledEmailStatus(str, Enum):
    """
    Lifecycle of an email planned for later.

    Attributes:
        PENDING: Waiting for its time
        SENDING: Claimed by the worker, send in progress
        SENT: Went out
        FAILED: The send failed (the user can reschedule it)
        CANCELLED: Cancelled by the user
    """

    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"
