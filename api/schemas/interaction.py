"""
Pydantic schemas for prospect interactions.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InteractionCreate(BaseModel):
    """Schema for creating a new interaction."""

    interaction_type: str = Field(..., max_length=50, description="Type of interaction")
    description: str = Field(..., description="Description of the interaction")
    metadata: dict | None = Field(None, description="Additional metadata")


class InteractionResponse(BaseModel):
    """Schema for interaction response."""

    id: int
    prospect_id: int
    user_id: int
    interaction_type: str
    description: str
    interaction_metadata: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InteractionListResponse(BaseModel):
    """Schema for interaction list response."""

    interactions: list[InteractionResponse]
    total: int

    model_config = ConfigDict(from_attributes=True)
