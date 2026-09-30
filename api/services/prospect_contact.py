"""Whether a prospect is reachable by email or SMS-only (demo inbox routing)."""

from __future__ import annotations

from models.prospect_db import ProspectDB
from services.prospect_phones import first_mobile_e164


def prospect_has_email(prospect: ProspectDB | None) -> bool:
    """True when the prospect has a primary email on file."""
    if prospect is None:
        return False
    return bool((prospect.email or "").strip())


def prospect_has_mobile(prospect: ProspectDB | None) -> bool:
    """True when a French/Swiss-style mobile can be resolved for SMS."""
    if prospect is None:
        return False
    return first_mobile_e164(prospect) is not None


def prospect_demo_inbox_channel(prospect: ProspectDB | None) -> str | None:
    """
    Where a demo-banner message should appear in « réponses à traiter ».

    Returns ``email`` when an address exists, ``sms`` when mobile-only, else ``None``.
    """
    if prospect_has_email(prospect):
        return "email"
    if prospect_has_mobile(prospect):
        return "sms"
    return None
