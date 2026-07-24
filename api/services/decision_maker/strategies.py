"""The name-resolution strategies of the decision-maker cascade.

Every strategy is source-agnostic (fed by ResolutionContext, whatever scraper
discovered the prospect), best-effort (network/parse failures return an empty
list, never raise) and returns scored NameCandidate objects. The resolver
merges them and applies the confidence threshold.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from core.config import settings
from services.decision_maker.normalize import (
    company_similarity,
    infer_gender,
    split_registry_full_name,
    title_case_name,
)
from services.decision_maker.types import NameCandidate, ResolutionContext

logger = logging.getLogger(__name__)

_RECHERCHE_ENTREPRISES_URL = "https://recherche-entreprises.api.gouv.fr/search"
_PAPPERS_URL = "https://api.pappers.fr/v2/recherche"

# A company-name match below this similarity is considered a different business.
_MIN_COMPANY_SIMILARITY = 0.45


class RegistreGouvStrategy:
    """Tier 1 — the official (free, key-less) « Recherche d'entreprises » API.

    Exposes ``dirigeants`` (nom / prenoms / qualite) straight from SIRENE/RNE.
    For an ENTREPRISE INDIVIDUELLE the dirigeant IS the person → high
    confidence. Multi-dirigeant companies are scored lower (ambiguity).
    """

    name = "registre_gouv"

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Query the registry by company name (+ postal code / city)."""
        query = (context.company_name or "").strip()
        if not query:
            return []
        params: dict[str, Any] = {"q": query, "page": 1, "per_page": 5}
        if context.postal_code:
            params["code_postal"] = context.postal_code
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(_RECHERCHE_ENTREPRISES_URL, params=params)
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
        except Exception as exc:
            logger.warning("registre_gouv lookup failed for %r: %s", query, exc)
            return []
        return self.parse_results(payload.get("results") or [], context)

    def parse_results(self, results: list[dict[str, Any]], context: ResolutionContext) -> list[NameCandidate]:
        """Score the registry matches (pure — unit-testable on fixtures)."""
        candidates: list[NameCandidate] = []
        for result in results[:5]:
            similarity = self._match_similarity(result, context)
            if similarity < _MIN_COMPANY_SIMILARITY:
                continue
            city_ok = self._city_matches(result, context)
            base = 0.5 + 0.25 * similarity + (0.15 if city_ok else 0.0)

            dirigeants = [
                d
                for d in (result.get("dirigeants") or [])
                if (d.get("type_dirigeant") or "personne physique") == "personne physique"
            ]
            is_ei = str(result.get("nature_juridique") or "").startswith("1000")

            if is_ei:
                # EI: the denomination itself is « NOM Prénom » of the person.
                first, last = split_registry_full_name(str(result.get("nom_complet") or ""))
                if dirigeants:
                    first = title_case_name(dirigeants[0].get("prenoms")) or first
                    last = title_case_name(dirigeants[0].get("nom")) or last
                if first or last:
                    candidates.append(self._candidate(first, last, min(0.95, base + 0.25), result))
                continue

            if len(dirigeants) == 1:
                d = dirigeants[0]
                candidates.append(
                    self._candidate(
                        title_case_name(d.get("prenoms")),
                        title_case_name(d.get("nom")),
                        min(0.9, base + 0.1),
                        result,
                    )
                )
            elif len(dirigeants) > 1:
                # Ambiguous: prefer the gérant/président, scored under the
                # solo case (golden rule — when unsure, stay neutral).
                lead = next(
                    (
                        d
                        for d in dirigeants
                        if "gérant" in str(d.get("qualite") or "").lower()
                        or "président" in str(d.get("qualite") or "").lower()
                    ),
                    None,
                )
                if lead is not None:
                    candidates.append(
                        self._candidate(
                            title_case_name(lead.get("prenoms")),
                            title_case_name(lead.get("nom")),
                            min(0.75, base),
                            result,
                        )
                    )
        return candidates

    def _candidate(
        self,
        first: str | None,
        last: str | None,
        confidence: float,
        result: dict[str, Any],
    ) -> NameCandidate:
        """Build a candidate carrying the matched SIREN for traceability."""
        # Registries may pack several first names (« Léo Jean Marc ») — keep the first.
        first_single = (first or "").split(" ")[0] or None
        return NameCandidate(
            first=first_single,
            last=last,
            gender=infer_gender(first_single),
            source=self.name,
            confidence=round(confidence, 2),
            raw={"siren": result.get("siren"), "nom_complet": result.get("nom_complet")},
        )

    @staticmethod
    def _match_similarity(result: dict[str, Any], context: ResolutionContext) -> float:
        """Best similarity between the prospect name and the registry names."""
        names = [str(result.get("nom_complet") or ""), str(result.get("nom_raison_sociale") or "")]
        return max(company_similarity(context.company_name, n) for n in names)

    @staticmethod
    def _city_matches(result: dict[str, Any], context: ResolutionContext) -> bool:
        """True when the registry HQ city/postal code matches the prospect's."""
        siege = result.get("siege") or {}
        if context.postal_code and str(siege.get("code_postal") or "") == context.postal_code:
            return True
        if context.city:
            from services.decision_maker.normalize import fold

            return fold(str(siege.get("libelle_commune") or "")) == fold(context.city)
        return False


