"""
Scraping job management routes.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from models.scraping_job import ScrapingJob, ScrapingJobCreate
from models.user import User
from services.scraping_job_service import scraping_job_service
from services.auth_service import require_auth
from core.database import get_db


router = APIRouter(
    prefix="/scraping-jobs",
    tags=["scraping-jobs"]
)


@router.post(
    "",
    response_model=ScrapingJob,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scraping job",
    description="Create a new scraping job that runs asynchronously"
)
async def create_scraping_job(
    job_data: ScrapingJobCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
) -> ScrapingJob:
    """
    Create a new scraping job.
    
    The job will run in the background and you can check its status
    by polling the GET /scraping-jobs/{job_id} endpoint.
    
    Args:
        job_data: Job configuration
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Created scraping job
        
    Example:
        >>> POST /scraping-jobs
        {
            "category": "restaurant",
            "city": "Paris",
            "max_results": 50,
            "source": "google",
            "skip_duplicates": true
        }
    """
    try:
        # Create job
        job = scraping_job_service.create_job(
            user_id=current_user.id,
            job_data=job_data
        )
        
        # Start job in background
        scraping_job_service.start_job(job.id, db)
        
        return job
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create scraping job: {str(e)}"
        )


@router.get(
    "/{job_id}",
    response_model=ScrapingJob,
    summary="Get scraping job status",
    description="Get the current status and progress of a scraping job"
)
async def get_scraping_job(
    job_id: str,
    current_user: User = Depends(require_auth)
) -> ScrapingJob:
    """
    Get a scraping job by ID.
    
    Args:
        job_id: Job identifier
        current_user: Current authenticated user
        
    Returns:
        Scraping job with current status
        
    Raises:
        HTTPException: If job not found or not owned by user
    """
    job = scraping_job_service.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Check ownership
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job"
        )
    
    return job


@router.get(
    "",
    response_model=List[ScrapingJob],
    summary="List user's scraping jobs",
    description="Get all scraping jobs for the current user"
)
async def list_scraping_jobs(
    current_user: User = Depends(require_auth)
) -> List[ScrapingJob]:
    """
    Get all scraping jobs for the current user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of user's scraping jobs
    """
    return scraping_job_service.get_user_jobs(current_user.id)


@router.delete(
    "/{job_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a scraping job",
    description="Delete a scraping job (will cancel if running)"
)
async def delete_scraping_job(
    job_id: str,
    current_user: User = Depends(require_auth)
) -> None:
    """
    Delete a scraping job.
    
    Args:
        job_id: Job identifier
        current_user: Current authenticated user
        
    Raises:
        HTTPException: If job not found or not owned by user
    """
    job = scraping_job_service.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Check ownership
    if job.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job"
        )
    
    scraping_job_service.delete_job(job_id)

