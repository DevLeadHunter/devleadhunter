"""
Scraping job models for managing async scraping tasks.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    """Job status enumeration."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    # User cancelled the search (e.g. launched by mistake). Prospects already
    # found are kept — cancellation just stops the scrape gracefully.
    CANCELLED = "cancelled"


class ScrapingJobCreate(BaseModel):
    """Model for creating a scraping job."""

    category: str | None = Field(None, description="Business category")
    city: str | None = Field(None, description="City name")
    country: str = Field("FR", min_length=2, max_length=2, description="ISO alpha-2 search country (FR, CH, BE, LU)")
    max_results: int = Field(50, description="Maximum results to fetch")
    source: str | None = Field(None, description="Source filter (google, pagesjaunes, etc.)")
    skip_duplicates: bool = Field(True, description="Skip duplicate prospects")
    only_without_website: bool = Field(
        True,
        description="When True, only keep prospects without an existing website",
    )
    # Facebook match loop: extra rounds are separate jobs pointing at the user's
    # original search, so the UI can present one search instead of N rounds.
    parent_job_id: str | None = Field(None, description="Origin job when this job is an automatic extra round")


class ScrapingJobProgress(BaseModel):
    """Model for tracking job progress."""

    current: int = Field(0, description="Current number of prospects processed")
    total: int = Field(0, description="Total expected prospects")
    percentage: float = Field(0.0, description="Progress percentage")
    current_prospect: str | None = Field(None, description="Currently processing prospect")
    estimated_time_remaining: int | None = Field(None, description="Estimated seconds remaining")


class ScrapingJob(BaseModel):
    """Complete scraping job model."""

    model_config = ConfigDict(
        json_schema_extra={
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
                    "estimated_time_remaining": 120,
                },
                "results": [1, 2, 3],
                "skipped_duplicates": 2,
                "created_at": "2024-01-15T10:30:00Z",
            }
        }
    )

    id: str = Field(..., description="Unique job identifier")
    user_id: int = Field(..., description="User ID who created the job")
    status: JobStatus = Field(JobStatus.PENDING, description="Current job status")
    category: str | None = Field(None, description="Business category")
    city: str | None = Field(None, description="City name")
    country: str = Field("FR", description="ISO alpha-2 search country (FR, CH, BE, LU)")
    max_results: int = Field(50, description="Maximum results to fetch")
    source: str | None = Field(None, description="Source filter")
    skip_duplicates: bool = Field(True, description="Skip duplicate prospects")
    only_without_website: bool = Field(
        True,
        description="When True, only keep prospects without an existing website",
    )
    progress: ScrapingJobProgress = Field(default_factory=ScrapingJobProgress, description="Job progress")
    logs: list[str] = Field(default_factory=list, description="Live log lines for the job")
    live_prospects: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Prospects saved during the job (for reconnect / polling)",
    )
    results: list[int] = Field(default_factory=list, description="List of prospect IDs created")
    skipped_duplicates: int = Field(0, description="Number of duplicates skipped")
    # Facebook discovery: pages skipped because a previous search already tested and
    # rejected them — lets the client explain an « exhausted » run honestly.
    known_pages_skipped: int = Field(0, description="Pages skipped as already tested by past searches")
    parent_job_id: str | None = Field(None, description="Origin job when this job is an automatic extra round")
    error: str | None = Field(None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    started_at: datetime | None = Field(None, description="Start timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")
