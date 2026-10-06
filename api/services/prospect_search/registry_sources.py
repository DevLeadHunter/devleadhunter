"""
Registry sources — public files that list tradespeople WITH their email.

Two official, free files turn the search around: instead of hunting an email at the
end, start from companies whose email is published by a public body.

- France: ADEME's list of RGE-certified companies (building and energy trades), an
  open API that says whether a website is declared.
- Québec: the RBQ's list of licensed contractors, a daily open-data file.

A company coming from a registry is still verified like any other candidate: « no
website declared » is not « no website ».
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx

from enums.prospect_search import CandidateOrigin
from scrappers.email_candidate_scoring import email_candidate_scorer
from services.decision_maker.normalize import fold
from services.prospect_search.trade_catalog import TradeProfile

logger = logging.getLogger(__name__)

_RGE_LINES_URL: str = "https://data.ademe.fr/data-fair/api/v1/datasets/liste-des-entreprises-rge-2/lines"
_RGE_PUBLIC_URL: str = "https://data.ademe.fr/datasets/liste-des-entreprises-rge-2"
_RBQ_FILE_URL: str = (
    "https://www.donneesquebec.ca/recherche/dataset/755b45d6-7aee-46df-a216-748a0191c79f/resource/"
    "32f6ec46-85fd-45e9-945b-965d9235840a/download/rdl01_extractiondonneesouvertes.zip"
)
_RBQ_PUBLIC_URL: str = "https://www.donneesquebec.ca/recherche/dataset/licencesactives"
_RBQ_FILE_MAX_AGE_SECONDS: float = 24 * 3600
_REQUEST_TIMEOUT_SECONDS: float = 60.0
_INSTITUTION_NAME_MARKERS: tuple[str, ...] = (
    "hopital",
    "ciusss",
    "cisss",
    "cegep",
    "universite",
    "commission scolaire",
)


@dataclass(frozen=True)
class RegistryCompany:
    """One company read in a public registry."""

    name: str
    city: str
    address: str | None
    phone: str | None
    email: str
    registry_number: str | None
    origin: CandidateOrigin
    source_label: str
    source_url: str
    owner_name: str | None = None

    @staticmethod
    def is_institution(name: str, email: str, *, city: str) -> bool:
        """Whether a registered holder is a hospital, a school or a public body that keeps its own licence, not a tradesperson."""
        folded_name = fold(name)
        has_institution_name = any(marker in folded_name for marker in _INSTITUTION_NAME_MARKERS)
        return has_institution_name or email_candidate_scorer.belongs_to_an_institution(email, city=city)


class RgeRegistry:
    """ADEME's list of RGE-certified companies (France)."""

    async def companies_near(self, *, trade: TradeProfile, city: str, limit: int) -> list[RegistryCompany]:
        """
        Companies of a trade, with an email and no declared website, in the town's département.

        Args:
            trade: Profile of the searched trade (its RGE work domains select the companies).
            city: A town of the département to cover.
            limit: Most companies to return.

        Returns:
            The companies, one per SIRET; empty when the trade has no RGE domain or the API fails.
        """
        if not trade.rge_domains:
            return []
        town = fold(city).upper()
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
                located = await client.get(
                    _RGE_LINES_URL, params={"size": 1, "select": "code_postal", "qs": f'commune:"{town}"'}
                )
                located.raise_for_status()
                rows = located.json().get("results") or []
                if not rows:
                    return []
                department = str(rows[0].get("code_postal") or "")[:2]
                domains = " OR ".join(f'"{domain}"' for domain in trade.rge_domains)
                listed = await client.get(
                    _RGE_LINES_URL,
                    params={
                        "size": limit,
                        "collapse": "siret",
                        "select": "nom_entreprise,adresse,code_postal,commune,telephone,email,siret",
                        "qs": (
                            f"code_postal:{department}* AND _exists_:email AND NOT _exists_:site_internet "
                            f"AND domaine:({domains})"
                        ),
                    },
                )
                listed.raise_for_status()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("[RGE] lookup failed for %s / %s: %s", trade.key, city, exc)
            return []

        companies: list[RegistryCompany] = []
        for row in listed.json().get("results") or []:
            name = str(row.get("nom_entreprise") or "").strip()
            email = str(row.get("email") or "").strip().lower()
            if not name or "@" not in email or RegistryCompany.is_institution(name, email, city=city):
                continue
            companies.append(
                RegistryCompany(
                    name=name.title(),
                    city=str(row.get("commune") or city).title(),
                    address=str(row.get("adresse") or "").title() or None,
                    phone=str(row.get("telephone") or "").strip() or None,
                    email=email,
                    registry_number=str(row.get("siret") or "").strip() or None,
                    origin=CandidateOrigin.REGISTRY_RGE,
                    source_label="Liste des entreprises RGE (ADEME)",
                    source_url=_RGE_PUBLIC_URL,
                )
            )
        return companies