class PappersStrategy:
    """Tier 1bis — Pappers (structured dirigeants, freemium API key).

    Clean no-op when ``PAPPERS_API_KEY`` is not configured.
    """

    name = "pappers"

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Query Pappers by company name + postal code (when a key exists)."""
        api_key = getattr(settings, "pappers_api_key", "") or ""
        query = (context.company_name or "").strip()
        if not api_key or not query:
            return []
        params: dict[str, Any] = {"api_token": api_key, "q": query, "par_page": 3}
        if context.postal_code:
            params["code_postal"] = context.postal_code
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(_PAPPERS_URL, params=params)
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
        except Exception as exc:
            logger.warning("pappers lookup failed for %r: %s", query, exc)
            return []
        return self.parse_results(payload.get("resultats") or [], context)

    def parse_results(self, results: list[dict[str, Any]], context: ResolutionContext) -> list[NameCandidate]:
        """Score Pappers matches (pure — unit-testable on fixtures)."""
        candidates: list[NameCandidate] = []
        for result in results[:3]:
            similarity = company_similarity(context.company_name, str(result.get("nom_entreprise") or ""))
            if similarity < _MIN_COMPANY_SIMILARITY:
                continue
            representants = [r for r in (result.get("representants") or []) if r.get("personne_morale") is not True]
            if not representants:
                continue
            lead = representants[0]
            first = title_case_name(str(lead.get("prenom") or "").split(" ")[0] or None)
            last = title_case_name(lead.get("nom"))
            if not (first or last):
                continue
            confidence = min(0.9, 0.55 + 0.25 * similarity + (0.1 if len(representants) == 1 else 0.0))
            candidates.append(
                NameCandidate(
                    first=first,
                    last=last,
                    gender=infer_gender(first),
                    source=self.name,
                    confidence=round(confidence, 2),
                    raw={"siren": result.get("siren")},
                )
            )
        return candidates


# « Réponse du propriétaire » signatures: a line/dash followed by a short name.
_OWNER_SIGNATURE_RE = re.compile(
    r"(?:^|[\n\-—–])\s*(?:cordialement|merci|à bientôt)?[,\s]*([A-ZÀ-Ü][a-zà-ü]{2,15})\s*$",
    re.MULTILINE,
)


class OwnerResponseStrategy:
    """Tier 2 — signatures in Google « réponse du propriétaire » texts.

    Uses only text already captured by the enrichment scraper (no network).
    A recurring signature (« … à bientôt ! — Léo ») is a decent first-name
    signal, scored moderately.
    """

    name = "owner_response"

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Extract recurring signatures from owner responses."""
        counts: dict[str, int] = {}
        for text in context.owner_responses:
            for match in _OWNER_SIGNATURE_RE.finditer(text or ""):
                name = title_case_name(match.group(1))
                if name:
                    counts[name] = counts.get(name, 0) + 1
        if not counts:
            return []
        best, seen = max(counts.items(), key=lambda kv: kv[1])
        confidence = 0.55 if seen == 1 else 0.7
        return [
            NameCandidate(
                first=best,
                last=None,
                gender=infer_gender(best),
                source=self.name,
                confidence=confidence,
                raw={"occurrences": seen},
            )
        ]


