"""
Real SPF / DKIM DNS lookups for custom sending domains (provider-agnostic).

Replaces the old Mailjet placeholder that always returned "not verified" with fake
Mailjet-branded instructions. Uses dnspython to actually query the domain's DNS.
Sending goes through Resend, so the guidance points to the provider's own domain setup.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import dns.resolver

logger = logging.getLogger(__name__)

# DKIM selectors to probe, covering the common providers (Resend/AWS SES, Google, generic).
_DKIM_SELECTORS: tuple[str, ...] = (
    "resend",
    "resend2",
    "google",
    "default",
    "s1",
    "s2",
    "k1",
    "mail",
    "dkim",
    "selector1",
    "selector2",
)


def _txt_records(name: str) -> list[str]:
    """Return the TXT records at ``name`` (empty list on any DNS failure)."""
    try:
        answers = dns.resolver.resolve(name, "TXT", lifetime=5.0)
    except Exception:  # noqa: BLE001 — any resolver error → treat as "no record"
        return []
    records: list[str] = []
    for answer in answers:
        strings = getattr(answer, "strings", None)
        if strings:
            records.append(
                "".join(s.decode() if isinstance(s, bytes) else str(s) for s in strings)
            )
        else:
            records.append(str(answer).strip('"'))
    return records


def _lookup(domain: str) -> dict[str, Any]:
    """Blocking DNS lookups for SPF + DKIM presence (run off the event loop)."""
    normalized = domain.strip().lower().lstrip("@")
    spf_records = [txt for txt in _txt_records(normalized) if txt.lower().startswith("v=spf1")]
    spf_verified = bool(spf_records)

    dkim_verified = False
    for selector in _DKIM_SELECTORS:
        records = _txt_records(f"{selector}._domainkey.{normalized}")
        if any(("v=dkim1" in r.lower()) or ("p=" in r.lower()) for r in records):
            dkim_verified = True
            break

    return {
        "spf_verified": spf_verified,
        "dkim_verified": dkim_verified,
        "spf_record": spf_records[0] if spf_records else None,
        "dkim_instructions": (
            "Ajoutez les enregistrements SPF et DKIM de votre fournisseur d'envoi "
            "(dans Resend : onglet Domains → votre domaine → enregistrements DNS à copier) "
            "dans la zone DNS de votre domaine, puis relancez la vérification."
        ),
    }


async def verify_domain_dns(domain: str) -> dict[str, Any]:
    """Verify a domain's SPF + DKIM records with real DNS lookups.

    @param domain - The sending domain (e.g. ``exemple.fr``).
    @returns ``{spf_verified, dkim_verified, spf_record, dkim_instructions}``.
    """
    if not domain or not domain.strip():
        return {"spf_verified": False, "dkim_verified": False, "spf_record": None, "dkim_instructions": ""}
    return await asyncio.to_thread(_lookup, domain)
