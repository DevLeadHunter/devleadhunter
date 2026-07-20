"""
Email templates routes for managing email templates.
"""
from typing import List
import json
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from core.database import get_db
from models.user import User
from models.email_account import EmailAccount
from models.email_template import EmailTemplate
from schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplateUpdate,
    EmailTemplateResponse,
    EmailTemplatePreviewRequest,
    EmailTemplatePreviewResponse
)
from services.auth_service import get_current_user

router = APIRouter(prefix="/email-templates", tags=["email-templates"])


def extract_variables(text: str) -> List[str]:
    """
    Extract variable names from template text.
    Variables are in the format {variable_name}.
    """
    pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
    matches = re.findall(pattern, text)
    return list(set(matches))  # Remove duplicates


def replace_variables(text: str, variables: dict) -> str:
    """
    Replace variables in text with their values.
    """
    for key, value in variables.items():
        text = text.replace(f"{{{key}}}", str(value))
    return text


@router.get("", response_model=List[EmailTemplateResponse])
async def get_email_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all email templates for the current user.
    """
    stmt = select(EmailTemplate).where(
        EmailTemplate.user_id == current_user.id
    ).order_by(EmailTemplate.sort_order.desc(), EmailTemplate.created_at.desc())
    
    result = db.execute(stmt)
    templates = result.scalars().all()
    
    # Convert variables JSON string to list
    response_templates = []
    for template in templates:
        template_dict = {
            "id": template.id,
            "user_id": template.user_id,
            "email_account_id": template.email_account_id,
            "name": template.name,
            "subject": template.subject,
            "body_html": template.body_html,
            "body_text": template.body_text,
            "variables": json.loads(template.variables) if template.variables else [],
            "signature_id": template.signature_id,
            "is_active": template.is_active,
            "created_at": template.created_at,
            "updated_at": template.updated_at
        }
        response_templates.append(EmailTemplateResponse(**template_dict))
    
    return response_templates


@router.get("/{template_id}", response_model=EmailTemplateResponse)
async def get_email_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific email template by ID.
    """
    stmt = select(EmailTemplate).where(
        EmailTemplate.id == template_id,
        EmailTemplate.user_id == current_user.id
    )
    
    result = db.execute(stmt)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )
    
    return EmailTemplateResponse(
        id=template.id,
        user_id=template.user_id,
        email_account_id=template.email_account_id,
        name=template.name,
        subject=template.subject,
        body_html=template.body_html,
        body_text=template.body_text,
        variables=json.loads(template.variables) if template.variables else [],
        signature_id=template.signature_id,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.post("", response_model=EmailTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_email_template(
    template_data: EmailTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new email template.
    """
    # Verify email account belongs to user if provided
    if template_data.email_account_id:
        stmt = select(EmailAccount).where(
            EmailAccount.id == template_data.email_account_id,
            EmailAccount.user_id == current_user.id
        )
        result = db.execute(stmt)
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email account not found"
            )
    
    # Extract variables from subject and body
    subject_vars = extract_variables(template_data.subject)
    body_vars = extract_variables(template_data.body_html)
    all_variables = list(set(subject_vars + body_vars))
    
    # Use provided variables or auto-detected ones
    variables = template_data.variables if template_data.variables else all_variables
    
    # Create new template
    new_template = EmailTemplate(
        user_id=current_user.id,
        email_account_id=template_data.email_account_id,
        name=template_data.name,
        subject=template_data.subject,
        body_html=template_data.body_html,
        body_text=template_data.body_text,
        variables=json.dumps(variables),
        signature_id=template_data.signature_id,
    )
    
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    
    return EmailTemplateResponse(
        id=new_template.id,
        user_id=new_template.user_id,
        email_account_id=new_template.email_account_id,
        name=new_template.name,
        subject=new_template.subject,
        body_html=new_template.body_html,
        body_text=new_template.body_text,
        variables=variables,
        signature_id=new_template.signature_id,
        is_active=new_template.is_active,
        created_at=new_template.created_at,
        updated_at=new_template.updated_at
    )


@router.patch("/{template_id}", response_model=EmailTemplateResponse)
async def update_email_template(
    template_id: int,
    template_data: EmailTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update an email template.
    """
    # Get template
    stmt = select(EmailTemplate).where(
        EmailTemplate.id == template_id,
        EmailTemplate.user_id == current_user.id
    )
    result = db.execute(stmt)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )
    
    # Verify email account if provided
    if template_data.email_account_id is not None:
        stmt = select(EmailAccount).where(
            EmailAccount.id == template_data.email_account_id,
            EmailAccount.user_id == current_user.id
        )
        result = db.execute(stmt)
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email account not found"
            )
        template.email_account_id = template_data.email_account_id
    
    # Update fields
    if template_data.name is not None:
        template.name = template_data.name
    if template_data.subject is not None:
        template.subject = template_data.subject
    if template_data.body_html is not None:
        template.body_html = template_data.body_html
    if template_data.body_text is not None:
        template.body_text = template_data.body_text
    if template_data.is_active is not None:
        template.is_active = template_data.is_active
    # Signature: apply only when the field is explicitly present in the payload.
    # ``null`` means "detach" (switch off), so an ``is not None`` guard would be
    # wrong; ``model_fields_set`` distinguishes omitted from explicit null and
    # keeps a partial update (e.g. toggling is_active) from wiping the signature.
    if "signature_id" in template_data.model_fields_set:
        template.signature_id = template_data.signature_id

    # Update variables if provided, or auto-detect
    if template_data.variables is not None:
        template.variables = json.dumps(template_data.variables)
    else:
        # Auto-detect variables from updated subject/body
        subject_vars = extract_variables(template.subject)
        body_vars = extract_variables(template.body_html)
        all_variables = list(set(subject_vars + body_vars))
        template.variables = json.dumps(all_variables)
    
    db.commit()
    db.refresh(template)
    
    return EmailTemplateResponse(
        id=template.id,
        user_id=template.user_id,
        email_account_id=template.email_account_id,
        name=template.name,
        subject=template.subject,
        body_html=template.body_html,
        body_text=template.body_text,
        variables=json.loads(template.variables) if template.variables else [],
        signature_id=template.signature_id,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_template(
    template_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an email template.
    """
    # Get template
    stmt = select(EmailTemplate).where(
        EmailTemplate.id == template_id,
        EmailTemplate.user_id == current_user.id
    )
    result = db.execute(stmt)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )
    
    db.delete(template)
    db.commit()
    
    return None


@router.post("/preview", response_model=EmailTemplatePreviewResponse)
async def preview_email_template(
    preview_data: EmailTemplatePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview an email template with variable substitution.
    """
    # Get template
    stmt = select(EmailTemplate).where(
        EmailTemplate.id == preview_data.template_id,
        EmailTemplate.user_id == current_user.id
    )
    result = db.execute(stmt)
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email template not found"
        )
    
    # Replace variables in subject and body
    preview_subject = replace_variables(template.subject, preview_data.variables)
    preview_body_html = replace_variables(template.body_html, preview_data.variables)

    # Append the attached signature (same rendering as the real send paths).
    from services.email_signatures import render_signature_html

    preview_body_html += render_signature_html(
        db,
        template.signature_id,
        preview_data.variables,
        user_id=current_user.id,
    )

    return EmailTemplatePreviewResponse(
        subject=preview_subject,
        body_html=preview_body_html
    )

