"""Audit the authentication of a sending domain from the command line.

Same checks as the « Santé email » page (SPF, DKIM, DMARC with subdomain
inheritance, MX, blocklists), runnable without starting the API — handy right
after touching a DNS zone.

Usage::

    python scripts/check_email_dns.py                       # mail.dibodev.fr + dibodev.fr
    python scripts/check_email_dns.py example.fr mail.example.fr
    python scripts/check_email_dns.py --system-resolver     # ignore the public resolver

By default the lookups go through a public resolver: right after editing a zone,
a local/ISP resolver still serves the cached "no such record" answer and every
fresh record looks missing. Blocklist verdicts may come back ``unknown`` in that
mode (Spamhaus refuses queries from large public resolvers) — that is not a
listing.

Exit code is 1 as soon as one check is in ``danger``, so it can gate a script.
"""
from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.email_dns_service import email_dns_service, use_nameservers  # noqa: E402

_DEFAULT_DOMAINS: tuple[str, ...] = ("mail.dibodev.fr", "dibodev.fr")

# Cloudflare then Google: neither caches this zone's negative answers the way a
# box/ISP resolver does.
_PUBLIC_NAMESERVERS: list[str] = ["1.1.1.1", "8.8.8.8"]

_ICONS: dict[str, str] = {"ok": "[OK]  ", "warn": "[WARN]", "danger": "[FAIL]"}

_LABELS: tuple[tuple[str, str], ...] = (
    ("spf", "SPF"),
    ("dkim", "DKIM"),
    ("dmarc", "DMARC"),
    ("mx", "MX"),
    ("blocklists", "Blocklists"),
)


def _print_check(label: str, check: dict[str, Any]) -> str:
    """Print one check and return its status.

    @param label - Human-readable check name.
    @param check - Payload from :class:`EmailDnsService`.
    @returns The check status (``ok`` | ``warn`` | ``danger``).
    """
    status: str = str(check.get("status", "warn"))
    print(f"  {_ICONS.get(status, '[?]   ')} {label:<11} {check.get('detail', '')}")
    record = check.get("record")
    if record:
        print(f"           {record}")
    return status


def main(domains: list[str]) -> int:
    """Audit every domain and report the worst status found.

    @param domains - Domains to check.
    @returns Process exit code (1 when at least one check failed).
    """
    failed: bool = False
    for domain in domains:
        print(f"\n=== {domain} ===")
        result = email_dns_service.check_domain(domain)
        for key, label in _LABELS:
            if _print_check(label, result[key]) == "danger":
                failed = True
    print()
    return 1 if failed else 0


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if "--system-resolver" in arguments:
        arguments.remove("--system-resolver")
    else:
        use_nameservers(_PUBLIC_NAMESERVERS)
    raise SystemExit(main(arguments or list(_DEFAULT_DOMAINS)))