class RbqRegistry:
    """The RBQ's open file of active contractor licences (Québec)."""

    def __init__(self) -> None:
        self._file_path: Path = Path(tempfile.gettempdir()) / "devleadhunter_rbq_licences.zip"
        self._lock = asyncio.Lock()

    async def companies_in(self, *, trade: TradeProfile, city: str, limit: int) -> list[RegistryCompany]:
        """
        Licensed contractors of a trade, with an email, in a town.

        Args:
            trade: Profile of the searched trade (its RBQ sub-categories select the licences).
            city: Town of the contractors.
            limit: Most contractors to return.

        Returns:
            The contractors, one per licence; empty when the trade has no RBQ sub-category or the file is unavailable.
        """
        if not trade.rbq_subcategories:
            return []
        async with self._lock:
            if not await self._refresh_file():
                return []
        return await asyncio.to_thread(self._read_file, set(trade.rbq_subcategories), fold(city), limit)

    async def _refresh_file(self) -> bool:
        """Download the licence file when the local copy is missing or older than a day."""
        is_fresh = (
            self._file_path.exists() and time.time() - self._file_path.stat().st_mtime < _RBQ_FILE_MAX_AGE_SECONDS
        )
        if is_fresh:
            return True
        try:
            async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_SECONDS * 2, follow_redirects=True) as client:
                response = await client.get(_RBQ_FILE_URL)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("[RBQ] licence file download failed: %s", exc)
            return self._file_path.exists()
        self._file_path.write_bytes(response.content)
        return True

    def _read_file(self, subcategories: set[str], folded_city: str, limit: int) -> list[RegistryCompany]:
        """Blocking read of the licence file, filtered on the sub-categories and the town."""
        try:
            with zipfile.ZipFile(self._file_path) as archive, archive.open(archive.namelist()[0]) as licence_file:
                # Streamed row by row: the file holds close to a million lines, too heavy to load whole.
                rows = csv.DictReader(io.TextIOWrapper(licence_file, encoding="utf-8-sig", errors="replace"))
                return self._matching_companies(rows, subcategories, folded_city, limit)
        except (OSError, zipfile.BadZipFile, IndexError, csv.Error) as exc:
            logger.warning("[RBQ] licence file unreadable: %s", exc)
            return []

    @staticmethod
    def _matching_companies(
        rows: csv.DictReader[str], subcategories: set[str], folded_city: str, limit: int
    ) -> list[RegistryCompany]:
        """Keep one company per licence among the rows of the asked sub-categories and town."""
        companies: dict[str, RegistryCompany] = {}
        for row in rows:
            licence = str(row.get("Numéro de licence") or "").strip()
            email = str(row.get("Courriel") or "").strip().lower()
            if not licence or licence in companies or "@" not in email:
                continue
            if str(row.get("Sous-catégories") or "").strip() not in subcategories:
                continue
            if fold(str(row.get("Municipalité") or "")) != folded_city:
                continue
            legal_name = str(row.get("Nom de l'intervenant") or "").strip()
            trade_name = str(row.get("Autre nom") or "").strip()
            if RegistryCompany.is_institution(
                f"{legal_name} {trade_name}", email, city=str(row.get("Municipalité") or "")
            ):
                continue
            is_person = fold(str(row.get("Statut juridique") or "")) == "personne physique"
            companies[licence] = RegistryCompany(
                name=trade_name or legal_name,
                city=str(row.get("Municipalité") or "").strip(),
                address=str(row.get("Adresse") or "").strip().title() or None,
                phone=str(row.get("Numéro de téléphone") or "").strip() or None,
                email=email,
                registry_number=f"RBQ {licence}",
                origin=CandidateOrigin.REGISTRY_RBQ,
                source_label="Licences actives de la RBQ (Données Québec)",
                source_url=_RBQ_PUBLIC_URL,
                owner_name=legal_name.title() if is_person and legal_name else None,
            )
            if len(companies) >= limit:
                break
        return [company for company in companies.values() if company.name]


rge_registry = RgeRegistry()
rbq_registry = RbqRegistry()
