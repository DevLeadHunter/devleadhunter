"""
Email account type enumeration.
"""
from enum import Enum


class EmailAccountType(str, Enum):
    """
    Email account type enumeration.
    
    Attributes:
        CUSTOM_DOMAIN: Custom domain with SPF/DKIM verification
        GMAIL_OAUTH: Gmail account connected via OAuth
    """
    CUSTOM_DOMAIN = "custom_domain"
    GMAIL_OAUTH = "gmail_oauth"
    RESEND = "resend"

