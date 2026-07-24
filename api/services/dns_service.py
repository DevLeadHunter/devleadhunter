"""SPF / DKIM lookups for a user's custom sending domain (provider-agnostic)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import dns.resolver

logger = logging.getLogger(__name__)

DNS_TIMEOUT_SECONDS = 5.0

DKIM_SETUP_INSTRUCTIONS = (
    "Ajoutez les enregistrements SPF et DKIM de votre fournisseur d'envoi "
    "(dans Resend : onglet Domains → votre domaine → enregistrements DNS à copier) "
    "dans la zone DNS de votre domaine, puis relancez la vérification."
)


class SendingDomainDnsService:
    """
    Checks that a sending domain actually publishes SPF and DKIM records.

    Sending goes through Resend, so the guidance returned to the dashboard points at the
    provider's own domain setup rather than at any hardcoded record.
    """

    # Selectors covering the common providers (Resend/AWS SES, Google, generic).
    DKIM_SELECTORS: tuple[str, ...] = (
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

    async def verify_domain(self, domain: str) -> dict[str, Any]:
        """
        Verify a domain's SPF and DKIM records with real DNS lookups.

        Args:
            domain: The sending domain, for example `exemple.fr`.

        Returns:
            `{spf_verified, dkim_verified, spf_record, dkim_instructions}`, all falsy when the
            domain is blank.
        """
        if not domain or not domain.strip():
            return {
                "spf_verified": False,
                "dkim_verified": False,
                "spf_record": None,
                "dkim_instructions": "",
            }
        return await asyncio.to_thread(self._lookup, domain)

    def _lookup(self, domain: str) -> dict[str, Any]:
        """
        Run the blocking SPF and DKIM lookups, off the event loop.

        Args:
            domain: The sending domain.

        Returns:
            The verification payload described in `verify_domain`.
        """
        normalized: str = domain.strip().lower().lstrip("@")
        spf_records: list[str] = [txt for txt in self._txt_records(normalized) if txt.lower().startswith("v=spf1")]

        dkim_verified: bool = False
        for selector in self.DKIM_SELECTORS:
            records: list[str] = self._txt_records(f"{selector}._domainkey.{normalized}")
            if any(("v=dkim1" in record.lower()) or ("p=" in record.lower()) for record in records):
                dkim_verified = True
                break

        return {
            "spf_verified": bool(spf_records),
            "dkim_verified": dkim_verified,
            "spf_record": spf_records[0] if spf_records else None,
            "dkim_instructions": DKIM_SETUP_INSTRUCTIONS,
        }

    @staticmethod
    def _txt_records(name: str) -> list[str]:
        """
        Read the TXT records published at a name.

        Args:
            name: Fully qualified DNS name.

        Returns:
            The record strings, empty on any resolver failure — an unreachable name is treated
            exactly like a missing record.
        """
        try:
            answers = dns.resolver.resolve(name, "TXT", lifetime=DNS_TIMEOUT_SECONDS)
        except Exception:
            return []

        records: list[str] = []
        for answer in answers:
            strings = getattr(answer, "strings", None)
            if strings:
                records.append("".join(s.decode() if isinstance(s, bytes) else str(s) for s in strings))
            else:
                records.append(str(answer).strip('"'))
        return records


sending_domain_dns_service = SendingDomainDnsService()
