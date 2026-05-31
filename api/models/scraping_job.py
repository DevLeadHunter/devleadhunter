"""
Scraping job models for managing async scraping tasks.
"""
from typing import Any, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ScrapingJobCreate(BaseModel):
    """Model for creating a scraping job."""
    category: Optional[str] = Field(None, description="Business category")
    city: Optional[str] = Field(None, description="City name")
    max_results: int = Field(50, description="Maximum results to fetch")
    source: Optional[str] = Field(None, description="Source filter (google, pagesjaunes, etc.)")
    skip_duplicates: bool = Field(True, description="Skip duplicate prospects")
    only_without_website: bool = Field(
        True,
        description="When True, only keep prospects without an existing website",
    )


class ScrapingJobProgress(BaseModel):
    """Model for tracking job progress."""
    current: int = Field(0, description="Current number of prospects processed")
    total: int = Field(0, description="Total expected prospects")
    percentage: float = Field(0.0, description="Progress percentage")
    current_prospect: Optional[str] = Field(None, description="Currently processing prospect")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated seconds remaining")


class ScrapingJob(BaseModel):
    """Complete scraping job model."""
    id: str = Field(..., description="Unique job identifier")
    user_id: int = Field(..., description="User ID who created the job")
    status: JobStatus = Field(JobStatus.PENDING, description="Current job status")
    category: Optional[str] = Field(None, description="Business category")
    city: Optional[str] = Field(None, description="City name")
    max_results: int = Field(50, description="Maximum results to fetch")
    source: Optional[str] = Field(None, description="Source filter")
    skip_duplicates: bool = Field(True, description="Skip duplicate prospects")
    only_without_website: bool = Field(
        True,
        description="When True, only keep prospects without an existing website",
    )
    progress: ScrapingJobProgress = Field(default_factory=ScrapingJobProgress, description="Job progress")
    logs: List[str] = Field(default_factory=list, description="Live log lines for the job")
    live_prospects: List[dict[str, Any]] = Field(
        default_factory=list,
        description="Prospects saved during the job (for reconnect / polling)",
    )
    results: List[int] = Field(default_factory=list, description="List of prospect IDs created")
    skipped_duplicates: int = Field(0, description="Number of duplicates skipped")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "job_123abc",
                "user_id": 1,
                "status": "running",
                "category": "restaurant",
                "city": "Paris",
                "max_results": 50,
                "source": "google",
                "skip_duplicates": True,
                "progress": {
                    "current": 15,
                    "total": 50,
                    "percentage": 30.0,
                    "current_prospect": "Le Bon Restaurant",
                    "estimated_time_remaining": 120
                },
                "results": [1, 2, 3],
                "skipped_duplicates": 2,
                "created_at": "2024-01-15T10:30:00Z"
            }
        }

