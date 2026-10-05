"""
Prospect search routes — one objective-driven search instead of a choice of sources.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.prospect_search import ProspectSearch
from models.prospect_search_candidate import ProspectSearchCandidate
from models.user import User
from schemas.prospect_search import (
    CandidateDecisions,
    CandidateDecisionsOutcome,
    FacebookContactPayload,
    ProspectSearchActivity,
    ProspectSearchCandidateResponse,
    ProspectSearchCreate,
    ProspectSearchDetail,
    ProspectSearchSummary,
    SearchBrowserTask,
    SearchTradeOption,
)
from services.auth_service import require_auth
from services.prospect_search.desktop_app_presence import desktop_app_presence
from services.prospect_search.facebook_contact import FacebookContactRead
from services.prospect_search.service import ProspectSearchError, prospect_search_service
from services.prospect_search.trade_catalog import TradeCatalog

router = APIRouter(prefix="/prospect-searches", tags=["prospect-searches"])

_SEARCH_NOT_FOUND: str = "Recherche introuvable"
_CANDIDATE_NOT_FOUND: str = "Candidat introuvable"


def _summaries(db: Session, searches: list[ProspectSearch]) -> list[ProspectSearchSummary]:
    """Project searches into their summary, counted in one query."""
    counts = prospect_search_service.trade_counts(db, searches)
    summaries: list[ProspectSearchSummary] = []
    for search in searches:
        summary = ProspectSearchSummary.model_validate(search)
        summary.trade_counts = counts.get(search.id, [])
        summaries.append(summary)
    return summaries


def _detail(db: Session, search: ProspectSearch) -> ProspectSearchDetail:
    """Project a search into its detail: totals, journal and candidates."""
    detail = ProspectSearchDetail.model_validate(search)
    detail.trade_counts = prospect_search_service.trade_counts(db, [search]).get(search.id, [])
    detail.candidates = [
        ProspectSearchCandidateResponse.model_validate(candidate)
        for candidate in prospect_search_service.candidates_of(db, search)
    ]
    return detail


def _candidate_or_404(candidate: ProspectSearchCandidate | None) -> ProspectSearchCandidateResponse:
    """The candidate's public shape, or a 404."""
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_CANDIDATE_NOT_FOUND)
    return ProspectSearchCandidateResponse.model_validate(candidate)


@router.get("/trades", response_model=list[SearchTradeOption])
async def list_search_trades(current_user: User = Depends(require_auth)) -> list[SearchTradeOption]:
    """Trades the search knows how to recognise, for the form's suggestions."""
    return [SearchTradeOption(key=profile.key, label=profile.label) for profile in TradeCatalog.profiles()]


