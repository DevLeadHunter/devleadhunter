"""
Pydantic schemas for email accounts.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from enums.email_account_type import EmailAccountType


class EmailAccountBase(BaseModel):
    """Base schema for email account."""

    email: EmailStr
    name: str = Field(..., max_length=255)
    account_type: EmailAccountType
    is_default: bool = False


class EmailAccountCreateCustomDomain(EmailAccountBase):
    """Schema for creating a custom domain email account."""

    account_type: EmailAccountType = EmailAccountType.CUSTOM_DOMAIN
    domain: str = Field(..., max_length=255)


class EmailAccountCreateGmail(EmailAccountBase):
    """Schema for creating a Gmail OAuth email account."""

    account_type: EmailAccountType = EmailAccountType.GMAIL_OAUTH
    oauth_code: str = Field(..., description="OAuth authorization code from Google")


class EmailAccountUpdate(BaseModel):
    """Schema for updating an email account."""

    name: str | None = Field(None, max_length=255)
    is_default: bool | None = None
    is_active: bool | None = None


class EmailAccountResponse(BaseModel):
    """Schema for email account response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    email: str
    name: str
    account_type: EmailAccountType
    is_verified: bool
    is_default: bool
    is_active: bool

    # Custom domain fields
    domain: str | None = None
    spf_verified: bool = False
    dkim_verified: bool = False

    # Gmail OAuth fields (don't expose tokens!)
    oauth_token_expires_at: datetime | None = None

    created_at: datetime
    updated_at: datetime | None = None


class GmailAuthUrlResponse(BaseModel):
    """Schema for Gmail OAuth authorization URL response."""

    auth_url: str
    state: str


class DNSVerificationResponse(BaseModel):
    """Schema for DNS verification response."""

    spf_verified: bool
    dkim_verified: bool
    is_verified: bool
    spf_record: str | None = None
    dkim_record: str | None = None
    instructions: str
