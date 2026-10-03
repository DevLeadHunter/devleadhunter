"""Domain availability via RDAP — each registry's own server when we know it, the rdap.org bootstrap otherwise.

RDAP answers ``404`` when a domain is not registered (available) and ``200`` with the record when
it is taken. A ``404`` is only trusted when it comes from a registry: rdap.org also answers ``404``
for a TLD it has no server for (``.ch``, ``.be``, ``.lu`` are absent from the IANA bootstrap), which
would otherwise declare every such domain « available ». The check is best-effort: any other outcome
(network error, unexpected status, no RDAP server for the TLD) returns ``None`` so the caller never
claims a domain is free without proof.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 6.0
# Registries asked directly: .ch is missing from the IANA bootstrap; .be and .lu run no public RDAP (left unverified).
_REGISTRY_RDAP: dict[str, str] = {
    "fr": "https://rdap.nic.fr/domain/{domain}",
    "ch": "https://rdap.nic.ch/domain/{domain}",
    "ca": "https://rdap.ca.fury.ca/rdap/domain/{domain}",
}
# Everything else goes through the IANA bootstrap redirector, which forwards to the registry when one exists.
_BOOTSTRAP_RDAP = "https://rdap.org/domain/{domain}"
_BOOTSTRAP_HOST = "rdap.org"


def _tld(domain: str) -> str:
    """The extension of a domain, without its dot (``"tacos-maru.fr"`` → ``"fr"``)."""
    return domain.rsplit(".", 1)[-1]


def _rdap_url(domain: str) -> str:
    """The RDAP query URL for a domain (the registry's server when known, the bootstrap redirector otherwise)."""
    return _REGISTRY_RDAP.get(_tld(domain), _BOOTSTRAP_RDAP).format(domain=domain)


async def is_available(domain: str) -> bool | None:
    """Whether a domain is free to register.

    Args:
        domain: A full domain (e.g. ``"tacos-maru.fr"``, ``"tacos-maru.ch"`` or ``"tacos-maru.com"``); case-insensitive.

    Returns:
        ``True`` when available, ``False`` when already registered, ``None`` when the check is
        inconclusive (no dot, network error, no RDAP server for the TLD, or an unexpected status).
    """
    name = (domain or "").strip().lower()
    if "." not in name:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(_rdap_url(name))
    except httpx.HTTPError as exc:
        logger.debug("RDAP availability check inconclusive for %s: %s", name, exc)
        return None
    if response.status_code == 404:
        # A 404 still served by the redirector means « no RDAP server for this TLD », not « free ».
        if httpx.URL(str(response.url)).host == _BOOTSTRAP_HOST:
            logger.debug("RDAP has no registry server for %s — availability not verifiable", name)
            return None
        return True
    if response.status_code == 200:
        return False
    logger.debug("RDAP returned unexpected status %s for %s", response.status_code, name)
    return None


async def availability_map(domains: list[str]) -> dict[str, bool | None]:
    """Resolve availability for several domains in parallel.

    Args:
        domains: Full domains to check.

    Returns:
        A mapping ``domain -> True/False/None`` (see :func:`is_available`).
    """
    unique = list(dict.fromkeys(d.strip().lower() for d in domains if d and "." in d))
    results = await asyncio.gather(*(is_available(domain) for domain in unique))
    return dict(zip(unique, results, strict=True))
