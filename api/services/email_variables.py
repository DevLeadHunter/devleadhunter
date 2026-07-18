"""Shared email personalisation variables for a prospect.

Single source of truth for {salutation} / {prenom} / {nom} / {entreprise}… —
used by the campaign queue (dispatch + preview) and the behaviour follow-up so
every send resolves the SAME trusted contact.

The old behaviour ({prenom} = first word of the COMPANY name → « Bonjour
Plomberie, ») is gone: {prenom}/{nom} come from the decision-maker resolution
stored on the enrichment, and are EMPTY when unknown. {salutation} always
renders a clean greeting (« Bonjour » at worst).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from services.decision_maker import build_greeting

# Personalisation variable keys used in cold-email templates.
VAR_SALUTATION = "salutation"
VAR_FIRST_NAME = "prenom"
VAR_LAST_NAME = "nom"
VAR_COMPANY = "entreprise"
VAR_CITY = "ville"
VAR_EMAIL = "email"
VAR_PHONE = "phone"
VAR_METIER = "metier"
VAR_DEMO_LINK = "lien_demo"
# Prospection video: {lien_video} = URL of the tracked player page,
# {vignette_video} = full clickable thumbnail HTML block (image → player page).
VAR_VIDEO_LINK = "lien_video"
VAR_VIDEO_THUMBNAIL = "vignette_video"


def build_video_thumbnail_html(video_link: str, thumbnail_url: str) -> str:
    """
    Build the email-safe clickable thumbnail block for ``{vignette_video}``.

    Emails cannot embed a playable video — the proven pattern is a
    personalised thumbnail (his site + play button) linking to the player
    page. Inline styles only (email clients strip stylesheets).

    @param video_link - Player page URL (demo host ``/v/{slug}``).
    @param thumbnail_url - Absolute public URL of the personalised JPEG.
    @returns The HTML block, or an empty string when either URL is missing.
    """
    if not video_link or not thumbnail_url:
        return ""
    return (
        f'<p style="margin:16px 0;"><a href="{video_link}" target="_blank">'
        f'<img src="{thumbnail_url}" alt="Votre site en vidéo" width="480" '
        f'style="display:block;width:100%;max-width:480px;border-radius:12px;border:0;" />'
        f"</a></p>"
    )


def resolved_contact(
    db: Session, prospect_id: int
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return the trusted (first, last, gender) for a prospect, or Nones.

    Only names the resolver (or a manual edit) stored on the enrichment are
    returned — the confidence threshold was applied at write time.
    """
    enrichment: Optional[ProspectEnrichment] = db.execute(
        select(ProspectEnrichment).where(ProspectEnrichment.prospect_id == prospect_id)
    ).scalar_one_or_none()
    if enrichment is None:
        return None, None, None
    return enrichment.contact_first_name, enrichment.contact_last_name, enrichment.contact_gender


def build_prospect_variables(
    db: Session,
    prospect: ProspectDB,
    demo_link: str = "",
    video_link: str = "",
    video_thumbnail_url: str = "",
) -> dict[str, str]:
    """Build the full substitution map for a prospect's emails.

    {salutation} is always safe (« Bonjour » / « Bonjour Léo » / « Bonjour
    M. Guillaume ») ; {prenom} and {nom} are empty strings when unknown —
    never a company word. {lien_video}/{vignette_video} are empty when the
    prospect has no generated prospection video (the queue guards prevent
    sending a template that needs them in that case).
    """
    first, last, gender = resolved_contact(db, prospect.id)
    return {
        VAR_SALUTATION: build_greeting(first, last, gender),
        VAR_FIRST_NAME: first or "",
        VAR_LAST_NAME: last or "",
        VAR_COMPANY: prospect.name or "",
        VAR_CITY: prospect.city or "",
        VAR_EMAIL: prospect.email or "",
        VAR_PHONE: prospect.phone or "",
        VAR_METIER: prospect.category or "",
        VAR_DEMO_LINK: demo_link,
        VAR_VIDEO_LINK: video_link,
        VAR_VIDEO_THUMBNAIL: build_video_thumbnail_html(video_link, video_thumbnail_url),
    }
