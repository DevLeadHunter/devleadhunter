"""
Email templates routes for managing email templates.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_db
from models.email_account import EmailAccount
from models.user import User
from schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateDraftPreviewRequest,
    EmailTemplatePreviewRequest,
    EmailTemplatePreviewResponse,
    EmailTemplateResponse,
    EmailTemplateUpdate,
)
from services import email_template_service as template_service
from services.auth_service import get_current_user

router = APIRouter(prefix="/email-templates", tags=["email-templates"])


@router.get("", response_model=list[EmailTemplateResponse])
async def get_email_templates(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List library templates (with per-user forks) and personal templates."""
    templates = template_service.list_for_user(db, current_user)
    return [template_service.to_response(t) for t in templates]


@router.get("/{template_id}", response_model=EmailTemplateResponse)
async def get_email_template(
    template_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get one template visible to the current user."""
    template = template_service.get_for_user(db, template_id, current_user)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email template not found")
    return template_service.to_response(template)


@router.post("", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_email_template(
    template_data: EmailTemplateCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Create a personal template, or a library template when ``share_with_all`` (super-admin)."""
    if template_data.email_account_id:
        account = db.execute(
            select(EmailAccount).where(
                EmailAccount.id == template_data.email_account_id, EmailAccount.user_id == current_user.id
            )
        ).scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email account not found")

    template = template_service.create_template(db, current_user, template_data)
    return template_service.to_response(template)


@router.patch("/{template_id}", response_model=EmailTemplateResponse)
async def update_email_template(
    template_id: int,
    template_data: EmailTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a template — library edits fork for non-owner users."""
    if template_data.email_account_id is not None:
        account = db.execute(
            select(EmailAccount).where(
                EmailAccount.id == template_data.email_account_id, EmailAccount.user_id == current_user.id
            )
        ).scalar_one_or_none()
        if not account:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email account not found")

    template = template_service.update_template(db, current_user, template_id, template_data)
    return template_service.to_response(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_template(
    template_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Remove a personal template or hide a library template for this user."""
    template_service.delete_template(db, current_user, template_id)
    return None


@router.post("/preview", response_model=EmailTemplatePreviewResponse)
async def preview_email_template(
    preview_data: EmailTemplatePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Preview a template with variable substitution."""
    template = template_service.get_for_user(db, preview_data.template_id, current_user)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email template not found")

    return template_service.render_preview(
        db,
        current_user,
        subject=template.subject,
        body_html=template.body_html,
        signature_id=template.signature_id,
        layout=template.layout,
        sample_values=preview_data.variables,
    )


@router.post("/preview-draft", response_model=EmailTemplatePreviewResponse)
async def preview_email_template_draft(
    draft: EmailTemplateDraftPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailTemplatePreviewResponse:
    """Preview a template still being written, as it would leave."""
    return template_service.render_preview(
        db,
        current_user,
        subject=draft.subject,
        body_html=draft.body_html,
        signature_id=draft.signature_id,
        layout=draft.layout.value,
        sample_values=draft.variables,
    )
