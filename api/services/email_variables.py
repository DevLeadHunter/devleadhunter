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
    db: Session, prospect: ProspectDB, demo_link: str = ""
) -> dict[str, str]:
    """Build the full substitution map for a prospect's emails.

    {salutation} is always safe (« Bonjour » / « Bonjour Léo » / « Bonjour
    M. Guillaume ») ; {prenom} and {nom} are empty strings when unknown —
    never a company word.
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
    }
