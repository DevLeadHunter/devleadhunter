"""
Search request and response models.
"""

from pydantic import BaseModel, ConfigDict, Field

from enums.source import Source

from .prospect import Prospect


class ProspectSearchRequest(BaseModel):
    """Model for prospect search requests."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category": "restaurant",
                "city": "Paris",
                "source": "google",
                "max_results": 50,
            }
        }
    )

    category: str | None = Field(None, description="Business category")
    city: str | None = Field(None, description="City name")
    source: Source | None = Field(Source.ALL, description="Data source to search in")
    max_results: int = Field(50, ge=1, le=1000, description="Maximum results to return")
    only_without_website: bool = Field(
        True,
        description="When True, only return prospects without an existing website",
    )


class ProspectSearchResponse(BaseModel):
    """
    Model for prospect search responses.

    Attributes:
        total: Total number of prospects found
        prospects: List of prospect objects
        has_website: Number of prospects with websites
        without_website: Number of prospects without websites
    """

    total: int = Field(..., description="Total number of prospects")
    prospects: list[Prospect] = Field(..., description="List of prospects")
    has_website: int = Field(..., description="Number with websites")
    without_website: int = Field(..., description="Number without websites")
