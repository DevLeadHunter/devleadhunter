"""
Email status enumeration.
"""
from enum import Enum


class EmailStatus(str, Enum):
    """
    Email status enumeration.
    
    Attributes:
        PENDING: Email is queued for sending
        SENDING: Email is being sent
        SENT: Email was successfully sent
        DELIVERED: Email was delivered to recipient
        OPENED: Email was opened by recipient
        CLICKED: Links in email were clicked
        BOUNCED: Email bounced
        FAILED: Email sending failed
        COMPLAINED: Recipient marked as spam
    """
    PENDING = "pending"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    COMPLAINED = "complained"

