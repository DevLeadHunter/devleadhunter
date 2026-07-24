"""Pydantic schemas for the organizations API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class CreateOrganizationRequest(BaseModel):
    """Payload to create an organization."""

    name: str = Field(..., min_length=2, max_length=255, description="Organization display name")


class InviteMemberRequest(BaseModel):
    """Payload to add an existing user to the caller's organization."""

    email: EmailStr = Field(..., description="Account email of the user to invite")


class OrganizationMemberResponse(BaseModel):
    """A member of the organization (with resolved identity)."""

    user_id: int = Field(..., description="Member user id")
    name: str = Field(..., description="Member display name")
    email: str = Field(..., description="Member account email")
    role: str = Field(..., description="owner or member")
    joined_at: datetime | None = Field(None, description="When the user joined")


class OrganizationResponse(BaseModel):
    """The caller's organization with its members."""

    id: int = Field(..., description="Organization id")
    name: str = Field(..., description="Organization display name")
    owner_user_id: int = Field(..., description="Owner user id")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    members: list[OrganizationMemberResponse] = Field(default_factory=list, description="All members, owner included")
