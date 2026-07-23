"""
Pydantic schemas for email signatures.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class EmailSignatureBase(BaseModel):
    """Base schema for an email signature."""
    name: str = Field(..., max_length=255)
    content_html: str
    is_default: bool = False


class EmailSignatureCreate(EmailSignatureBase):
    """Schema for creating an email signature."""
    pass


class EmailSignatureUpdate(BaseModel):
    """Schema for updating an email signature (all fields optional)."""
    name: Optional[str] = Field(None, max_length=255)
    content_html: Optional[str] = None
    is_default: Optional[bool] = None


class EmailSignatureResponse(BaseModel):
    """Schema for an email signature response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    content_html: str
    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
