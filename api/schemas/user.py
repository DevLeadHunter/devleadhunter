"""
User Pydantic schemas for request/response validation.
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from enums.user_role import UserRole

_SIRET_PATTERN = re.compile(r"[0-9]{14}")


class UserBase(BaseModel):
    """
    Base user schema with common fields.

    Attributes:
        name: User's full name
        email: User's email address
        role: User role
        company_name: Optional business name for outreach branding
    """

    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    company_name: str | None = Field(None, max_length=255, description="Optional business name")
    company_website_url: str | None = Field(None, max_length=500, description="Optional business website URL")
    contact_phone: str | None = Field(None, max_length=30, description="Optional public phone (demo contact banner)")
    contact_email: str | None = Field(None, max_length=255, description="Optional public display email")
    postal_address: str | None = Field(
        None, max_length=500, description="Sender postal address printed in the footer of emails to Canada (CASL)"
    )
    siret: str | None = Field(None, max_length=14, description="French establishment number shown on demo legal pages")


class UserSignup(BaseModel):
    """
    Public self-service signup — role is never accepted from the client.
    """

    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, max_length=100, description="User's password")
    company_name: str | None = Field(None, max_length=255, description="Optional business name")


class UserCreate(UserBase):
    """
    Schema for creating a new user (super-admin only).

    Attributes:
        password: User's password
    """

    password: str = Field(..., min_length=6, max_length=100, description="User's password")


class ProfilePhotoResponse(BaseModel):
    """Profile photo state returned to the frontend (no file content)."""

    has_photo: bool


class UserUpdate(BaseModel):
    """
    Schema for updating user information.

    Attributes:
        name: User's full name
        email: User's email address
        company_name: Optional business name
    """

    name: str | None = Field(None, min_length=1, max_length=255, description="User's full name")
    email: EmailStr | None = Field(None, description="User's email address")
    site_sale_price_cents: int | None = Field(None, ge=0, description="Website sale price in cents (default 500 €)")
    assistant_monthly_price_cents: int | None = Field(
        None, ge=0, description="AI-assistant monthly subscription price in cents (default 79 €)"
    )
    assistant_annual_free_months: int | None = Field(
        None, ge=0, le=11, description="Months offered on the assistant annual plan (default 2 → 790 €/an)"
    )
    company_name: str | None = Field(None, max_length=255, description="Optional business name")
    company_website_url: str | None = Field(None, max_length=500, description="Optional business website URL")
    contact_phone: str | None = Field(None, max_length=30, description="Optional public phone (demo contact banner)")
    contact_email: str | None = Field(None, max_length=255, description="Optional public display email")
    postal_address: str | None = Field(
        None, max_length=500, description="Sender postal address printed in the footer of emails to Canada (CASL)"
    )
    siret: str | None = Field(None, max_length=20, description="French establishment number shown on demo legal pages")

    @field_validator("siret")
    @classmethod
    def _siret_digits_only(cls, value: str | None) -> str | None:
        """Keep the SIRET's 14 digits without their spaces; an empty value clears it."""
        if value is None:
            return None
        digits = "".join(value.split())
        if digits and not _SIRET_PATTERN.fullmatch(digits):
            raise ValueError("A SIRET has 14 digits")
        return digits


class AdminUserUpdate(UserUpdate):
    """
    Super-admin user management — can also change role and activation state.
    """

    role: UserRole | None = Field(None, description="User role (USER or ADMIN only)")
    is_active: bool | None = Field(None, description="Whether the user account is active")


class UserResponse(UserBase):
    """
    Schema for user response.

    Attributes:
        id: User's unique identifier
        is_active: Whether the user is active
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        credit_balance: Current credit balance (-1 for unlimited/admin)
        credits_available: Current credits available (-1 for unlimited/admin)
        credits_consumed: Total credits consumed
        onboarding_completed: Whether the post-signup setup wizard is done
    """

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    onboarding_completed: bool = Field(
        default=False, description="Whether the post-signup setup wizard (/configuration) has been completed"
    )
    site_sale_price_cents: int = Field(default=50000, description="Website sale price in cents (default 500 €)")
    assistant_monthly_price_cents: int = Field(
        default=7900, description="AI-assistant monthly subscription price in cents (default 79 €)"
    )
    assistant_annual_free_months: int = Field(
        default=2, description="Months offered on the assistant annual plan (default 2 → 790 €/an)"
    )
    credit_balance: int | None = Field(
        None, description="Current credit balance. -1 indicates unlimited credits (admin)"
    )
    credits_available: int | None = Field(
        None, description="Current credits available. -1 indicates unlimited credits (admin)"
    )
    credits_consumed: int | None = Field(None, description="Total credits consumed")

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """
    Schema for user login.

    Attributes:
        email: User's email address
        password: User's password
    """

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=1, description="User's password")


class Token(BaseModel):
    """
    Schema for authentication token.

    Attributes:
        access_token: JWT access token
        token_type: Token type (usually 'bearer')
    """

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Schema for token data.

    Attributes:
        email: User's email from token
    """

    email: str | None = None
