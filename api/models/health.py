"""
Health check models.
"""
from typing import Dict
from pydantic import BaseModel, ConfigDict, Field


class HealthStatus(BaseModel):
    """Health check status response."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "v1",
                "timestamp": "2024-01-15T10:30:00Z",
                "services": {
                    "database": "healthy",
                    "scrapers": "healthy",
                },
            }
        }
    )

    status: str = Field(..., description="Overall status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current timestamp")
    services: Dict[str, str] = Field(default_factory=dict, description="Service statuses")

