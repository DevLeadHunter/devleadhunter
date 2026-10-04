"""
Email template library — list, fork-on-edit, and per-user hide semantics.
"""

from __future__ import annotations

import json
import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from enums.user_role import is_super_admin
from models.email_template import EmailTemplate
from models.email_template_library_hide import EmailTemplateLibraryHide
from models.user import User
from schemas.email_template import (
    EmailTemplateCreate,
    EmailTemplatePreviewResponse,
    EmailTemplateResponse,
    EmailTemplateUpdate,
)
from services.email_layout import EmailLayout
from services.email_signatures import preferred_signature_id, render_signature_html
from services.email_variables import EmailVariables
from services.unsubscribe_service import unsubscribe_service

_VARIABLE_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
_PREVIEW_UNSUBSCRIBE_LINK = "#"


def extract_variables(text: str) -> list[str]:
    """Return unique ``{variable}`` names found in *text*."""
    return list(set(_VARIABLE_PATTERN.findall(text)))


def _is_library_owner(template: EmailTemplate, user: User) -> bool:
    """True when *user* owns and may edit the canonical library row in place."""
    return template.is_library and template.user_id == user.id and is_super_admin(user.role)


def _hidden_library_ids(db: Session, user_id: int) -> set[int]:
    rows = db.execute(
        select(EmailTemplateLibraryHide.library_template_id).where(EmailTemplateLibraryHide.user_id == user_id)
    ).all()
    return {int(row[0]) for row in rows}


def _forks_by_library_id(db: Session, user_id: int) -> dict[int, EmailTemplate]:
    rows = db.execute(
        select(EmailTemplate).where(
            EmailTemplate.user_id == user_id,
            EmailTemplate.library_source_id.isnot(None),
        )
    ).scalars()
    return {int(t.library_source_id): t for t in rows if t.library_source_id is not None}


def _get_fork(db: Session, user_id: int, library_template_id: int) -> EmailTemplate | None:
    return db.execute(
        select(EmailTemplate).where(
            EmailTemplate.user_id == user_id,
            EmailTemplate.library_source_id == library_template_id,
        )
    ).scalar_one_or_none()


def _hide_library_template(db: Session, user_id: int, library_template_id: int) -> None:
    exists = db.execute(
        select(EmailTemplateLibraryHide).where(
            EmailTemplateLibraryHide.user_id == user_id,
            EmailTemplateLibraryHide.library_template_id == library_template_id,
        )
    ).scalar_one_or_none()
    if exists is None:
        db.add(EmailTemplateLibraryHide(user_id=user_id, library_template_id=library_template_id))


def _clone_template(
    source: EmailTemplate,
    *,
    user_id: int,
    signature_id: int | None,
    library_source_id: int | None = None,
) -> EmailTemplate:
    """Duplicate *source* as a personal row for *user_id*, signed with *signature_id*.

    A signature belongs to its owner, so the copy never keeps the one of *source*.
    """
    return EmailTemplate(
        user_id=user_id,
        email_account_id=None,
        signature_id=signature_id,
        name=source.name,
        subject=source.subject,
        body_html=source.body_html,
        body_text=source.body_text,
        variables=source.variables,
        is_active=source.is_active,
        category=source.category,
        layout=source.layout,
        sort_order=source.sort_order,
        is_library=False,
        library_source_id=library_source_id,
    )


def _apply_update(template: EmailTemplate, data: EmailTemplateUpdate) -> None:
    """Apply a partial update payload onto an ORM row."""
    if data.email_account_id is not None:
        template.email_account_id = data.email_account_id
    if data.name is not None:
        template.name = data.name
    if data.subject is not None:
        template.subject = data.subject
    if data.body_html is not None:
        template.body_html = data.body_html
    if data.body_text is not None:
        template.body_text = data.body_text
    if data.is_active is not None:
        template.is_active = data.is_active
    if data.category is not None:
        template.category = data.category.value
    if data.layout is not None:
        template.layout = data.layout.value
    if "signature_id" in data.model_fields_set:
        template.signature_id = data.signature_id

    if data.variables is not None:
        template.variables = json.dumps(data.variables)
    elif data.subject is not None or data.body_html is not None:
        subject_vars = extract_variables(template.subject)
        body_vars = extract_variables(template.body_html)
        template.variables = json.dumps(list(set(subject_vars + body_vars)))


def to_response(template: EmailTemplate) -> EmailTemplateResponse:
    """Serialize an ORM template for the API."""
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
        category=template.category,
        layout=template.layout,
        sort_order=template.sort_order,
        is_library=template.is_library,
        is_fork=template.library_source_id is not None,
        library_source_id=template.library_source_id,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def render_preview(
    db: Session,
    user: User,
    *,
    subject: str,
    body_html: str,
    signature_id: int | None,
    layout: str,
    sample_values: dict[str, str],
) -> EmailTemplatePreviewResponse:
    """
    Render a template as it would leave: variables, signature, then the layout the template chose.

    Args:
        db: Active database session.
        user: The user previewing, whose signature and accent colour apply.
        subject: Subject still holding its ``{variables}``.
        body_html: Body still holding its ``{variables}``.
        signature_id: Signature attached to the template, or None.
        layout: The template's ``EmailTemplateLayout`` value.
        sample_values: Example value of each variable, as the app sends them.

    Returns:
        The rendered subject and body.
    """
    variables: dict[str, str] = EmailVariables.preview_values(sample_values)
    for key, value in variables.items():
        subject = subject.replace(f"{{{key}}}", value)
        body_html = body_html.replace(f"{{{key}}}", value)
    signature_html: str = render_signature_html(db, signature_id, variables, user_id=user.id)
    dressed_html: str = EmailLayout.dress(layout, body_html, signature_html, variables, user.email_accent_color)
    if unsubscribe_service.FOOTER_SLOT in dressed_html:
        dressed_html = unsubscribe_service.add_unsubscribe_footer(dressed_html, _PREVIEW_UNSUBSCRIBE_LINK, sender=user)
    return EmailTemplatePreviewResponse(subject=subject, body_html=dressed_html)


