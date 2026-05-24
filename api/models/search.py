"""
Search request and response models.
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from .prospect import Prospect
from enums.source import Source


class ProspectSearchRequest(BaseModel):
    """
    Model for prospect search requests.
    
    Attributes:
        category: Business category to search for
        city: City to search in
        source: Data source to search in (optional, default: all)
        max_results: Maximum number of results to return
    """
    
    category: Optional[str] = Field(None, description="Business category")
    city: Optional[str] = Field(None, description="City name")
    source: Optional[Source] = Field(Source.ALL, description="Data source to search in")
    max_results: int = Field(50, ge=1, le=1000, description="Maximum results to return")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "category": "restaurant",
                "city": "Paris",
                "source": "google",
                "max_results": 50
            }
        }


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
    prospects: List[Prospect] = Field(..., description="List of prospects")
    has_website: int = Field(..., description="Number with websites")
    without_website: int = Field(..., description="Number without websites")