# « Gérant : Prénom Nom » patterns found on mentions-légales / à-propos pages.
_LEGAL_ROLE_RE = re.compile(
    r"(?:g[ée]rant(?:e)?|directeur(?:\s+de\s+la)?\s+publication|responsable\s+de\s+(?:la\s+)?publication|"
    r"repr[ée]sentant\s+l[ée]gal|propri[ée]taire|fondateur|dirigeant)\s*(?:de la publication)?\s*[:\-–]\s*"
    r"(?:m\.|mme|monsieur|madame)?\s*([A-ZÀ-Ü][a-zà-ü]+(?:[-\s][A-ZÀ-Ü][a-zà-üA-ZÀ-Ü]+){0,3})",
    re.IGNORECASE,
)

_LEGAL_PATHS = ("/mentions-legales", "/mentions_legales", "/mentions-légales", "/a-propos", "/about")


class LegalMentionsStrategy:
    """Tier 2 — the prospect's own website legal/about pages.

    French legal pages must name the publisher (« Gérant : … ») — a strong,
    self-declared signal when the prospect has a website.
    """

    name = "legal_mentions"

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Fetch the site's legal/about pages and extract the named person."""
        website = (context.website or "").strip()
        if not website:
            return []
        if not website.startswith("http"):
            website = f"https://{website}"
        base = website.rstrip("/")
        texts: list[str] = []
        try:
            async with httpx.AsyncClient(
                timeout=10.0, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}
            ) as client:
                for path in ("", *_LEGAL_PATHS):
                    try:
                        response = await client.get(f"{base}{path}")
                        if response.status_code == 200 and "text/html" in response.headers.get("content-type", ""):
                            texts.append(response.text[:200_000])
                    except Exception:
                        continue
                    if len(texts) >= 3:
                        break
        except Exception as exc:
            logger.warning("legal_mentions fetch failed for %r: %s", website, exc)
            return []
        return self.parse_pages(texts)

    def parse_pages(self, pages: list[str]) -> list[NameCandidate]:
        """Extract « rôle : Prénom Nom » declarations (pure — testable)."""
        for html in pages:
            text = re.sub(r"<[^>]+>", " ", html)
            match = _LEGAL_ROLE_RE.search(text)
            if not match:
                continue
            full = title_case_name(match.group(1)) or ""
            parts = full.split(" ")
            if len(parts) >= 2:
                first, last = parts[0], " ".join(parts[1:])
            else:
                first, last = full or None, None
            if not first:
                continue
            return [
                NameCandidate(
                    first=first,
                    last=last,
                    gender=infer_gender(first),
                    source=self.name,
                    confidence=0.75,
                    raw={},
                )
            ]
        return []


class LlmAggregateStrategy:
    """Tier 3 (last resort) — LLM over the already-scraped free text.

    Anti-hallucination gate: the model must QUOTE the exact snippet naming the
    person; if the quote is not literally present in the source text, the
    answer is discarded.
    """

    name = "llm_aggregate"

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Ask the LLM for the most likely owner name, with a mandatory quote."""
        from services.llm_service import llm_service

        corpus = "\n".join([context.description or "", *context.owner_responses]).strip()
        if not corpus or not llm_service.is_configured:
            return []
        prompt = (
            f"Texte public à propos de l'entreprise « {context.company_name} » :\n---\n{corpus[:4000]}\n---\n"
            "Si (et seulement si) ce texte nomme la personne qui dirige l'entreprise, réponds sur "
            "EXACTEMENT trois lignes :\nPRENOM: <prénom ou vide>\nNOM: <nom ou vide>\n"
            "CITATION: <l'extrait exact du texte qui contient ce nom>\n"
            "Si aucun nom de personne n'apparaît, réponds uniquement : AUCUN"
        )
        answer = await llm_service._chat([{"role": "user", "content": prompt}], max_tokens=120)
        if not answer or "AUCUN" in answer.upper()[:12]:
            return []
        return self.parse_answer(answer, corpus)

    def parse_answer(self, answer: str, corpus: str) -> list[NameCandidate]:
        """Validate the LLM answer against the source text (pure — testable)."""
        fields: dict[str, str] = {}
        for line in answer.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                fields[key.strip().upper()] = value.strip()
        first = title_case_name(fields.get("PRENOM") or None)
        last = title_case_name(fields.get("NOM") or None)
        quote = (fields.get("CITATION") or "").strip()
        if not (first or last) or not quote:
            return []
        # The quote must literally exist in the corpus (hallucination gate).
        from services.decision_maker.normalize import fold

        if fold(quote)[:60] not in fold(corpus):
            return []
        return [
            NameCandidate(
                first=first,
                last=last,
                gender=infer_gender(first),
                source=self.name,
                confidence=0.6,
                raw={"quote": quote[:200]},
            )
        ]
