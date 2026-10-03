"""Professional license lookup in the public RBQ registry (Québec construction contractors).

Calls the JSON API behind the registry's Blazor front. A holder is kept only when its name AND its
municipality match the prospect (never a homonym), an ambiguous result yields nothing, and a license
typed by a human is never overwritten.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy.orm import Session

from enums.professional_license_source import ProfessionalLicenseSource
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from services.decision_maker.normalize import fold
from services.scraper_diagnostics_service import (
    STATUS_EMPTY,
    STATUS_ERROR,
    STATUS_OK,
    scraper_diagnostics_service,
)
from services.trade_normalizer import TradeNormalizer

logger = logging.getLogger(__name__)

RBQ_REGISTRY_SEARCH_URL = "https://www.pes.rbq.gouv.qc.ca/APIPROXY/RBQ.Registre.API/Licence/Rechercher"
RBQ_LICENSE_LABEL = "Licence RBQ"
RBQ_DIAGNOSTIC_SOURCE = "rbq_registry"

_RBQ_SEARCH_MODE_BY_BUSINESS_NAME = 1
_RBQ_LICENSE_TYPE_CONTRACTOR = 1
_RBQ_LICENSE_STATUS_VALID = 3
_RBQ_LICENSE_STATUS_VALID_WITH_RESTRICTION = 2
_RBQ_DISPLAYABLE_LICENSE_STATUSES: frozenset[int] = frozenset(
    {_RBQ_LICENSE_STATUS_VALID, _RBQ_LICENSE_STATUS_VALID_WITH_RESTRICTION}
)

_RBQ_LICENSE_NUMBER_RE = re.compile(r"^\d{4}-?\d{4}(-?\d{2})?$")
_REQUEST_TIMEOUT_SECONDS = 12.0

_RBQ_LICENSED_TRADES: frozenset[str] = frozenset(
    {
        "électricien",
        "plombier",
        "chauffagiste",
        "couvreur",
        "paysagiste",
        "maçon",
        "menuisier",
        "carreleur",
        "peintre",
        "serrurier",
    }
)
_RBQ_LICENSED_CATEGORY_KEYWORDS: tuple[str, ...] = (
    "entrepreneur general",
    "entrepreneur en construction",
    "construction",
    "renovation",
    "excavation",
    "toiture",
    "charpent",
    "isolation",
)

_COMPANY_NAME_NOISE_WORDS: frozenset[str] = frozenset(
    {
        "inc",
        "ltee",
        "ltd",
        "enr",
        "senc",
        "sencrl",
        "cie",
        "co",
        "les",
        "le",
        "la",
        "de",
        "du",
        "des",
        "et",
        "entreprise",
        "entreprises",
        "quebec",
        "canada",
    }
)
_MIN_NAME_SIMILARITY = 0.5


@dataclass(frozen=True)
class RbqLicenseHolder:
    """One holder row of the RBQ registry search results."""

    business_name: str
    other_names: str
    license_number: str
    city: str
    status_code: int
    license_type_code: int


@dataclass(frozen=True)
class ProfessionalLicenseMatch:
    """A license confidently attributed to the prospect, ready to persist."""

    label: str
    number: str
    source: str
    provenance: str


class RbqLicenseRegistryClient:
    """HTTP client of the RBQ registry JSON API."""

    async def search_by_business_name(self, business_name: str) -> list[RbqLicenseHolder] | None:
        """Search the registry by business name.

        Args:
            business_name: The prospect's business name (the API needs at least 2 letters).

        Returns:
            The holders returned by the registry (possibly empty), or None when the registry is
            unreachable, blocks the call or answers something unexpected.
        """
        query = business_name.strip()
        if len(query) < 2:
            return []
        body: dict[str, Any] = {
            "ModeRecherche": _RBQ_SEARCH_MODE_BY_BUSINESS_NAME,
            "CriteresRecherche": {"NomEntreprise": query},
            "NumeroPage": 1,
        }
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(RBQ_REGISTRY_SEARCH_URL, json=body, headers={"Accept": "application/json"})
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
        except Exception as exc:
            logger.warning("RBQ registry search failed for %r: %s", query, exc)
            return None
        return self.parse_search_results(payload)

    @staticmethod
    def parse_search_results(payload: dict[str, Any]) -> list[RbqLicenseHolder]:
        """Turn the registry's ``retour.licences`` rows into holders.

        Args:
            payload: The decoded JSON answer of ``/Licence/Rechercher``.

        Returns:
            One holder per row that carries a license number; malformed rows are skipped.
        """
        result = payload.get("retour") if isinstance(payload, dict) else None
        rows = result.get("licences") if isinstance(result, dict) else None
        holders: list[RbqLicenseHolder] = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            license_number = str(row.get("noLicence") or "").strip()
            if not license_number:
                continue
            holders.append(
                RbqLicenseHolder(
                    business_name=str(row.get("nomIntervenant") or "").strip(),
                    other_names=str(row.get("autresNoms") or "").strip(),
                    license_number=license_number,
                    city=RbqLicenseRegistryClient.city_from_address_line(row.get("adresseLigne2")),
                    status_code=int(row.get("statutLicence") or 0),
                    license_type_code=int(row.get("typeLicence") or 0),
                )
            )
        return holders

    @staticmethod
    def city_from_address_line(address_line: Any) -> str:
        """Extract the municipality from the registry's « Ville QC » address line."""
        if not isinstance(address_line, str):
            return ""
        return re.sub(r"\s+\(?QC\)?\s*$", "", address_line.strip(), flags=re.IGNORECASE).strip()


