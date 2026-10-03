"""Suggest a domain for a prospect — a logical, ideally-available pre-fill in his country's extension.

Priority is the LOGICAL domain built from the business name (code logic): the client wants
THEIR name as the address, not a creative brand. Groq only enriches the alternatives (handy
when the exact name is taken or awkward). Every candidate — code or AI — is validated as a
real domain label and checked for availability (RDAP) before being offered, under the
extensions of the prospect's country (``.fr`` in France, ``.ch``, ``.be``, ``.lu``, ``.ca``).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from services.country_profiles import DEFAULT_COUNTRY_CODE, CountryProfiles
from services.domain.availability import availability_map
from services.domain.ovh_catalog import first_year_price_eur
from services.llm_service import llm_service

# A registrable domain label: 1-63 chars, letters/digits/hyphens, no leading/trailing hyphen.
_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
# How many candidates we RDAP-check (keeps the AFNIC calls bounded).
_MAX_CANDIDATES = 8


@dataclass
class DomainCandidate:
    """One proposed domain with its availability and estimated price."""

    domain: str
    available: bool | None  # True = free, False = taken, None = could not check
    price_eur: float | None


@dataclass
class DomainSuggestion:
    """The best pre-fill plus every candidate considered (for the UI's alternatives)."""

    suggested: str | None
    candidates: list[DomainCandidate]


def _ascii_lower(value: str) -> str:
    """Strip accents and lowercase (é → e), keeping the raw characters otherwise."""
    normalized = unicodedata.normalize("NFKD", value or "")
    return normalized.encode("ascii", "ignore").decode("ascii").lower()


def _compact(value: str) -> str:
    """Business name → a single hyphen-free label (``Chez Mimon`` → ``chezmimon``)."""
    return re.sub(r"[^a-z0-9]+", "", _ascii_lower(value))


def _hyphenated(value: str) -> str:
    """Business name → a hyphen-separated label (``Chez Mimon`` → ``chez-mimon``)."""
    slug = re.sub(r"[^a-z0-9]+", "-", _ascii_lower(value)).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def _is_valid_label(label: str) -> bool:
    """Whether a bare label is a registrable domain label (no ``--`` to avoid IDN clashes)."""
    return bool(label) and "--" not in label and _LABEL_RE.match(label) is not None


class DomainSuggestionService:
    """Build and rank domain candidates for a prospect, in the extensions of his country."""

    def _candidate_labels(self, name: str, city: str | None, category: str | None) -> list[str]:
        """Ordered, de-duplicated labels built from the business name (logical first)."""
        compact = _compact(name)
        hyphen = _hyphenated(name)
        city_slug = _compact(city or "")
        trade_slug = _compact(category or "")

        ordered: list[str] = [compact, hyphen]
        if compact and city_slug:
            ordered.append(f"{compact}-{city_slug}")
        if hyphen and city_slug:
            ordered.append(f"{hyphen}-{city_slug}")
        if compact and trade_slug:
            ordered.append(f"{compact}-{trade_slug}")

        return self._dedupe_valid(ordered)

    @staticmethod
    def _dedupe_valid(labels: list[str]) -> list[str]:
        """Keep valid labels, first occurrence wins, order preserved."""
        seen: set[str] = set()
        out: list[str] = []
        for label in labels:
            if label and label not in seen and _is_valid_label(label):
                seen.add(label)
                out.append(label)
        return out

    async def suggest(
        self,
        *,
        name: str,
        city: str | None,
        category: str | None,
        use_ai: bool = True,
        country: str = DEFAULT_COUNTRY_CODE,
    ) -> DomainSuggestion:
        """Propose a domain for a prospect, ranked by logic then availability.

        Args:
            name: Business name (drives the logical candidates).
            city: City, when known (adds ``nom-ville`` variants).
            category: Trade, when known (adds a ``nom-metier`` variant).
            use_ai: Enrich with Groq (the « Suggérer » button); off for snappy as-you-type suggestions.
            country: ISO code of the prospect's country, whose profile names the extensions offered.

        Returns:
            A :class:`DomainSuggestion` — the best pre-fill plus the checked alternatives.
        """
        labels = self._candidate_labels(name, city, category)
        if use_ai:
            # Groq enriches the pool (best-effort) — validated and appended after the logical ones.
            ai_labels = await llm_service.suggest_domain_names(business_name=name, city=city, category=category)
            labels = self._dedupe_valid(labels + ai_labels)
        labels = labels[:_MAX_CANDIDATES]

        tlds = CountryProfiles.get(country).domain_tlds
        domains = [f"{label}{tld}" for tld in tlds for label in labels]
        available = await availability_map(domains)
        prices = {tld: await first_year_price_eur(tld.lstrip(".")) for tld in tlds}

        candidates = [
            DomainCandidate(domain=domain, available=available.get(domain), price_eur=prices[tld])
            for tld in tlds
            for domain in (f"{label}{tld}" for label in labels)
        ]
        return DomainSuggestion(suggested=self._pick_suggested(candidates), candidates=candidates)

    @staticmethod
    def _pick_suggested(candidates: list[DomainCandidate]) -> str | None:
        """The best pre-fill: first confirmed-free, else first unknown, else the top logical one."""
        for candidate in candidates:
            if candidate.available is True:
                return candidate.domain
        for candidate in candidates:
            if candidate.available is None:
                return candidate.domain
        return candidates[0].domain if candidates else None


domain_suggestion_service = DomainSuggestionService()