def list_for_user(db: Session, user: User) -> list[EmailTemplate]:
    """
    Build the template list visible to *user*.

    Library templates appear once (fork replaces the library row when present).
    Personal templates created from scratch are appended.
    """
    hidden = _hidden_library_ids(db, user.id)
    forks = _forks_by_library_id(db, user.id)

    library_rows = db.execute(
        select(EmailTemplate)
        .where(EmailTemplate.is_library.is_(True))
        .order_by(EmailTemplate.sort_order.desc(), EmailTemplate.created_at.desc())
    ).scalars()

    personal_rows = db.execute(
        select(EmailTemplate)
        .where(
            EmailTemplate.user_id == user.id,
            EmailTemplate.is_library.is_(False),
            EmailTemplate.library_source_id.is_(None),
        )
        .order_by(EmailTemplate.sort_order.desc(), EmailTemplate.created_at.desc())
    ).scalars()

    merged: list[EmailTemplate] = []
    for library in library_rows:
        if library.id in hidden:
            continue
        merged.append(forks.get(library.id, library))

    merged.extend(personal_rows)
    return merged


def get_for_user(db: Session, template_id: int, user: User) -> EmailTemplate | None:
    """Resolve a template id the way *user* would see it in their list."""
    template = db.get(EmailTemplate, template_id)
    if template is None:
        return None

    if template.user_id == user.id and not template.is_library:
        return template

    if template.is_library:
        if template.id in _hidden_library_ids(db, user.id):
            return None
        return _get_fork(db, user.id, template.id) or template

    return None


def create_template(db: Session, user: User, data: EmailTemplateCreate) -> EmailTemplate:
    """
    Create a personal template or a new library entry (super-admin only).

    A payload that does not name a signature gets the user's preferred one: every email leaves
    signed unless the user explicitly sends ``signature_id: null``.
    """
    share = bool(data.share_with_all)
    if share and not is_super_admin(user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only super-admins can publish library templates"
        )

    subject_vars = extract_variables(data.subject)
    body_vars = extract_variables(data.body_html)
    variables = data.variables if data.variables else list(set(subject_vars + body_vars))
    signature_id: int | None = (
        data.signature_id if "signature_id" in data.model_fields_set else preferred_signature_id(db, user.id)
    )

    template = EmailTemplate(
        user_id=user.id,
        email_account_id=data.email_account_id,
        name=data.name,
        subject=data.subject,
        body_html=data.body_html,
        body_text=data.body_text,
        variables=json.dumps(variables),
        signature_id=signature_id,
        category=data.category.value,
        layout=data.layout.value,
        is_library=share,
        library_source_id=None,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


def _fork_or_get(db: Session, user: User, library: EmailTemplate) -> EmailTemplate:
    """Return the user's fork of *library*, creating it on first use."""
    existing = _get_fork(db, user.id, library.id)
    if existing is not None:
        return existing
    fork = _clone_template(
        library,
        user_id=user.id,
        signature_id=preferred_signature_id(db, user.id),
        library_source_id=library.id,
    )
    db.add(fork)
    db.flush()
    return fork


def update_template(db: Session, user: User, template_id: int, data: EmailTemplateUpdate) -> EmailTemplate:
    """
    Update a template.

    Library rows are edited in place by their super-admin owner; everyone else
    gets a personal fork so the canonical library stays untouched.
    """
    template = db.get(EmailTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email template not found")

    if template.is_library:
        if _is_library_owner(template, user):
            _apply_update(template, data)
            db.commit()
            db.refresh(template)
            return template
        fork = _fork_or_get(db, user, template)
        _apply_update(fork, data)
        db.commit()
        db.refresh(fork)
        return fork

    if template.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email template not found")

    _apply_update(template, data)
    db.commit()
    db.refresh(template)
    return template


def delete_template(db: Session, user: User, template_id: int) -> None:
    """
    Delete a template for *user*.

    Personal rows are removed. Library rows are hidden per user; super-admins
    delete the canonical library globally.
    """
    template = db.get(EmailTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email template not found")

    if template.is_library:
        if _is_library_owner(template, user):
            db.delete(template)
            db.commit()
            return
        fork = _get_fork(db, user.id, template.id)
        if fork is not None:
            db.delete(fork)
        _hide_library_template(db, user.id, template.id)
        db.commit()
        return

    if template.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email template not found")

    db.delete(template)
    db.commit()
