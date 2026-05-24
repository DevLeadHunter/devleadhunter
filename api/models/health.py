"""
Health check models.
"""
from typing import Dict
from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """
    Health check status response.
    
    Attributes:
        status: Overall health status
        version: API version
        timestamp: Current server timestamp
        services: Status of individual services
    """
    
    status: str = Field(..., description="Overall status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current timestamp")
    services: Dict[str, str] = Field(default_factory=dict, description="Service statuses")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "v1",
                "timestamp": "2024-01-15T10:30:00Z",
                "services": {
                    "database": "healthy",
                    "scrapers": "healthy"
                }
            }
        }

