"""
Organization routes — team workspace with a shared prospect list.

Only prospects are shared across an organization; campaigns, demo sites,
emails and credits stay personal to each member.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_db
from models.organization import Organization, OrganizationMember
from models.user import User
from schemas.organization import (
    CreateOrganizationRequest,
    InviteMemberRequest,
    OrganizationMemberResponse,
    OrganizationResponse,
)
from services.auth_service import require_auth
from services.organization_service import OrganizationError, organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _to_response(db: Session, organization: Organization) -> OrganizationResponse:
    """Build the API response for an organization with resolved member identities."""
    rows = db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == organization.id)
        .order_by(OrganizationMember.created_at.asc())
    ).all()
    members = [
        OrganizationMemberResponse(
            user_id=user.id,
            name=user.name,
            email=user.email,
            role=member.role,
            joined_at=member.created_at,
        )
        for member, user in rows
    ]
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        owner_user_id=organization.owner_user_id,
        created_at=organization.created_at,
        members=members,
    )


def _raise(exc: OrganizationError) -> None:
    """Map a business error to its HTTP status."""
    raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get(
    "/mine",
    response_model=OrganizationResponse | None,
    summary="Get my organization",
    description="Return the caller's organization with members, or null when not in any",
)
async def get_my_organization(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> OrganizationResponse | None:
    """Return the caller's organization (members included), or ``null``."""
    organization = organization_service.get_user_organization(db, current_user.id)
    if organization is None:
        return None
    return _to_response(db, organization)


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organization",
    description="Create a team workspace owned by the caller; their prospects become shared",
)
async def create_organization(
    payload: CreateOrganizationRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> OrganizationResponse:
    """Create the caller's organization (one per user)."""
    try:
        organization = organization_service.create_organization(db, current_user, payload.name)
    except OrganizationError as exc:
        _raise(exc)
    return _to_response(db, organization)


@router.post(
    "/members",
    response_model=OrganizationResponse,
    summary="Invite a member",
    description="Add an existing DevLeadHunter user (by account email) to my organization",
)
async def invite_member(
    payload: InviteMemberRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> OrganizationResponse:
    """Invite an existing user into the caller's organization."""
    try:
        organization_service.invite_member(db, current_user.id, payload.email)
    except OrganizationError as exc:
        _raise(exc)
    organization = organization_service.get_user_organization(db, current_user.id)
    assert organization is not None
    return _to_response(db, organization)


@router.delete(
    "/members/{member_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member / leave",
    description="Owner removes any member; a member removes themselves (leave). Their prospects turn personal again",
)
async def remove_member(
    member_user_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> None:
    """Remove a member from the caller's organization (or leave it)."""
    try:
        organization_service.remove_member(db, current_user.id, member_user_id)
    except OrganizationError as exc:
        _raise(exc)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete my organization",
    description="Owner only — every member's prospects become personal again",
)
async def delete_organization(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> None:
    """Delete the caller's organization (owner only)."""
    try:
        organization_service.delete_organization(db, current_user.id)
    except OrganizationError as exc:
        _raise(exc)
