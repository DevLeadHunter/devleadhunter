"""Sending-domain DNS health — SPF, DKIM, DMARC, MX and blocklist checks.

Pure DNS lookups (dnspython), no external account needed. Results are cached
in memory for a short TTL: DNS records change rarely and the page may be
refreshed often.

Honest limits, surfaced in the payloads:
- DKIM needs a selector; we probe the common ones (Resend, Google, generic).
- Spamhaus public mirrors refuse queries coming from big public resolvers
  (8.8.8.8…), so a blocklist check can come back ``unknown`` — that is not a
  listing.
- The organizational domain of a sending subdomain is approximated by walking
  up to the last two labels (correct for ``mail.dibodev.fr``, imprecise for
  multi-label suffixes like ``.co.uk``).
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

# Shortest domain we consider organizational when walking up for an inherited
# DMARC record (``mail.dibodev.fr`` → ``dibodev.fr``).
_MIN_ORGANIZATIONAL_LABELS: int = 2


# Overrides the system resolver when set. A local/ISP resolver caches negative
# answers, so a freshly published record can look missing for hours — a false
# alarm right when a zone has just been edited.
_NAMESERVERS: Optional[list[str]] = None


def use_nameservers(nameservers: Optional[list[str]]) -> None:
    """Force every lookup through *nameservers* (``None`` restores the system ones).

    Blocklist queries are the exception to prefer the system resolver: Spamhaus
    mirrors refuse queries coming from large public resolvers.

    @param nameservers - Resolver IPs, or ``None``.
    """
    global _NAMESERVERS
    _NAMESERVERS = nameservers


def _resolver() -> dns.resolver.Resolver:
    """A resolver with tight timeouts (the page must never hang on DNS).

    @returns A configured dnspython resolver.
    """
    resolver = dns.resolver.Resolver()
    if _NAMESERVERS:
        resolver.nameservers = _NAMESERVERS
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


def _parent_domains(name: str) -> list[str]:
    """Ancestors of *name*, closest first, down to the organizational domain.

    @param name - A domain, possibly a sending subdomain.
    @returns Parent domains (empty when *name* is already organizational).
    """
    labels = name.split(".")
    return [
        ".".join(labels[index:])
        for index in range(1, len(labels) - _MIN_ORGANIZATIONAL_LABELS + 1)
    ]


def _is_dkim_key(record: str) -> bool:
    """Whether a TXT record published under ``_domainkey`` holds a public key.

    ``v=`` is only RECOMMENDED by RFC 6376, and some providers omit it: Resend
    publishes a bare ``p=…``. Keying the detection on ``v=DKIM1`` alone would
    silently miss the very selector the campaigns are signed with.

    @param record - Raw TXT value.
    @returns ``True`` when the record carries a DKIM public key.
    """
    normalized = record.lower().replace(" ", "")
    return "v=dkim1" in normalized or "k=rsa" in normalized or normalized.startswith("p=")


def _dmarc_record(name: str) -> Optional[str]:
    """The DMARC TXT record published at ``_dmarc.<name>``, if any.

    @param name - Domain to look up.
    @returns The raw record, or ``None``.
    """
    return next(
        (record for record in _txt_records(f"_dmarc.{name}") if record.lower().startswith("v=dmarc1")),
        None,
    )


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
            if any(_is_dkim_key(record) for record in records):
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
        """DMARC record, *effective* policy level and rua reporting address.

        A sending subdomain rarely publishes its own record: it inherits the
        organizational domain's, and the policy that actually applies to it is
        then ``sp=`` (which defaults to ``p=``), not ``p=``. Reading ``p=``
        alone hides the classic trap of a parent in ``p=quarantine;sp=none``
        whose subdomain is in fact enforced by nothing.

        @param domain - Sending domain.
        @returns Status, effective policy, inheritance origin, rua and advice.
        """
        dmarc: Optional[str] = _dmarc_record(domain)
        inherited_from: Optional[str] = None
        if dmarc is None:
            for parent in _parent_domains(domain):
                dmarc = _dmarc_record(parent)
                if dmarc is not None:
                    inherited_from = parent
                    break

        if dmarc is None:
            return {
                "status": "danger",
                "record": None,
                "policy": None,
                "subdomain_policy": None,
                "inherited_from": None,
                "rua": None,
                "detail": "Aucun enregistrement DMARC — requis par Gmail/Yahoo depuis 2024 pour les expéditeurs en volume.",
            }

        tags: dict[str, str] = {}
        for part in dmarc.split(";"):
            if "=" in part:
                key, _, value = part.strip().partition("=")
                tags[key.strip().lower()] = value.strip()

        declared_policy = tags.get("p", "").lower() or None
        subdomain_policy = tags.get("sp", "").lower() or None
        rua = tags.get("rua") or None
        # RFC 7489: subdomains follow ``sp`` when it is set, otherwise ``p``.
        policy = (subdomain_policy or declared_policy) if inherited_from else declared_policy
        tag_name = "sp" if inherited_from else "p"

        if policy in ("quarantine", "reject"):
            status = "ok"
            detail = f"DMARC actif en « {tag_name}={policy} »."
        elif policy == "none":
            status = "warn"
            detail = (
                f"DMARC en « {tag_name}=none » : les rapports arrivent mais rien n'est appliqué "
                "— passez à « quarantine »."
            )
        else:
            status = "warn"
            detail = "DMARC présent mais politique illisible."

        if inherited_from:
            detail += (
                f" Ce sous-domaine n'a pas son propre enregistrement : il hérite de {inherited_from}, "
                f"donc c'est « sp= » qui s'applique à vos envois, pas « p= »."
            )

        if rua is None:
            detail += " Aucune adresse « rua » : vous ne recevez pas les rapports agrégés (gratuits et précieux)."

        return {
            "status": status,
            "record": dmarc,
            "policy": policy,
            "subdomain_policy": subdomain_policy,
            "inherited_from": inherited_from,
            "rua": rua,
            "detail": detail,
        }

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
            pass
        # No MX: RFC 5321 falls back to the A record, so replies may still be
        # delivered — but only if that host accepts mail for this domain.
        try:
            _resolver().resolve(domain, "A")
            return {
                "status": "warn",
                "hosts": [],
                "detail": (
                    "Aucun MX : les réponses retombent sur l'enregistrement A du domaine. "
                    "Vérifiez qu'une réponse vous parvient vraiment, sinon vous perdrez des leads en silence."
                ),
            }
        except Exception:  # noqa: BLE001
            return {
                "status": "danger",
                "hosts": [],
                "detail": "Ni MX ni A : les prospects ne peuvent pas vous répondre et les filtres s'en méfient.",
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
