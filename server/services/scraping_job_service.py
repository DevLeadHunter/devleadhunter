"""
Scraping job service for managing async scraping tasks.
"""
import asyncio
import time
from datetime import datetime
from typing import Dict, Optional, List
from uuid import uuid4
import logging

from sqlalchemy.orm import Session
from models.scraping_job import ScrapingJob, ScrapingJobCreate, JobStatus, ScrapingJobProgress
from models.prospect import ProspectCreate
from services.scraper_service import scraper_service
from services.prospect_service import prospect_service

logger = logging.getLogger(__name__)


class ScrapingJobService:
    """
    Service for managing scraping jobs.
    
    This service handles the lifecycle of scraping jobs including
    creation, execution, progress tracking, and result storage.
    """
    
    def __init__(self):
        """Initialize the scraping job service."""
        self._jobs: Dict[str, ScrapingJob] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
    
    def create_job(
        self,
        user_id: int,
        job_data: ScrapingJobCreate
    ) -> ScrapingJob:
        """
        Create a new scraping job.
        
        Args:
            user_id: ID of the user creating the job
            job_data: Job configuration data
            
        Returns:
            Created scraping job
        """
        job_id = f"job_{uuid4().hex[:12]}"
        
        job = ScrapingJob(
            id=job_id,
            user_id=user_id,
            status=JobStatus.PENDING,
            category=job_data.category,
            city=job_data.city,
            max_results=job_data.max_results,
            source=job_data.source,
            skip_duplicates=job_data.skip_duplicates
        )
        
        self._jobs[job_id] = job
        logger.info(f"Created job {job_id} for user {user_id}")
        
        return job
    
    def get_job(self, job_id: str) -> Optional[ScrapingJob]:
        """
        Get a job by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job if found, None otherwise
        """
        return self._jobs.get(job_id)
    
    def get_user_jobs(self, user_id: int) -> List[ScrapingJob]:
        """
        Get all jobs for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of user's jobs
        """
        return [job for job in self._jobs.values() if job.user_id == user_id]
    
    async def execute_job(
        self,
        job_id: str,
        db: Session
    ) -> None:
        """
        Execute a scraping job asynchronously.
        
        Args:
            job_id: Job identifier
            db: Database session
        """
        job = self._jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return
        
        try:
            # Update job status
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            logger.info(f"Starting job {job_id}")
            
            start_time = time.time()
            
            # Run scrapers
            scraped_prospects: List[ProspectCreate] = await scraper_service.scrape_all(
                category=job.category or "",
                city=job.city or "",
                max_results=job.max_results,
                source_filter=job.source
            )
            
            logger.info(f"Job {job_id}: Scraped {len(scraped_prospects)} prospects")
            
            # Update progress
            job.progress.total = len(scraped_prospects)
            
            # Save prospects to database
            created_prospects = []
            skipped_count = 0
            
            for i, prospect_data in enumerate(scraped_prospects):
                try:
                    # Update progress
                    job.progress.current = i + 1
                    job.progress.percentage = ((i + 1) / len(scraped_prospects)) * 100
                    job.progress.current_prospect = prospect_data.name
                    
                    # Estimate time remaining
                    elapsed_time = time.time() - start_time
                    avg_time_per_prospect = elapsed_time / (i + 1)
                    remaining_prospects = len(scraped_prospects) - (i + 1)
                    job.progress.estimated_time_remaining = int(avg_time_per_prospect * remaining_prospects)
                    
                    # Check for duplicates if enabled
                    if job.skip_duplicates:
                        is_duplicate = await prospect_service.check_duplicate(
                            db=db,
                            name=prospect_data.name,
                            city=prospect_data.city,
                            user_id=job.user_id
                        )
                        if is_duplicate:
                            skipped_count += 1
                            logger.debug(f"Job {job_id}: Skipped duplicate prospect: {prospect_data.name}")
                            continue
                    
                    # Create prospect
                    created = await prospect_service.create_prospect(
                        db=db,
                        prospect=prospect_data,
                        user_id=job.user_id
                    )
                    created_prospects.append(created)
                    job.results.append(created.id)
                    
                    # Small delay to allow other operations
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    logger.error(f"Job {job_id}: Error processing prospect {prospect_data.name}: {e}")
                    continue
            
            # Mark job as completed
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.skipped_duplicates = skipped_count
            job.progress.current = len(scraped_prospects)
            job.progress.percentage = 100.0
            job.progress.estimated_time_remaining = 0
            
            logger.info(f"Job {job_id} completed: {len(created_prospects)} prospects created, {skipped_count} duplicates skipped")
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}", exc_info=True)
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.utcnow()
        finally:
            # Cleanup task reference
            if job_id in self._running_tasks:
                del self._running_tasks[job_id]
    
    def start_job(
        self,
        job_id: str,
        db: Session
    ) -> None:
        """
        Start executing a job in the background.
        
        Args:
            job_id: Job identifier
            db: Database session
        """
        if job_id in self._running_tasks:
            logger.warning(f"Job {job_id} is already running")
            return
        
        # Create background task
        task = asyncio.create_task(self.execute_job(job_id, db))
        self._running_tasks[job_id] = task
        logger.info(f"Started background task for job {job_id}")
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if deleted, False if not found
        """
        if job_id in self._jobs:
            # Cancel running task if exists
            if job_id in self._running_tasks:
                self._running_tasks[job_id].cancel()
                del self._running_tasks[job_id]
            
            del self._jobs[job_id]
            logger.info(f"Deleted job {job_id}")
            return True
        return False
    
    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed/failed jobs.
        
        Args:
            max_age_hours: Maximum age in hours to keep jobs
            
        Returns:
            Number of jobs deleted
        """
        now = datetime.utcnow()
        deleted_count = 0
        
        jobs_to_delete = []
        for job_id, job in self._jobs.items():
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
                age_hours = (now - job.created_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    jobs_to_delete.append(job_id)
        
        for job_id in jobs_to_delete:
            if self.delete_job(job_id):
                deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old jobs")
        
        return deleted_count


# Global service instance
scraping_job_service = ScrapingJobService()

