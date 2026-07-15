"""
Resilience helpers for DOM scraping — keep extraction working when a site rotates
its obfuscated CSS classes (Google Maps, Pages Jaunes…).

Three layers, from most to least stable:

  1. **JSON-LD** (schema.org ``LocalBusiness`` / ``Organization``) embedded in the
     page: the most durable anchor — structured data changes far less often than
     rendered class names, and is what search engines consume, so sites keep it stable.
  2. **Regex on visible text** (phones, emails): independent of markup entirely.
  3. **Selector chains**: handled at the call site (try the current selector, then
     known alternates); this module only folds the candidates with ``first_nonempty``.

Nothing here touches the network or a specific backend, so it is fully unit-testable
and shared by BOTH the nodriver path and the BeautifulSoup/HTTP path.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# JS that returns the raw text of every JSON-LD block — run via NodriverDom.evaluate_list.
LD_JSON_JS: str = (
    "Array.from(document.querySelectorAll('script[type=\"application/ld+json\"]'))"
    ".map(s => s.textContent || '')"
)

# schema.org @types we treat as a business record (LocalBusiness has ~100 subtypes;
# we match the base ones + accept anything that carries business-shaped fields).
_BUSINESS_TYPES: frozenset[str] = frozenset(
    t.lower()
    for t in (
        "LocalBusiness", "Organization", "Store", "ProfessionalService",
        "Plumber", "Electrician", "HomeAndConstructionBusiness", "GeneralContractor",
        "AutoRepair", "HVACBusiness", "Locksmith", "RoofingContractor", "Painter",
        "MovingCompany", "Restaurant", "HairSalon", "BeautySalon", "Dentist",
        "MedicalBusiness", "LegalService", "FinancialService", "Corporation",
    )
)

# Loose but conservative French / international phone matcher (kept to plausible
# lengths so we do not grab SIREN numbers or prices).
_PHONE_RE: re.Pattern[str] = re.compile(
    r"(?:(?:\+|00)\d{1,3}[\s.\-]?)?(?:\(?\d\)?[\s.\-]?){9,13}\d"
)
_EMAIL_RE: re.Pattern[str] = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def first_nonempty(*values: Optional[str]) -> Optional[str]:
    """Return the first stripped, non-empty string among ``values`` (else ``None``)."""
    for value in values:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def safe_email(value: Optional[str]) -> Optional[str]:
    """Return ``value`` only if it is a syntactically valid email.

    ``ProspectCreate.email`` is a Pydantic ``EmailStr`` — a malformed value from a
    regex/JSON-LD fallback would raise ``ValidationError`` for the WHOLE prospect.
    This gate keeps a bad email from poisoning an otherwise good record.

    @param value - Candidate email (any source).
    @returns The lower-cased email, or ``None`` when invalid/absent.
    """
    if not value or not isinstance(value, str):
        return None
    candidate = value.strip().strip("<>").removeprefix("mailto:").strip()
    match = _EMAIL_RE.fullmatch(candidate)
    return candidate.lower() if match else None


def find_phone(text: Optional[str]) -> Optional[str]:
    """Extract the first plausible phone number from free text (markup-independent).

    @param text - Any text that may contain a phone number.
    @returns The matched phone (whitespace-normalised), or ``None``.
    """
    if not text or not isinstance(text, str):
        return None
    match = _PHONE_RE.search(text)
    if not match:
        return None
    phone = re.sub(r"\s+", " ", match.group(0)).strip()
    # Reject if it does not carry enough digits to be a real number.
    return phone if len(re.sub(r"\D", "", phone)) >= 9 else None


def _iter_ld_objects(payload: Any) -> list[dict[str, Any]]:
    """Flatten a parsed JSON-LD payload into a flat list of objects.

    Handles a single object, a list, and the ``@graph`` container.
    """
    out: list[dict[str, Any]] = []
    stack: list[Any] = [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            out.append(node)
            graph = node.get("@graph")
            if isinstance(graph, list):
                stack.extend(graph)
    return out


def _type_matches_business(obj: dict[str, Any]) -> bool:
    """True when the object's ``@type`` looks like a business/organization."""
    raw_type = obj.get("@type")
    types = raw_type if isinstance(raw_type, list) else [raw_type]
    for t in types:
        if isinstance(t, str) and t.lower() in _BUSINESS_TYPES:
            return True
    return False


