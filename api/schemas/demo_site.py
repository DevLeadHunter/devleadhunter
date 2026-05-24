"""Pydantic schemas for demo site generation."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class DemoSiteCreateRequest(BaseModel):
    """Payload to create a demo site from the stepper tunnel."""

    business_name: str = Field(..., min_length=2, max_length=255)
    template_id: str = Field(default="plumber-simple", max_length=64)
    phone: Optional[str] = Field(default=None, max_length=64)
    email: EmailStr
    city: Optional[str] = Field(default=None, max_length=128)
    description: Optional[str] = Field(default=None, max_length=2000)


class DemoSiteUpdateRequest(BaseModel):
    """Partial update payload for an existing demo site."""

    business_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    template_id: Optional[str] = Field(default=None, max_length=64)
    phone: Optional[str] = Field(default=None, max_length=64)
    email: Optional[EmailStr] = None
    city: Optional[str] = Field(default=None, max_length=128)
    description: Optional[str] = Field(default=None, max_length=2000)


class DemoSiteTemplateResponse(BaseModel):
    """Available site template metadata."""

    id: str
    name: str
    description: str
    preview_image_url: Optional[str] = None


class DemoSiteResponse(BaseModel):
    """Demo site returned to authenticated users."""

    id: int
    slug: str
    template_id: str
    business_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    description: Optional[str] = None
    status: str
    demo_url: Optional[str] = None
    demo_url_live: bool = False
    local_demo_url: Optional[str] = None
    verification_message: Optional[str] = None
    storyblok_editor_url: Optional[str] = None
    storyblok_login_email: Optional[str] = None
    storyblok_login_password: Optional[str] = None
    storyblok_invite_sent: bool = False
    expires_at: datetime
    created_at: datetime
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class DemoSitePublicResponse(BaseModel):
    """Public payload consumed by demo.dibodev.fr/{slug}."""

    slug: str
    business_name: str
    template_id: str
    storyblok_space_id: Optional[int] = None
    storyblok_public_token: Optional[str] = None
    storyblok_preview_token: Optional[str] = None
    content_json: Optional[dict] = None
    status: str
    expires_at: datetime

    model_config = {"from_attributes": True}


class DemoSiteListResponse(BaseModel):
    """Paginated list of demo sites for the current user."""

    items: list[DemoSiteResponse]
    total: int
