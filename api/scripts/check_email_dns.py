"""Audit the authentication of a sending domain from the command line.

Same checks as the « Santé email » page (SPF, DKIM, DMARC with subdomain
inheritance, MX, blocklists), runnable without starting the API — handy right
after touching a DNS zone.

Usage::

    python scripts/check_email_dns.py                       # mail.dibodev.fr + dibodev.fr
    python scripts/check_email_dns.py example.fr mail.example.fr

Exit code is 1 as soon as one check is in ``danger``, so it can gate a script.
"""
from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.email_dns_service import email_dns_service  # noqa: E402

_DEFAULT_DOMAINS: tuple[str, ...] = ("mail.dibodev.fr", "dibodev.fr")

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
    raise SystemExit(main(sys.argv[1:] or list(_DEFAULT_DOMAINS)))