def _stringify(value: Any) -> Optional[str]:
    """Coerce a JSON-LD scalar/list to a clean string (first item of a list)."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list) and value:
        return _stringify(value[0])
    return None


def _parse_address(node: Any) -> dict[str, Optional[str]]:
    """Normalise a schema.org ``address`` (PostalAddress dict or plain string)."""
    if isinstance(node, str):
        return {"street": node.strip() or None, "postal_code": None, "city": None}
    if isinstance(node, list) and node:
        return _parse_address(node[0])
    if isinstance(node, dict):
        return {
            "street": _stringify(node.get("streetAddress")),
            "postal_code": _stringify(node.get("postalCode")),
            "city": _stringify(node.get("addressLocality")),
        }
    return {"street": None, "postal_code": None, "city": None}


def parse_ld_json_blocks(blocks: Any) -> Optional[dict[str, Any]]:
    """Parse raw JSON-LD blocks and return the best business record found.

    @param blocks - A list of raw JSON-LD strings and/or already-parsed dicts/lists
        (e.g. from ``NodriverDom.evaluate_list`` or ``extract_ld_json_from_html``).
    @returns A normalised dict — keys: ``name``, ``phone``, ``website``, ``email``,
        ``street``, ``postal_code``, ``city``, ``category``, ``rating``,
        ``reviews_count`` (each optional) — or ``None`` when no business is found.
    """
    if not blocks:
        return None
    if not isinstance(blocks, (list, tuple)):
        blocks = [blocks]

    candidates: list[dict[str, Any]] = []
    for block in blocks:
        if isinstance(block, str):
            try:
                parsed = json.loads(block)
            except (json.JSONDecodeError, ValueError):
                continue
        else:
            parsed = block
        candidates.extend(_iter_ld_objects(parsed))

    # Prefer a typed business object; else any object carrying business-shaped fields.
    business = next((c for c in candidates if _type_matches_business(c)), None)
    if business is None:
        business = next(
            (c for c in candidates if c.get("telephone") or c.get("address")),
            None,
        )
    if business is None:
        return None

    address = _parse_address(business.get("address"))
    rating_node = business.get("aggregateRating")
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    if isinstance(rating_node, dict):
        try:
            rating_val = _stringify(rating_node.get("ratingValue"))
            rating = float(rating_val.replace(",", ".")) if rating_val else None
        except (TypeError, ValueError):
            rating = None
        try:
            count_val = _stringify(rating_node.get("reviewCount") or rating_node.get("ratingCount"))
            reviews_count = int(re.sub(r"\D", "", count_val)) if count_val else None
        except (TypeError, ValueError):
            reviews_count = None

    # @type is a decent category hint (e.g. "Plumber") — but drop the generic bases.
    ld_type = _stringify(business.get("@type"))
    category = ld_type if ld_type and ld_type.lower() not in {"localbusiness", "organization"} else None

    return {
        "name": _stringify(business.get("name") or business.get("legalName")),
        "phone": _stringify(business.get("telephone")),
        "website": _stringify(business.get("url") or business.get("sameAs")),
        "email": safe_email(_stringify(business.get("email"))),
        "description": _stringify(business.get("description")),
        "street": address["street"],
        "postal_code": address["postal_code"],
        "city": address["city"],
        "category": category,
        "rating": rating,
        "reviews_count": reviews_count,
    }


def extract_ld_json_from_html(html: Optional[str]) -> list[str]:
    """Return the raw text of every ``<script type="application/ld+json">`` in HTML.

    Used by the HTTP/BeautifulSoup path (Pages Jaunes tier 1). Robust to attribute
    ordering and extra attributes on the script tag.

    @param html - Full page HTML.
    @returns A list of raw JSON-LD strings (possibly empty).
    """
    if not html or not isinstance(html, str):
        return []
    pattern = re.compile(
        r"<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"][^>]*>(.*?)</script>",
        re.IGNORECASE | re.DOTALL,
    )
    return [m.group(1).strip() for m in pattern.finditer(html) if m.group(1).strip()]
