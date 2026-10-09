"""Signature rendering shared by every send path.

A template (or a manual send) may reference an :class:`EmailSignature`. This
helper resolves it to an HTML block appended to the already-rendered body, so
the switch "Inclure une signature" behaves identically for campaigns,
follow-ups, the preview and the one-off composer.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.email_signature import EmailSignature
from services.country_profiles import DEFAULT_COUNTRY_CODE, CountryProfiles
from services.regional_lexicon import RegionalLexicon
from services.sms.phone_normalizer import format_phone_for_reader, to_e164

_PHONE_LINK = re.compile(r'(<a\b[^>]*\bhref="tel:([^"]+)"[^>]*>)(.*?)(</a>)', re.IGNORECASE | re.DOTALL)
_TEXT_AFTER_LAST_TAG = re.compile(r"[^<>]*$")
_DIALLED_NUMBER = re.compile(r"^\+?[\d\s.()\-]*\d$")


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
        html = _phone_links_for_reader(html, variables.get(RegionalLexicon.COUNTRY_KEY))

    return f'<div style="margin-top:16px;">{html}</div>'


def _phone_links_for_reader(html: str, reader_country: str | None) -> str:
    """Write the number shown by each phone link the way a prospect abroad dials it (« +33 6 12 34 56 78 »).

    The link already calls from anywhere; only its text, dialled by hand from Switzerland or Québec, failed.
    A French reader keeps the number as the sender wrote it, and a link whose text is not a number is left alone.

    Args:
        html: The signature HTML.
        reader_country: ISO code of the prospect's country (``None`` reads as France).

    Returns:
        The HTML with the number of each phone link written for the reader.
    """
    if CountryProfiles.get(reader_country).code == DEFAULT_COUNTRY_CODE:
        return html

    def rewrite(link: re.Match[str]) -> str:
        opening, number, inner, closing = link.groups()
        shown: str = _TEXT_AFTER_LAST_TAG.search(inner).group(0)
        shown_number: str = shown.strip()
        if not _DIALLED_NUMBER.match(shown_number.replace("&nbsp;", " ")) or to_e164(number) is None:
            return link.group(0)
        readable: str = format_phone_for_reader(
            number, number_country=DEFAULT_COUNTRY_CODE, reader_country=reader_country
        )
        if "&nbsp;" in shown_number:
            readable = readable.replace(" ", "&nbsp;")
        return f"{opening}{inner[: len(inner) - len(shown)]}{shown.replace(shown_number, readable)}{closing}"

    return _PHONE_LINK.sub(rewrite, html)
