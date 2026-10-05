"""Desktop jobs: work a device without the desktop app leaves for the owner's computer, which does it in the background."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from enums.desktop_job import DesktopJobKind
from models.desktop_job import DesktopJob
from models.user import User
from schemas.desktop_job import DesktopJobCreateRequest, DesktopJobFailureRequest, DesktopJobResponse
from services.auth_service import require_auth
from services.desktop_job_relay import desktop_job_relay
from services.prospect_search.desktop_app_presence import desktop_app_presence

router = APIRouter(prefix="/desktop-jobs", tags=["desktop-jobs"])


def _job_or_404(db: Session, user: User, job_id: int) -> DesktopJob:
    """Fetch a job owned by the caller, or answer 404."""
    job = desktop_job_relay.get_for_user(db, user.id, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Desktop job not found")
    return job


@router.get("", response_model=list[DesktopJobResponse])
async def list_active_desktop_jobs(
    kind: DesktopJobKind | None = Query(None, description="Only this kind of work"),
    subject_id: int | None = Query(None, description="Only the work about this record"),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[DesktopJobResponse]:
    """The caller's jobs still waiting for a computer or being done, for the dashboard to show where they stand."""
    jobs = desktop_job_relay.active_jobs(db, current_user.id, kind)
    if subject_id is not None:
        jobs = [job for job in jobs if job.subject_id == subject_id]
    return [DesktopJobResponse.model_validate(job) for job in jobs]


@router.get("/waiting", response_model=list[DesktopJobResponse])
async def list_waiting_desktop_jobs(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[DesktopJobResponse]:
    """The jobs the caller's desktop app must take, oldest first. Only the desktop app calls this: it marks it on."""
    desktop_app_presence.mark_seen(current_user.id)
    return [DesktopJobResponse.model_validate(job) for job in desktop_job_relay.waiting_jobs(db, current_user.id)]


@router.post("", response_model=DesktopJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def request_desktop_job(
    payload: DesktopJobCreateRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DesktopJobResponse:
    """Leave work for the owner's desktop app, from a device that cannot do it; the same work asked twice is one job."""
    try:
        job = desktop_job_relay.request(db, current_user.id, payload.kind, payload.subject_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DesktopJobResponse.model_validate(job)


@router.delete("/{job_id}", response_model=DesktopJobResponse)
async def cancel_desktop_job(
    job_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DesktopJobResponse:
    """Withdraw a job before a computer takes it; refused while the desktop app is doing it."""
    job = _job_or_404(db, current_user, job_id)
    try:
        job = desktop_job_relay.cancel(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DesktopJobResponse.model_validate(job)


@router.post("/{job_id}/claim", response_model=DesktopJobResponse)
async def claim_desktop_job(
    job_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DesktopJobResponse:
    """Tell that the caller's desktop app starts the job, so nothing else takes it."""
    job = _job_or_404(db, current_user, job_id)
    try:
        job = desktop_job_relay.claim(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DesktopJobResponse.model_validate(job)


@router.post("/{job_id}/done", response_model=DesktopJobResponse)
async def complete_desktop_job(
    job_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DesktopJobResponse:
    """Close a job whose result the desktop app already saved through the usual routes."""
    job = _job_or_404(db, current_user, job_id)
    try:
        job = desktop_job_relay.complete(db, job)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DesktopJobResponse.model_validate(job)


@router.post("/{job_id}/fail", response_model=DesktopJobResponse)
async def fail_desktop_job(
    job_id: int,
    payload: DesktopJobFailureRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> DesktopJobResponse:
    """Close a job the desktop app could not do, with the reason the dashboard shows."""
    job = _job_or_404(db, current_user, job_id)
    try:
        job = desktop_job_relay.fail(db, job, payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DesktopJobResponse.model_validate(job)
