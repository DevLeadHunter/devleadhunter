"""Signature rendering shared by every send path.

A template (or a manual send) may reference an :class:`EmailSignature`. This
helper resolves it to an HTML block appended to the already-rendered body, so
the switch "Inclure une signature" behaves identically for campaigns,
follow-ups, the preview and the one-off composer.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.email_signature import EmailSignature


def get_default_signature(db: Session, user_id: int) -> EmailSignature | None:
    """Return the user's default signature, if any."""
    return db.execute(
        select(EmailSignature).where(EmailSignature.user_id == user_id, EmailSignature.is_default.is_(True)).limit(1)
    ).scalar_one_or_none()


def preferred_signature_id(db: Session, user_id: int) -> int | None:
    """Return the signature a new template carries: the user's default one, else their first one.

    Args:
        db: Database session.
        user_id: Owner of the signatures.

    Returns:
        The signature id, or None when the user has no signature.
    """
    return db.execute(
        select(EmailSignature.id)
        .where(EmailSignature.user_id == user_id)
        .order_by(EmailSignature.is_default.desc(), EmailSignature.id)
        .limit(1)
    ).scalar_one_or_none()


def render_default_signature_html(db: Session, user_id: int, variables: dict[str, str] | None = None) -> str:
    """Append block for the user's default signature, or empty string."""
    signature = get_default_signature(db, user_id)
    if signature is None:
        return ""
    return render_signature_html(db, signature.id, variables=variables, user_id=user_id)


def render_signature_html(
    db: Session,
    signature_id: int | None,
    variables: dict[str, str] | None = None,
    user_id: int | None = None,
) -> str:
    """Return the signature HTML block to append to an email body.

    Args:
        db: Database session.
        signature_id: Signature to render (None → no signature).
        variables: Optional substitution map (same keys as the body); a signature rarely uses prospect variables but stays consistent if it does.
        user_id: When provided, guards the lookup to that owner (defense in depth — the id comes from a user-scoped template).

    Returns:
        The HTML block prefixed with a spacing wrapper, or "" when there is no usable signature.
    """
    if not signature_id:
        return ""

    stmt = select(EmailSignature).where(EmailSignature.id == signature_id)
    if user_id is not None:
        stmt = stmt.where(EmailSignature.user_id == user_id)
    signature: EmailSignature | None = db.execute(stmt).scalar_one_or_none()

    if signature is None or not signature.content_html:
        return ""

    html: str = signature.content_html
    if variables:
        for key, value in variables.items():
            html = html.replace(f"{{{key}}}", str(value))

    return f'<div style="margin-top:16px;">{html}</div>'