class ProfessionalLicenseService:
    """Find a prospect's professional license in the public registry of its country and persist it."""

    def __init__(self, registry_client: RbqLicenseRegistryClient | None = None) -> None:
        self._registry_client = registry_client or RbqLicenseRegistryClient()

    @staticmethod
    def is_eligible(prospect: ProspectDB) -> bool:
        """Tell whether the prospect's country and trade call for a registry lookup.

        Only Québec (country CA) construction trades are covered; garages, barbers, dentists and food
        businesses never need an RBQ license.
        """
        if (prospect.country or "").strip().upper() != "CA":
            return False
        category = prospect.category or ""
        if TradeNormalizer.normalize(category) in _RBQ_LICENSED_TRADES:
            return True
        folded_category = fold(category)
        return any(keyword in folded_category for keyword in _RBQ_LICENSED_CATEGORY_KEYWORDS)

    @staticmethod
    def format_license_number(raw_number: str) -> str:
        """Format a registry license number the way the RBQ prints it (« 1117-4539-60 »).

        Args:
            raw_number: The 8 or 10 digit number, with or without dashes.

        Returns:
            The dashed number, or the input untouched when it does not look like an RBQ number.
        """
        digits = raw_number.replace("-", "").strip()
        if not _RBQ_LICENSE_NUMBER_RE.match(digits):
            return raw_number.strip()
        groups = [digits[0:4], digits[4:8]]
        if len(digits) == 10:
            groups.append(digits[8:10])
        return "-".join(groups)

    @staticmethod
    def _city_key(city: str) -> str:
        """Comparison key of a municipality (« Saint-Jérôme » = « St-Jerome » = « saint jerome »)."""
        key = re.sub(r"[^a-z0-9 ]", " ", fold(city))
        key = re.sub(r"\bsainte?\b", "st", key)
        return re.sub(r"\s+", "", key)

    @staticmethod
    def _name_tokens(name: str) -> set[str]:
        """Significant tokens of a company name (legal forms and filler words removed)."""
        tokens = {token for token in re.split(r"[^a-z0-9]+", fold(name)) if len(token) > 1}
        return tokens - _COMPANY_NAME_NOISE_WORDS

    @classmethod
    def name_similarity(cls, prospect_name: str, holder_name: str) -> float:
        """Token-overlap similarity (0..1) between the prospect's name and a holder's name."""
        prospect_tokens = cls._name_tokens(prospect_name)
        holder_tokens = cls._name_tokens(holder_name)
        if not prospect_tokens or not holder_tokens:
            return 0.0
        return len(prospect_tokens & holder_tokens) / len(prospect_tokens | holder_tokens)

    @classmethod
    def pick_match(
        cls, prospect_name: str, prospect_city: str | None, holders: list[RbqLicenseHolder]
    ) -> RbqLicenseHolder | None:
        """Keep the one holder whose name AND municipality match the prospect.

        Args:
            prospect_name: Business name stored on the prospect.
            prospect_city: Prospect municipality; without it nothing can be confirmed.
            holders: Registry search results.

        Returns:
            The matching holder, or None when none, several (ambiguous) or an unconfirmable one.
        """
        if not prospect_city or not prospect_city.strip():
            return None
        prospect_city_key = cls._city_key(prospect_city)
        scored: dict[str, tuple[float, RbqLicenseHolder]] = {}
        for holder in holders:
            if holder.license_type_code != _RBQ_LICENSE_TYPE_CONTRACTOR:
                continue
            if holder.status_code not in _RBQ_DISPLAYABLE_LICENSE_STATUSES:
                continue
            if cls._city_key(holder.city) != prospect_city_key:
                continue
            similarity = max(
                cls.name_similarity(prospect_name, holder.business_name),
                cls.name_similarity(prospect_name, holder.other_names) if holder.other_names else 0.0,
            )
            if similarity < _MIN_NAME_SIMILARITY:
                continue
            previous = scored.get(holder.license_number)
            if previous is None or similarity > previous[0]:
                scored[holder.license_number] = (similarity, holder)
        if not scored:
            return None
        exact_matches = [holder for similarity, holder in scored.values() if similarity >= 1.0]
        if len(exact_matches) == 1:
            return exact_matches[0]
        if len(scored) == 1:
            return next(iter(scored.values()))[1]
        return None

    async def lookup(self, prospect: ProspectDB) -> ProfessionalLicenseMatch | None:
        """Look the prospect up in its country's registry.

        Returns:
            The confidently matched license, or None when the prospect is not eligible, the registry
            is unavailable, or no holder matches name AND municipality.
        """
        if not self.is_eligible(prospect):
            return None
        holders = await self._registry_client.search_by_business_name(prospect.name or "")
        if holders is None:
            return None
        holder = self.pick_match(prospect.name or "", prospect.city, holders)
        if holder is None:
            return None
        return ProfessionalLicenseMatch(
            label=RBQ_LICENSE_LABEL,
            number=self.format_license_number(holder.license_number),
            source=ProfessionalLicenseSource.RBQ_REGISTRY.value,
            provenance=f"Registre RBQ : « {holder.business_name} », {holder.city}, nom et ville concordants",
        )

    async def resolve_for_enrichment(self, db: Session, prospect: ProspectDB, record: ProspectEnrichment) -> None:
        """Fill the enrichment's license from the registry when it is missing or machine-set.

        Best-effort: a license typed by a human is never overwritten, and a registry failure leaves the
        record untouched and only shows up as a monitoring diagnostic, never as an enrichment failure.
        """
        if record.professional_license_source == ProfessionalLicenseSource.MANUAL.value:
            return
        if not self.is_eligible(prospect):
            return
        try:
            match = await self.lookup(prospect)
        except Exception as exc:
            logger.warning("Professional license lookup failed for prospect %s: %s", prospect.id, exc)
            self._record_diagnostic(prospect, STATUS_ERROR, 0, str(exc))
            return
        if match is None:
            self._record_diagnostic(
                prospect, STATUS_EMPTY, 0, "Aucune licence concordante (nom + ville) dans le registre"
            )
            return
        record.professional_license_label = match.label
        record.professional_license_number = match.number
        record.professional_license_source = match.source
        db.commit()
        self._record_diagnostic(prospect, STATUS_OK, 1, match.provenance)

    @staticmethod
    def _record_diagnostic(prospect: ProspectDB, status: str, results_count: int, detail: str | None) -> None:
        """Log the lookup outcome on the monitoring page (best-effort, never raises)."""
        scraper_diagnostics_service.record(
            source=RBQ_DIAGNOSTIC_SOURCE,
            status=status,
            category=prospect.category,
            city=prospect.city,
            results_count=results_count,
            error_message=detail,
            html_snapshot=None,
            user_id=prospect.user_id,
        )


professional_license_service = ProfessionalLicenseService()
