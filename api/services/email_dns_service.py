"""Sending-domain DNS health — SPF, DKIM, DMARC, MX and blocklist checks.

Pure DNS lookups (dnspython), no external account needed. Results are cached
in memory for a short TTL: DNS records change rarely and the page may be
refreshed often.

Honest limits, surfaced in the payloads:
- DKIM needs a selector; we probe the common ones (Resend, Google, generic).
- Spamhaus public mirrors refuse queries coming from big public resolvers
  (8.8.8.8…), so a blocklist check can come back ``unknown`` — that is not a
  listing.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

import dns.resolver

logger = logging.getLogger(__name__)

# Common DKIM selectors: Resend, Google Workspace, generic ESP defaults.
_DKIM_SELECTORS: tuple[str, ...] = (
    "resend",
    "google",
    "default",
    "selector1",
    "selector2",
    "k1",
    "s1",
    "s2",
    "mail",
    "dkim",
)

# Domain blocklists queried over DNS (domain-based DNSBL).
_DOMAIN_BLOCKLISTS: tuple[str, ...] = ("dbl.spamhaus.org", "multi.surbl.org")

_CACHE_TTL_SECONDS: float = 600.0
_DNS_TIMEOUT_SECONDS: float = 4.0


def _resolver() -> dns.resolver.Resolver:
    """A resolver with tight timeouts (the page must never hang on DNS).

    @returns A configured dnspython resolver.
    """
    resolver = dns.resolver.Resolver()
    resolver.timeout = _DNS_TIMEOUT_SECONDS
    resolver.lifetime = _DNS_TIMEOUT_SECONDS
    return resolver


def _txt_records(name: str) -> list[str]:
    """All TXT strings published at ``name`` (empty on NXDOMAIN/timeouts).

    @param name - DNS name to query.
    @returns Decoded TXT values.
    """
    try:
        answers = _resolver().resolve(name, "TXT")
        records: list[str] = []
        for answer in answers:
            joined = b"".join(part for part in answer.strings).decode("utf-8", errors="replace")
            records.append(joined)
        return records
    except Exception:  # noqa: BLE001 — NXDOMAIN, timeout… all mean "no record"
        return []


class EmailDnsService:
    """DNS authentication + reputation checks for a sending domain."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def check_domain(self, domain: str) -> dict[str, Any]:
        """Run every DNS check for one domain (cached ~10 min).

        @param domain - The sending domain (e.g. ``dibodev.fr``).
        @returns SPF/DKIM/DMARC/MX/blocklist results with ok/warn/danger statuses.
        """
        domain = domain.strip().lower()
        cached = self._cache.get(domain)
        if cached and (time.monotonic() - cached[0]) < _CACHE_TTL_SECONDS:
            return cached[1]

        result = {
            "domain": domain,
            "spf": self._check_spf(domain),
            "dkim": self._check_dkim(domain),
            "dmarc": self._check_dmarc(domain),
            "mx": self._check_mx(domain),
            "blocklists": self._check_blocklists(domain),
        }
        self._cache[domain] = (time.monotonic(), result)
        return result

    # ------------------------------------------------------------------ #
    # Individual checks                                                  #
    # ------------------------------------------------------------------ #

    def _check_spf(self, domain: str) -> dict[str, Any]:
        """SPF record presence + policy strictness.

        @param domain - Sending domain.
        @returns Status, the raw record and advice.
        """
        spf: Optional[str] = next(
            (record for record in _txt_records(domain) if record.lower().startswith("v=spf1")), None
        )
        if spf is None:
            return {
                "status": "danger",
                "record": None,
                "detail": "Aucun enregistrement SPF — les fournisseurs ne peuvent pas vérifier vos envois.",
            }
        lowered = spf.lower()
        if "+all" in lowered:
            return {
                "status": "danger",
                "record": spf,
                "detail": "SPF en « +all » : n'importe qui peut envoyer en votre nom.",
            }
        if "-all" in lowered or "~all" in lowered:
            return {"status": "ok", "record": spf, "detail": "SPF présent avec une politique stricte."}
        return {
            "status": "warn",
            "record": spf,
            "detail": "SPF présent mais sans « ~all »/« -all » final — politique trop permissive.",
        }

    def _check_dkim(self, domain: str) -> dict[str, Any]:
        """Probe common DKIM selectors for a published public key.

        @param domain - Sending domain.
        @returns Status, the selectors found and advice.
        """
        found: list[str] = []
        for selector in _DKIM_SELECTORS:
            records = _txt_records(f"{selector}._domainkey.{domain}")
            if any("v=dkim1" in record.lower() or "k=rsa" in record.lower() for record in records):
                found.append(selector)
        if found:
            return {
                "status": "ok",
                "selectors": found,
                "detail": f"Clé DKIM publiée (sélecteur{'s' if len(found) > 1 else ''} : {', '.join(found)}).",
            }
        return {
            "status": "warn",
            "selectors": [],
            "detail": (
                "Aucune clé DKIM trouvée sur les sélecteurs courants — si vos emails partent bien signés "
                "(Resend le fait), le sélecteur est simplement non standard."
            ),
        }

    def _check_dmarc(self, domain: str) -> dict[str, Any]:
        """DMARC record, policy level and rua reporting address.

        @param domain - Sending domain.
        @returns Status, policy, rua and advice.
        """
        dmarc: Optional[str] = next(
            (record for record in _txt_records(f"_dmarc.{domain}") if record.lower().startswith("v=dmarc1")),
            None,
        )
        if dmarc is None:
            return {
                "status": "danger",
                "record": None,
                "policy": None,
                "rua": None,
                "detail": "Aucun enregistrement DMARC — requis par Gmail/Yahoo depuis 2024 pour les expéditeurs en volume.",
            }

        tags: dict[str, str] = {}
        for part in dmarc.split(";"):
            if "=" in part:
                key, _, value = part.strip().partition("=")
                tags[key.strip().lower()] = value.strip()

        policy = tags.get("p", "").lower() or None
        rua = tags.get("rua") or None

        if policy in ("quarantine", "reject"):
            status = "ok"
            detail = f"DMARC actif en « p={policy} »."
        elif policy == "none":
            status = "warn"
            detail = "DMARC en « p=none » : les rapports arrivent mais rien n'est appliqué — passez à « quarantine »."
        else:
            status = "warn"
            detail = "DMARC présent mais politique illisible."

        if rua is None:
            detail += " Aucune adresse « rua » : vous ne recevez pas les rapports agrégés (gratuits et précieux)."

        return {"status": status, "record": dmarc, "policy": policy, "rua": rua, "detail": detail}

    def _check_mx(self, domain: str) -> dict[str, Any]:
        """MX presence (a domain without MX looks disposable to filters).

        @param domain - Sending domain.
        @returns Status, hosts and advice.
        """
        try:
            answers = _resolver().resolve(domain, "MX")
            hosts = sorted(str(answer.exchange).rstrip(".") for answer in answers)
            return {"status": "ok", "hosts": hosts, "detail": "Le domaine sait recevoir des réponses."}
        except Exception:  # noqa: BLE001
            return {
                "status": "warn",
                "hosts": [],
                "detail": "Aucun MX : les prospects ne peuvent pas vous répondre et les filtres s'en méfient.",
            }

    def _check_blocklists(self, domain: str) -> dict[str, Any]:
        """Query domain DNSBLs (Spamhaus DBL, SURBL).

        @param domain - Sending domain.
        @returns Per-list verdicts (`ok` / `listed` / `unknown`).
        """
        lists: list[dict[str, str]] = []
        overall = "ok"
        for blocklist in _DOMAIN_BLOCKLISTS:
            query = f"{domain}.{blocklist}"
            try:
                answers = _resolver().resolve(query, "A")
                codes = [str(answer) for answer in answers]
                # Spamhaus signals bad *queries* (public resolver, quota) via 127.255.255.x.
                if any(code.startswith("127.255.255.") for code in codes):
                    lists.append({"list": blocklist, "status": "unknown"})
                    continue
                lists.append({"list": blocklist, "status": "listed"})
                overall = "danger"
            except dns.resolver.NXDOMAIN:
                lists.append({"list": blocklist, "status": "ok"})
            except Exception:  # noqa: BLE001 — timeout/refused → unknown, not listed
                lists.append({"list": blocklist, "status": "unknown"})
        detail = (
            "Domaine absent des blocklists interrogées."
            if overall == "ok"
            else "Domaine LISTÉ sur au moins une blocklist — délivrabilité fortement impactée."
        )
        if any(item["status"] == "unknown" for item in lists):
            detail += " (Certaines listes n'ont pas répondu — un statut « inconnu » n'est pas un listage.)"
        return {"status": overall, "lists": lists, "detail": detail}


email_dns_service = EmailDnsService()
