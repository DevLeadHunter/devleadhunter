"""
Email signature routes — CRUD for a user's reusable email signatures.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from models.email_signature import EmailSignature
from models.email_template import EmailTemplate
from schemas.email_signature import (
    EmailSignatureCreate,
    EmailSignatureUpdate,
    EmailSignatureResponse,
)
from services.auth_service import get_current_user

router = APIRouter(prefix="/email-signatures", tags=["email-signatures"])


def _clear_other_defaults(db: Session, user_id: int, keep_id: int | None = None) -> None:
    """Unset ``is_default`` on every other signature of the user.

    Args:
        db: Database session.
        user_id: Owner whose signatures are updated.
        keep_id: Signature id to leave untouched (the new default).
    """
    stmt = update(EmailSignature).where(EmailSignature.user_id == user_id)
    if keep_id is not None:
        stmt = stmt.where(EmailSignature.id != keep_id)
    db.execute(stmt.values(is_default=False))


@router.get("", response_model=List[EmailSignatureResponse])
async def get_email_signatures(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[EmailSignature]:
    """Return every signature of the current user (default first, then newest)."""
    stmt = (
        select(EmailSignature)
        .where(EmailSignature.user_id == current_user.id)
        .order_by(EmailSignature.is_default.desc(), EmailSignature.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=EmailSignatureResponse, status_code=status.HTTP_201_CREATED)
async def create_email_signature(
    payload: EmailSignatureCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailSignature:
    """Create a signature. The first signature of a user becomes the default."""
    existing_count: int = len(
        db.execute(
            select(EmailSignature.id).where(EmailSignature.user_id == current_user.id)
        ).scalars().all()
    )
    is_default: bool = payload.is_default or existing_count == 0

    signature = EmailSignature(
        user_id=current_user.id,
        name=payload.name,
        content_html=payload.content_html,
        is_default=is_default,
    )
    db.add(signature)
    db.flush()  # assign id before clearing other defaults

    if is_default:
        _clear_other_defaults(db, current_user.id, keep_id=signature.id)

    db.commit()
    db.refresh(signature)
    return signature


@router.patch("/{signature_id}", response_model=EmailSignatureResponse)
async def update_email_signature(
    signature_id: int,
    payload: EmailSignatureUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailSignature:
    """Update a signature (name / content / default flag)."""
    signature: EmailSignature | None = db.execute(
        select(EmailSignature).where(
            EmailSignature.id == signature_id,
            EmailSignature.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if signature is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signature not found")

    if payload.name is not None:
        signature.name = payload.name
    if payload.content_html is not None:
        signature.content_html = payload.content_html
    if payload.is_default is not None:
        signature.is_default = payload.is_default
        if payload.is_default:
            _clear_other_defaults(db, current_user.id, keep_id=signature.id)

    db.commit()
    db.refresh(signature)
    return signature


@router.delete("/{signature_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_signature(
    signature_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a signature and detach it from any template referencing it."""
    signature: EmailSignature | None = db.execute(
        select(EmailSignature).where(
            EmailSignature.id == signature_id,
            EmailSignature.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if signature is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Signature not found")

    # Detach from templates first (no hard DB FK cascade on existing databases).
    db.execute(
        update(EmailTemplate)
        .where(EmailTemplate.signature_id == signature_id)
        .values(signature_id=None)
    )
    db.delete(signature)
    db.commit()
    return None