@router.post("", response_model=ProspectSearchDetail, status_code=status.HTTP_201_CREATED)
async def create_prospect_search(
    payload: ProspectSearchCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ProspectSearchDetail:
    """Create a search from an objective and start it in the background, or queue it behind the search at work."""
    try:
        search = prospect_search_service.create(db, current_user.id, payload)
    except ProspectSearchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    prospect_search_service.start_or_queue(db, search)
    return _detail(db, search)


@router.get("", response_model=list[ProspectSearchSummary])
async def list_prospect_searches(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[ProspectSearchSummary]:
    """The user's recent searches with their totals."""
    return _summaries(db, prospect_search_service.list_for_user(db, current_user.id))


# The fixed paths below are declared before « /{search_id} », which would otherwise take them for a search id.
@router.get("/pending-candidates", response_model=list[ProspectSearchCandidateResponse])
async def list_pending_candidates(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[ProspectSearchCandidateResponse]:
    """The candidates of every search of the user that wait for a decision, newest first."""
    return [
        ProspectSearchCandidateResponse.model_validate(candidate)
        for candidate in prospect_search_service.pending_candidates(db, current_user.id)
    ]


@router.get("/activity", response_model=ProspectSearchActivity)
async def get_prospect_search_activity(
    from_desktop_app: bool = Query(
        False, description="Set by the desktop app, which reads the Facebook pages: it is then known to be on"
    ),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ProspectSearchActivity:
    """How many candidates wait for the user, the search still at work, the ones queued behind it, and the PC."""
    if from_desktop_app:
        desktop_app_presence.mark_seen(current_user.id)
    active_search = prospect_search_service.active_search(db, current_user.id)
    return ProspectSearchActivity(
        pending_count=prospect_search_service.pending_candidate_count(db, current_user.id),
        active_search=_summaries(db, [active_search])[0] if active_search is not None else None,
        queued_searches=_summaries(db, prospect_search_service.queued_searches(db, current_user.id)),
        is_desktop_app_online=desktop_app_presence.is_online(current_user.id),
    )


@router.post("/candidates/decisions", response_model=CandidateDecisionsOutcome)
async def decide_candidates(
    payload: CandidateDecisions,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> CandidateDecisionsOutcome:
    """Accept and refuse several candidates at once, from any of the user's searches."""
    return await prospect_search_service.decide_candidates(db, current_user.id, payload)


@router.get("/{search_id}", response_model=ProspectSearchDetail)
async def get_prospect_search(
    search_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ProspectSearchDetail:
    """A search with its journal and every candidate it looked at."""
    search = prospect_search_service.get_for_user(db, current_user.id, search_id)
    if search is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SEARCH_NOT_FOUND)
    return _detail(db, search)


@router.post("/{search_id}/cancel", response_model=ProspectSearchDetail)
async def cancel_prospect_search(
    search_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ProspectSearchDetail:
    """Stop a search; what it found is kept."""
    search = prospect_search_service.cancel(db, current_user.id, search_id)
    if search is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SEARCH_NOT_FOUND)
    return _detail(db, search)


@router.post("/{search_id}/resume", response_model=ProspectSearchDetail)
async def resume_prospect_search(
    search_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ProspectSearchDetail:
    """Carry on a search that stopped short of its objective, or queue it behind the search at work."""
    try:
        search = prospect_search_service.resume(db, current_user.id, search_id)
    except ProspectSearchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if search is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SEARCH_NOT_FOUND)
    return _detail(db, search)


@router.get("/{search_id}/browser-tasks", response_model=list[SearchBrowserTask])
async def list_browser_tasks(
    search_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[SearchBrowserTask]:
    """Facebook pages the desktop app must read for the search's waiting candidates."""
    candidates = prospect_search_service.browser_tasks(db, current_user.id, search_id)
    if candidates is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=_SEARCH_NOT_FOUND)
    return [
        SearchBrowserTask(
            candidate_id=candidate.id,
            name=candidate.name,
            facebook_url=candidate.facebook_url or "",
            country=candidate.country,
        )
        for candidate in candidates
    ]


@router.post("/{search_id}/candidates/{candidate_id}/facebook-contact", response_model=ProspectSearchCandidateResponse)
async def record_facebook_contact(
    search_id: int,
    candidate_id: int,
    payload: FacebookContactPayload,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ProspectSearchCandidateResponse:
    """Hand over what a browser read on a candidate's Facebook page."""
    user_id = current_user.id
    # The session the auth guard read the user with would keep its pooled connection during the network checks.
    db.commit()
    candidate = await prospect_search_service.record_facebook_contact(
        user_id,
        search_id,
        candidate_id,
        FacebookContactRead(
            is_readable=payload.is_readable,
            emails=payload.emails,
            phone=payload.phone,
            website=payload.website,
        ),
    )
    return _candidate_or_404(candidate)


@router.post("/{search_id}/candidates/{candidate_id}/keep", response_model=ProspectSearchCandidateResponse)
async def keep_candidate(
    search_id: int,
    candidate_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ProspectSearchCandidateResponse:
    """Accept a candidate: it becomes a prospect."""
    try:
        candidate = await prospect_search_service.keep_candidate(db, current_user.id, search_id, candidate_id)
    except ProspectSearchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _candidate_or_404(candidate)


@router.post("/{search_id}/candidates/{candidate_id}/reject", response_model=ProspectSearchCandidateResponse)
async def reject_candidate(
    search_id: int,
    candidate_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ProspectSearchCandidateResponse:
    """Discard a candidate by hand: no later search proposes it again."""
    try:
        candidate = prospect_search_service.reject_candidate(db, current_user.id, search_id, candidate_id)
    except ProspectSearchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _candidate_or_404(candidate)


@router.post("/{search_id}/candidates/{candidate_id}/restore", response_model=ProspectSearchCandidateResponse)
async def restore_candidate(
    search_id: int,
    candidate_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> ProspectSearchCandidateResponse:
    """Undo the refusal of a candidate: it waits for a decision again, without becoming a prospect."""
    try:
        candidate = prospect_search_service.restore_candidate(db, current_user.id, search_id, candidate_id)
    except ProspectSearchError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _candidate_or_404(candidate)
