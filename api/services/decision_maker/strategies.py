"""The name-resolution strategies of the decision-maker cascade.

Every strategy is source-agnostic (fed by ResolutionContext, whatever scraper
discovered the prospect), best-effort (network/parse failures return an empty
list, never raise) and returns scored NameCandidate objects. The resolver
merges them and applies the confidence threshold.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, replace
from html import unescape
from itertools import pairwise
from typing import TYPE_CHECKING, Any

import httpx

from core.config import settings
from services.decision_maker.activity import (
    activity_codes_of,
    activity_consistency,
    has_known_activity,
    is_main_activity,
)
from services.decision_maker.french_departments import FrenchDepartments
from services.decision_maker.given_names import GivenNames
from services.decision_maker.normalize import (
    company_similarity,
    fold,
    infer_gender,
    join_dotted_initials,
    split_registry_full_name,
    title_case_name,
)
from services.decision_maker.types import NameCandidate, ResolutionContext

if TYPE_CHECKING:
    from services.professional_license_service import RbqLicenceOfficer

logger = logging.getLogger(__name__)

_RECHERCHE_ENTREPRISES_URL = "https://recherche-entreprises.api.gouv.fr/search"
_PAPPERS_URL = "https://api.pappers.fr/v2/recherche"

# A company-name match below this similarity is considered a different business.
_MIN_COMPANY_SIMILARITY = 0.45
_CEASED_STATE = "C"
_PROPERTY_COMPANY_LEGAL_CATEGORY = "654"
_SOLE_TRADER_LEGAL_CATEGORY = "1000"
_MIN_KEYWORD_CHARS = 4
_MAX_NAME_KEYWORDS = 2
_KEYWORD_RESULTS_PER_PAGE = 10
_PERSON_NAME_WORD_RE = re.compile(r"[a-z]+(?:-[a-z]+)*")
_CIVILITY_BEFORE_LAST_NAME_RE = re.compile(
    r"\b(?i:m\.|mr\.?|monsieur|mme|madame)\s+([A-ZÀ-Ý][a-zà-ÿ]+(?:-[A-ZÀ-Ý][a-zà-ÿ]+)?)\b"
)
_ENSEIGNE_IN_NAME_RE = re.compile(r"\(([^)]+)\)")
_GLUED_WORDS_RE = re.compile(r"(?<=[a-zà-ÿ])(?=[A-ZÀ-Ý]|\d)")
_DOTTED_CAPITALS_RE = re.compile(r"^[A-ZÀ-Ý](?:\.[A-ZÀ-Ý]+)+\.?['’]?$")

# Evidence groups — candidates extracted from the SAME underlying data are one
# observation, not two (owner replies feed both the regex and the LLM; the
# registre and Pappers both resell SIRENE/RNE, so they never corroborate).
_GROUP_REGISTRY = "registry"
_GROUP_WEBSITE = "website"
_GROUP_SCRAPED_TEXT = "scraped_text"
_GROUP_CUSTOMER_REVIEWS = "customer_reviews"

_TRADE_AND_LEGAL_FORM_WORDS: frozenset[str] = frozenset(
    {
        "garage",
        "garages",
        "carrosserie",
        "mecanique",
        "paysagiste",
        "paysagistes",
        "paysage",
        "paysages",
        "paysager",
        "jardin",
        "jardins",
        "electricite",
        "electrique",
        "electricien",
        "plomberie",
        "plombier",
        "chauffage",
        "services",
        "entretien",
        "generale",
        "general",
        "inc",
        "sarl",
        "sas",
        "eurl",
    }
)
_MIN_REGISTRY_QUERY_CHARS = 3
_MIN_TRADE_FREE_SIMILARITY = 0.75


@dataclass(frozen=True)
class RegistryKeyword:
    """A query the registry is searched with when the business name finds nothing, and what it stands for."""

    text: str
    #: The first name (if known) and last name of the person the query names, when it names one.
    person: tuple[str | None, str] | None = None
    is_email_domain: bool = False


class TradeName:
    """A business's trade name read the way the registry spells its legal name."""

    @staticmethod
    def searchable(name: str) -> str:
        """
        The name as the registry files it: glued words apart, dotted initials joined.

        « ExempleAuto64 » reads « Exemple Auto 64 », « E.XP' Jardins » reads « EXP Jardins ».

        Args:
            name: The trade name, as the listing or the page writes it.

        Returns:
            The name to search the registry with; the name itself when nothing needs mending.
        """
        words = _GLUED_WORDS_RE.sub(" ", name or "").split()
        return " ".join(re.sub(r"[.'’]", "", word) if _DOTTED_CAPITALS_RE.match(word) else word for word in words)

    @staticmethod
    def without_trade_words(name: str) -> str:
        """The name without its trade and legal-form words (« Garage Exemple Auto » reads « Exemple Auto »)."""
        words = [word for word in re.split(r"\s+", (name or "").strip()) if word]
        return " ".join(word for word in words if fold(word).strip(".,") not in _TRADE_AND_LEGAL_FORM_WORDS)


class RegistreGouvStrategy:
    """Tier 1 — the official (free, key-less) « Recherche d'entreprises » API.

    Exposes ``dirigeants`` (nom / prenoms / qualite) straight from SIRENE/RNE.
    For an ENTREPRISE INDIVIDUELLE the dirigeant IS the person → high
    confidence. Multi-dirigeant companies are scored lower (ambiguity).
    """

    name = "registre_gouv"

    @staticmethod
    def siren_of(registry_number: str | None) -> str | None:
        """The SIREN of a French company number (a SIREN or a SIRET), or ``None`` for any other number."""
        if (registry_number or "").upper().startswith(("CHE", "RBQ")):
            return None
        digits = re.sub(r"\D", "", registry_number or "")
        return digits[:9] if len(digits) in (9, 14) else None

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """
        Query the registry by the company number the search read, else by company name in the business's département.

        The registry's full-text search wants every word of the query in the company's legal name: the name as
        the registry files it (« ExempleAuto64 » as « Exemple Auto 64 ») is tried next, then, when the trade name
        carries words the legal name lacks (« A.S auto garage » for A.S AUTO), the name without its trade words.
        The département comes from the postal code, else from the town (a business found on Facebook has none).
        When no query names the business, its words and its owner's name are searched among the companies of its
        trade in its département.
        """
        query = (context.company_name or "").strip()
        if not query:
            return []
        siren = self.siren_of(context.registry_number)
        department = FrenchDepartments.of_postal_code(context.postal_code) or await FrenchDepartments.of_town(
            context.city
        )
        queries = [(siren, False)] if siren else [(query, False)]
        searchable_query = TradeName.searchable(query)
        if not siren and searchable_query != query:
            queries.append((searchable_query, False))
        trade_free_query = TradeName.without_trade_words(query)
        if (
            not siren
            and trade_free_query != query
            and len(re.sub(r"\W", "", trade_free_query)) >= _MIN_REGISTRY_QUERY_CHARS
        ):
            queries.append((trade_free_query, True))
        for registry_query, is_trade_free_query in queries:
            results = await self._search(registry_query, department=None if siren else department, per_page=5)
            if results is None:
                return []
            candidates = self.parse_results(
                results, context, department=department, is_trade_free_query=is_trade_free_query
            )
            if candidates:
                return candidates
        if siren or not department:
            return []
        return await self._search_by_keywords(context, department)

    @staticmethod
    async def _search(
        query: str, *, department: str | None, per_page: int, activity_codes: list[str] | None = None
    ) -> list[dict[str, Any]] | None:
        """The registry's companies for a query, in a département and those activities when given; None on failure."""
        params: dict[str, Any] = {"q": query, "page": 1, "per_page": per_page}
        if department:
            params["departement"] = department
        if activity_codes:
            params["activite_principale"] = ",".join(activity_codes)
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                response = await client.get(_RECHERCHE_ENTREPRISES_URL, params=params)
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
        except Exception as exc:
            logger.warning("registre_gouv lookup failed for %r: %s", query, exc)
            return None
        return payload.get("results") or []

    async def _search_by_keywords(self, context: ResolutionContext, department: str) -> list[NameCandidate]:
        """
        Find the business by one of its words or its owner's name, among the companies of its trade in its département.

        The registry files « EXEMPLE Electrical » as « JULES MODELE (EXEMPLE) », « Modele Entretien parc et jardin »
        under its owner, a sole trader under the name his email spells (« jules.modele@ ») or his customers say
        (« Monsieur Modele »). Each is searched in the département among the companies declaring the trade's
        activity, a common name not hiding them; only active ones count, and a single one is the business — the
        one declaring the trade's main activity when several fit (an electrician, not a builder of the family).
        A word naming a commune (« Exemple-Auto Pau-Lescar ») is a place, not the business: never searched.
        """
        from services.trade_normalizer import TradeNormalizer

        trade = TradeNormalizer.normalize(context.trade)
        if not has_known_activity(trade):
            return []
        activity_codes = activity_codes_of(trade)
        for keyword in self._keywords(context):
            if (
                keyword.person is None
                and not keyword.is_email_domain
                and await FrenchDepartments.is_town_name(keyword.text)
            ):
                continue
            results = await self._search(
                keyword.text, department=department, per_page=_KEYWORD_RESULTS_PER_PAGE, activity_codes=activity_codes
            )
            matching = [
                result
                for result in results or []
                if self.is_keyword_company(result, keyword, context=context, trade=trade, department=department)
            ]
            if len(matching) > 1:
                matching = [result for result in matching if is_main_activity(trade, self._activity_of(result))]
            if len(matching) == 1:
                found = self._candidates_of(matching[0], base=0.75 if keyword.person else 0.7, geo_confirmed=True)
                provenance_note = f", trouvée par « {keyword.text} » dans le métier"
                return [replace(candidate, provenance=candidate.provenance + provenance_note) for candidate in found]
        return []

    @staticmethod
    def _keywords(context: ResolutionContext) -> list[RegistryKeyword]:
        """The words of the business name and of its own email domain, then the owners its emails and its customers name."""
        from scrappers.email_candidate_scoring import GENERIC_EMAIL_PROVIDERS
        from services.decision_maker.email_owner import PersonInEmail
        from services.prospect_search.business_name import BusinessName

        name_words = sorted(
            BusinessName.distinctive_words(context.company_name, town=context.city), key=len, reverse=True
        )
        keywords = [RegistryKeyword(word) for word in name_words if len(word) >= _MIN_KEYWORD_CHARS][
            :_MAX_NAME_KEYWORDS
        ]
        for email in context.emails:
            domain = fold(email.partition("@")[2])
            domain_label = domain.rsplit(".", 1)[0]
            if (
                domain not in GENERIC_EMAIL_PROVIDERS
                and len(domain_label) >= _MIN_KEYWORD_CHARS
                and domain_label.isalnum()
            ):
                keywords.append(RegistryKeyword(domain_label, is_email_domain=True))
        for email in context.emails:
            person = PersonInEmail.person_of(email, context.company_name)
            if person is not None:
                keywords.append(
                    RegistryKeyword(
                        f"{person.last_name} {person.first_name}", person=(person.first_name, person.last_name)
                    )
                )
        customer_texts = " ".join([*context.review_texts, *context.owner_responses])
        for last_name in dict.fromkeys(_CIVILITY_BEFORE_LAST_NAME_RE.findall(customer_texts)):
            keywords.append(RegistryKeyword(last_name, person=(None, last_name)))
        return keywords

    def is_keyword_company(
        self,
        result: dict[str, Any],
        keyword: RegistryKeyword,
        *,
        context: ResolutionContext,
        trade: str,
        department: str,
    ) -> bool:
        """
        Whether a company a keyword found is the business (pure — testable).

        It must be active, sit in the département, declare the trade's activity and not be a property company.
        Found by a person, that person runs it; by the email domain, a name of the company is that domain; by a
        word of the business name, a name of the company holds only words of the business name (« EXEMPLE »,
        not « MODELE PARC ET JARDIN » for « Exemple Entretien parc et jardin »), or the company is the sole
        trader whose last name the word is.

        Args:
            result: A registry company.
            keyword: The query that found it.
            context: The business looked for.
            trade: The business's trade, as the trade normalizer writes it.
            department: The business's département.

        Returns:
            True when the company can be the business.
        """
        siege = result.get("siege") or {}
        naf = self._activity_of(result)
        if (
            str(result.get("etat_administratif") or "") == _CEASED_STATE
            or self._is_property_company(result)
            or FrenchDepartments.of_postal_code(str(siege.get("code_postal") or "")) != department
            or activity_consistency(trade, naf) is not True
        ):
            return False
        is_sole_trader = str(result.get("nature_juridique") or "").startswith(_SOLE_TRADER_LEGAL_CATEGORY)
        people = [f"{d.get('prenoms') or ''} {d.get('nom') or ''}" for d in result.get("dirigeants") or []]
        if is_sole_trader:
            people.append(_ENSEIGNE_IN_NAME_RE.sub(" ", str(result.get("nom_complet") or "")))
        company_names = [*self._trade_names(result)]
        if not is_sole_trader:
            company_names += [str(result.get("nom_complet") or ""), str(result.get("nom_raison_sociale") or "")]
        if keyword.person is not None:
            first, last = keyword.person
            wanted = self._person_words(last) | self._person_words(first or "")
            return any(wanted <= self._person_words(person_name) for person_name in people)
        if keyword.is_email_domain:
            return any(re.sub(r"[^a-z0-9]", "", fold(name)) == keyword.text for name in company_names if name)
        from services.prospect_search.business_name import BusinessName

        business_words = BusinessName.distinctive_stems(context.company_name, town=context.city)
        word = BusinessName.distinctive_stems(keyword.text)
        name_words = [BusinessName.distinctive_stems(name) for name in company_names if name]
        is_named_with_its_words = any(word <= words <= business_words for words in name_words)
        is_named_after_its_holder = is_sole_trader and any(
            fold(keyword.text) == fold(str(d.get("nom") or "")) for d in result.get("dirigeants") or []
        )
        return is_named_with_its_words or is_named_after_its_holder

    @staticmethod
    def _activity_of(result: dict[str, Any]) -> str:
        """The main activity code a registry company declares, at its head office first."""
        return str((result.get("siege") or {}).get("activite_principale") or result.get("activite_principale") or "")

    @staticmethod
    def _person_words(name: str) -> set[str]:
        """The folded words of a person's name, a hyphenated name kept whole (« Exemple-Modèle »)."""
        return set(_PERSON_NAME_WORD_RE.findall(fold(name)))

    def parse_results(
        self,
        results: list[dict[str, Any]],
        context: ResolutionContext,
        *,
        department: str | None = None,
        is_trade_free_query: bool = False,
    ) -> list[NameCandidate]:
        """
        Score the registry matches (pure — unit-testable on fixtures); the company of the searched number is the business, whatever its name.

        Companies found by the name without its trade words must carry that name almost exactly: « Lb Passion »
        also finds LB TENNIS PASSION for a garden firm. A ceased company, or one registered in another
        département, is another business: a homonym, or the business's former structure. A property company
        (SCI) owns premises and runs no trade: « SCI DE L'EXEMPLE » is the landlord of « Garage de l'Exemple ».
        When one company bears the business's name exactly (« EXEMPLE 05 »), the others found by its words
        (« VENTE EXEMPLE 05 ») are other businesses.

        Args:
            results: The registry's answer.
            context: The business looked for.
            department: The business's département, when known (else read from its postal code).
            is_trade_free_query: Whether the registry was asked the name without its trade words.

        Returns:
            One candidate per company that can be the business.
        """
        candidates: list[NameCandidate] = []
        siren = self.siren_of(context.registry_number)
        department = department or FrenchDepartments.of_postal_code(context.postal_code)
        exact_name_results = [result for result in results[:5] if self._bears_the_exact_name(result, context)]
        for result in exact_name_results or results[:5]:
            anchored = bool(siren) and str(result.get("siren") or "") == siren
            company_department = FrenchDepartments.of_postal_code(
                str((result.get("siege") or {}).get("code_postal") or "")
            )
            is_in_department = department is not None and company_department == department
            is_elsewhere = department is not None and company_department is not None and not is_in_department
            is_ceased = str(result.get("etat_administratif") or "") == _CEASED_STATE
            if not anchored and (is_ceased or is_elsewhere or self._is_property_company(result)):
                continue
            if anchored:
                similarity = 1.0
            elif is_trade_free_query:
                similarity = self._trade_free_similarity(result, context)
            else:
                similarity = self._match_similarity(result, context)
            if similarity < _MIN_COMPANY_SIMILARITY:
                continue
            city_ok = anchored or self._city_matches(result, context)
            # Département-level match is enough geo confirmation: artisans are
            # often registered at home, one commune away from where they work.
            geo_confirmed = city_ok or is_in_department
            base = 0.5 + 0.25 * similarity + (0.15 if city_ok else 0.0)
            found = self._candidates_of(result, base=base, geo_confirmed=geo_confirmed)
            if anchored:
                found = [self._anchored(candidate) for candidate in found]
            candidates.extend(found)
        return candidates

    @staticmethod
    def _bears_the_exact_name(result: dict[str, Any], context: ResolutionContext) -> bool:
        """Whether a registry company bears the business's name word for word, as its legal name or a trade name."""
        from services.prospect_search.business_name import BusinessName

        names = [
            str(result.get("nom_raison_sociale") or ""),
            str(result.get("nom_complet") or ""),
            *RegistreGouvStrategy._trade_names(result),
        ]
        return any(BusinessName.is_exact_name(name, context.company_name) for name in names if name)

    @staticmethod
    def _is_property_company(result: dict[str, Any]) -> bool:
        """Whether a registry company is a property company (SCI and its kinds, legal categories 654x)."""
        return str(result.get("nature_juridique") or "").startswith(_PROPERTY_COMPANY_LEGAL_CATEGORY)

    def _candidates_of(self, result: dict[str, Any], *, base: float, geo_confirmed: bool) -> list[NameCandidate]:
        """The person a registry company names: the EI holder, its sole dirigeant, else its gérant/président."""
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
                return [self._candidate(first, last, min(0.95, base + 0.25), result, geo_confirmed)]
            return []

        if len(dirigeants) == 1:
            d = dirigeants[0]
            return [
                self._candidate(
                    title_case_name(d.get("prenoms")),
                    title_case_name(d.get("nom")),
                    min(0.9, base + 0.1),
                    result,
                    geo_confirmed,
                )
            ]
        # Ambiguous: prefer the gérant/président, scored under the
        # solo case (golden rule — when unsure, stay neutral).
        lead = next(
            (
                d
                for d in dirigeants
                if "gérant" in str(d.get("qualite") or "").lower() or "président" in str(d.get("qualite") or "").lower()
            ),
            None,
        )
        if lead is None:
            return []
        return [
            self._candidate(
                title_case_name(lead.get("prenoms")),
                title_case_name(lead.get("nom")),
                min(0.75, base),
                result,
                geo_confirmed,
            )
        ]

    @staticmethod
    def _anchored(candidate: NameCandidate) -> NameCandidate:
        """The candidate as read from the company the search tied to the business by its number."""
        return replace(
            candidate,
            anchored=True,
            confidence=max(candidate.confidence, 0.9),
            provenance=candidate.provenance.replace("localisation confirmée", "numéro relevé par la recherche"),
        )

    def _candidate(
        self,
        first: str | None,
        last: str | None,
        confidence: float,
        result: dict[str, Any],
        geo_confirmed: bool,
    ) -> NameCandidate:
        """Build a candidate carrying the matched SIREN for traceability."""
        # Registries may pack several first names (« Léo Jean Marc ») — keep the first.
        first_single = (first or "").split(" ")[0] or None
        geo_note = "localisation confirmée" if geo_confirmed else "localisation NON confirmée"
        return NameCandidate(
            first=first_single,
            last=last,
            gender=infer_gender(first_single),
            source=self.name,
            confidence=round(confidence, 2),
            primary=True,
            geo_confirmed=geo_confirmed,
            evidence_group=_GROUP_REGISTRY,
            provenance=(
                f"Registre officiel (SIRENE) : {result.get('nom_complet') or '?'}, "
                f"SIREN {result.get('siren') or '?'} — {geo_note}"
            ),
            raw={
                "siren": result.get("siren"),
                "nom_complet": result.get("nom_complet"),
                "siege_postal_code": str((result.get("siege") or {}).get("code_postal") or "") or None,
                # Declared main activity (NAF) — the activity guard compares it to
                # the prospect's trade to catch a same-town homonym in another line
                # of work (« Mayer Paysagiste » → a cleaning company).
                "activite": str((result.get("siege") or {}).get("activite_principale") or "") or None,
                "activite_label": (
                    str(
                        result.get("libelle_activite_principale")
                        or (result.get("siege") or {}).get("libelle_activite_principale")
                        or ""
                    )
                    or None
                ),
            },
        )

    @staticmethod
    def _match_similarity(result: dict[str, Any], context: ResolutionContext) -> float:
        """
        How surely a registry company is the business: its legal names close to the business's, or a trade name that is it.

        The business's name is read as written and as the registry files it (« ExempleAuto64 », « Exemple Auto 64 »).
        A trade name (« JULES MODELE (EXEMPLE AUTO 64) ») must be the business's name, not share its generic words:
        « HOME PRO SERVICES » is not « Exemple Home Services ».
        """
        from services.prospect_search.business_name import BusinessName

        business_names = {context.company_name, TradeName.searchable(context.company_name)}
        legal_names = [str(result.get("nom_complet") or ""), str(result.get("nom_raison_sociale") or "")]
        legal_similarity = max(
            company_similarity(join_dotted_initials(business_name), join_dotted_initials(legal_name))
            for business_name in business_names
            for legal_name in legal_names
        )
        is_trading_under_the_name = any(
            BusinessName.is_same_name(trade_name, business_name)
            for business_name in business_names
            for trade_name in RegistreGouvStrategy._trade_names(result)
        )
        return max(
            legal_similarity,
            1.0 if is_trading_under_the_name else 0.0,
            RegistreGouvStrategy._trade_free_similarity(result, context),
        )

    @staticmethod
    def _trade_names(result: dict[str, Any]) -> list[str]:
        """The trade names a registry company declares: in brackets after its name, and on its head office."""
        listed = [str(name) for name in ((result.get("siege") or {}).get("liste_enseignes") or []) if name]
        return [*RegistreGouvStrategy.names_in(str(result.get("nom_complet") or ""))[1:], *listed]

    @staticmethod
    def names_in(full_name: str) -> list[str]:
        """A registry full name and the trade names it carries in brackets (« JULES MODELE (EXEMPLE AUTO 64) »)."""
        return [full_name, *_ENSEIGNE_IN_NAME_RE.findall(full_name)]

    @staticmethod
    def _trade_free_similarity(result: dict[str, Any], context: ResolutionContext) -> float:
        """
        Similarity between the name without its trade words and the registry names, kept only when near exact.

        What is left is often one family name or a pair of initials, shared by every homonym of the town
        (« Exemple Auto » is EXEMPLE AUTO, « Martin » is not MARTIN PAUL).
        """
        trade_free_name = TradeName.without_trade_words(context.company_name)
        if not trade_free_name or trade_free_name == context.company_name:
            return 0.0
        names = [str(result.get("nom_complet") or ""), str(result.get("nom_raison_sociale") or "")]
        similarity = max(
            company_similarity(join_dotted_initials(trade_free_name), join_dotted_initials(n)) for n in names
        )
        return similarity if similarity >= _MIN_TRADE_FREE_SIMILARITY else 0.0

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
            # The query itself filters on code_postal when the prospect has one,
            # so returned matches are geo-scoped by construction.
            geo_confirmed = bool(context.postal_code) or self._department_matches(result, context)
            confidence = min(0.9, 0.55 + 0.25 * similarity + (0.1 if len(representants) == 1 else 0.0))
            geo_note = "localisation confirmée" if geo_confirmed else "localisation NON confirmée"
            candidates.append(
                NameCandidate(
                    first=first,
                    last=last,
                    gender=infer_gender(first),
                    source=self.name,
                    confidence=round(confidence, 2),
                    primary=True,
                    geo_confirmed=geo_confirmed,
                    evidence_group=_GROUP_REGISTRY,
                    provenance=(
                        f"Pappers : {result.get('nom_entreprise') or '?'}, "
                        f"SIREN {result.get('siren') or '?'} — {geo_note}"
                    ),
                    raw={
                        "siren": result.get("siren"),
                        "siege_postal_code": str((result.get("siege") or {}).get("code_postal") or "") or None,
                        # Declared activity (NAF) for the activity guard — same role as
                        # the registre_gouv candidate; best-effort across Pappers shapes.
                        "activite": (
                            str(result.get("code_naf") or (result.get("siege") or {}).get("code_naf") or "") or None
                        ),
                    },
                )
            )
        return candidates

    @staticmethod
    def _department_matches(result: dict[str, Any], context: ResolutionContext) -> bool:
        """True when the Pappers HQ sits in the prospect's département."""
        siege = result.get("siege") or {}
        siege_postal = str(siege.get("code_postal") or "")
        if not context.postal_code or len(siege_postal) != 5:
            return False
        return siege_postal[:2] == context.postal_code[:2]


class WebRegistryStrategy:
    """Tier 1ter — recover the hidden legal name via a web search, then resolve
    its director through the official registry.

    The registry can't be matched on the prospect's TRADE name when it differs
    from the registered one (« Germain Paysagiste » → « SECOMAN GERMAIN »). A web
    search on « enseigne + ville » surfaces that legal name the way directories
    print it, which is handed back to :class:`RegistreGouvStrategy` — this time it
    matches, and the SIRENE dirigeant comes out reliably. HTTP-only (Bright Data
    Web Unlocker), so it runs on the datacenter VPS as well as the desktop.

    Clean no-op when Bright Data is not configured.
    """

    name = "web_registry"

    #: Cap on legal-name candidates handed to the registry (keeps the fan-out sane).
    _MAX_LEGAL_NAMES = 6

    #: An all-caps run of 2..4 words — how a directory prints a raison sociale.
    #: Explicit uppercase set (a Latin-1 range would also swallow accented
    #: LOWERCASE), no digits (so it stops at the street number after the name).
    _UPPER = "A-ZÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸ"
    _CAPS_NAME_RE = re.compile(rf"[{_UPPER}][{_UPPER}&'’\-]*(?:\s+[{_UPPER}&'’\-]+){{1,3}}")

    def __init__(self, registry: RegistreGouvStrategy | None = None, client: Any | None = None) -> None:
        """Wire the registry delegate and the Bright Data client (both injectable for tests)."""
        self._registry = registry or RegistreGouvStrategy()
        if client is not None:
            self._client = client
        else:
            from scrappers.brightdata_client import BrightDataClient

            self._client = BrightDataClient()

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Search the web for the legal name(s), then resolve each via the registry."""
        enseigne = (context.company_name or "").strip()
        if not enseigne or not getattr(self._client, "is_configured", False):
            return []
        # A long exact trade name makes Google over-filter (« Germain Paysagiste
        # Élagage Espaces Verts » returns nothing); the first couple of words +
        # city mirror a human search and recall the directory listings.
        query_terms = " ".join(enseigne.split()[:2])
        query = f"{query_terms} {context.city or ''}".strip()
        try:
            html = await self._client.google(query, num=20)
        except Exception as exc:
            logger.warning("web_registry SERP failed for %r: %s", query, exc)
            return []
        legal_names = self.extract_company_names(html, enseigne)
        if not legal_names:
            return []
        # Each sub-context carries the RECOVERED legal name, so the registry's own
        # similarity check compares legal-name↔registry, not the unmatchable trade name.
        subs = [replace(context, company_name=name) for name in legal_names]
        results = await asyncio.gather(*(self._registry.resolve(sub) for sub in subs), return_exceptions=True)
        candidates: list[NameCandidate] = []
        for result in results:
            if isinstance(result, BaseException):
                logger.warning("web_registry registry sub-lookup raised: %s", result)
                continue
            candidates.extend(candidate for candidate in result if self.is_company_of(candidate, context))
        return self._retag(candidates)

    @staticmethod
    def is_company_of(candidate: NameCandidate, context: ResolutionContext) -> bool:
        """
        Whether the registry company a web search led to is the business itself (pure — testable).

        A legal name found on the web shares a word with the trade name, which a neighbour's does too
        (« EXEMPLE HOME RENOV » for « Exemple Home Services »): the company must bear the trade name word for word,
        or its head must be the person the trade name is named after (« Germain Paysagiste » is SECOMAN Germain),
        in the same trade: « Exemple des Jardins » is not the painter of the Exemple family.

        Args:
            candidate: The head of a company the registry gave for a legal name found on the web.
            context: The business looked for.

        Returns:
            True when the company is the business.
        """
        from services.prospect_search.business_name import BusinessName
        from services.trade_normalizer import TradeNormalizer

        business_names = {context.company_name, TradeName.searchable(context.company_name)}
        company_names = RegistreGouvStrategy.names_in(str(candidate.raw.get("nom_complet") or ""))
        if any(
            BusinessName.is_same_name(company_name, business_name)
            for company_name in company_names
            for business_name in business_names
        ):
            return True
        person_words = {fold(word) for word in f"{candidate.first or ''} {candidate.last or ''}".split()}
        is_named_after_its_head = any(
            person_words & BusinessName.distinctive_words(name, town=context.city) for name in business_names
        )
        trade = TradeNormalizer.normalize(context.trade)
        return is_named_after_its_head and activity_consistency(trade, candidate.raw.get("activite")) is not False

    def extract_company_names(self, html: str, enseigne: str) -> list[str]:
        """Pull raison-sociale candidates from a SERP (pure — testable on fixtures).

        Keeps the all-caps runs that share a distinctive word with the trade
        name (the artisan's own name is almost always in both), which filters out
        the city, generic UI words and the other firms of the same trade (« AB
        ÉLECTRICITÉ » shares only its trade with « ABS électricité »), and returns
        the longest spelling of each.
        """
        from services.prospect_search.business_name import BusinessName

        text = unescape(re.sub(r"<[^>]+>", " ", html or ""))
        enseigne_words = BusinessName.distinctive_words(enseigne) | BusinessName.distinctive_words(
            TradeName.searchable(enseigne)
        )
        if not enseigne_words:
            return []
        found: dict[str, str] = {}
        for match in self._CAPS_NAME_RE.finditer(text):
            # Drop single-letter words (initials / SERP artefacts like a trailing « P »).
            words = [word for word in re.split(r"\s+", match.group(0)) if len(word) > 1]
            candidate = " ".join(words).strip(" -'’&")
            if len(words) < 2 or not (BusinessName.distinctive_words(candidate) & enseigne_words):
                continue
            key = fold(candidate)
            if key not in found or len(candidate) > len(found[key]):
                found[key] = candidate
        return sorted(found.values(), key=len, reverse=True)[: self._MAX_LEGAL_NAMES]

    @staticmethod
    def _retag(candidates: list[NameCandidate]) -> list[NameCandidate]:
        """Re-label the registry hits as web-sourced, deduped by identity."""
        best_by_identity: dict[str, NameCandidate] = {}
        for candidate in candidates:
            if not candidate.has_name:
                continue
            key = candidate.identity_key()
            current = best_by_identity.get(key)
            if current is None or candidate.confidence > current.confidence:
                best_by_identity[key] = candidate
        return [
            NameCandidate(
                first=candidate.first,
                last=candidate.last,
                gender=candidate.gender,
                source="web_registry",
                confidence=candidate.confidence,
                primary=candidate.primary,
                geo_confirmed=candidate.geo_confirmed,
                evidence_group=candidate.evidence_group,
                provenance=f"Recherche web → {candidate.provenance}",
                raw=candidate.raw,
            )
            for candidate in best_by_identity.values()
        ]


# « Réponse du propriétaire » signatures: a line/dash followed by a short name.
_OWNER_SIGNATURE_RE = re.compile(
    r"(?:^|[\n\-—–])\s*(?:cordialement|merci|à bientôt)?[,\s]*([A-ZÀ-Ü][a-zà-ü]{2,15})\s*$",
    re.MULTILINE,
)
_CLOSING_WORDS: frozenset[str] = frozenset(
    {
        "cordialement",
        "merci",
        "salutations",
        "amicalement",
        "sincerement",
        "bonne",
        "belle",
        "excellente",
        "bien",
        "equipe",
        "team",
        "direction",
        "gerant",
        "gerance",
    }
)
_NAME_LINK_WORDS: frozenset[str] = frozenset(
    {"de", "des", "du", "et", "la", "le", "les", "au", "aux", "en", "sur", "chez", "fils", "freres", "jr", "of", "and"}
)
_PERSON_CUE_BEFORE_NAME = r"\b(?:[Vv]oir|[Mm]erci(?:\s+à)?|[Aa]vec|[Dd]emandez|[Aa]ppelez|[Cc]ontactez)"
_ADDRESSING_CUE_RE = r"\b(?:merci|bonjour|bonsoir|cher|chere|salut|hello|thanks?)\b"
_MIN_NAME_WORD_CHARS = 3


class OwnerResponseStrategy:
    """Tier 2 — signatures in Google « réponse du propriétaire » texts.

    Uses only text already captured by the enrichment scraper (no network).
    A recurring signature (« … à bientôt ! — Léo ») is a decent first-name
    signal, scored moderately; a word no one is given as a first name
    (« Avatacar », the booking platform answering for the garage) is no person.
    """

    name = "owner_response"

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Extract recurring signatures from owner responses."""
        counts: dict[str, int] = {}
        for text in context.owner_responses:
            for match in _OWNER_SIGNATURE_RE.finditer(text or ""):
                name = title_case_name(match.group(1))
                if name and fold(name) not in _CLOSING_WORDS and GivenNames.is_given_name(name.split()[0]):
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
                primary=False,
                evidence_group=_GROUP_SCRAPED_TEXT,
                provenance=(
                    f"Signature « {best} » dans {seen} réponse{'s' if seen > 1 else ''} du propriétaire aux avis Google"
                ),
                raw={"occurrences": seen},
            )
        ]


class BusinessNameOwnerStrategy:
    """Supporting — the owner named in the business's own name, when customers call him by that first name.

    « Garage Jules Exemple » with reviews saying « je vais voir Jules pour réparer ma voiture »: Jules is
    the first name and Exemple the last name of the person behind the business. Never a primary source,
    so a proposal at best.
    """

    name = "business_name"

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Find the pair of name words customers call the owner by."""
        return self.candidates_of(context)

    def candidates_of(self, context: ResolutionContext) -> list[NameCandidate]:
        """
        The owner a business name spells, when customers address him by its first word (pure — testable).

        Both words are capitalized name words of the business name (not « des », « Fils », « JANTES ALU »),
        the business name holds more than them (« Modèle Jules » does not tell which is the first name),
        and a review calls the first one as a person: « voir Jules », « merci à Jules », never « chez Otobox ».
        """
        company_words = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", context.company_name or "")
        if all(self._is_name_word(word) for word in company_words):
            return []
        customer_texts = [text for text in [*context.review_texts, *context.owner_responses] if text]
        for first, last in pairwise(company_words):
            if not (self._is_name_word(first) and self._is_name_word(last)):
                continue
            addressed = re.compile(rf"{_PERSON_CUE_BEFORE_NAME}\s+{re.escape(first)}\b(?!\s+{re.escape(last)}\b)")
            mentions = sum(1 for text in customer_texts if addressed.search(text))
            if mentions:
                first_name, last_name = title_case_name(first), title_case_name(last)
                return [
                    NameCandidate(
                        first=first_name,
                        last=last_name,
                        gender=infer_gender(first_name),
                        source=self.name,
                        confidence=0.6,
                        primary=False,
                        evidence_group=_GROUP_CUSTOMER_REVIEWS,
                        provenance=(
                            f"Nom de l'entreprise « {context.company_name} », et les clients l'appellent « {first_name} »"
                            f" dans {mentions} avis"
                        ),
                        raw={"mentions": mentions},
                    )
                ]
        return []

    @staticmethod
    def _is_name_word(word: str) -> bool:
        """Whether a word of the business name can be a first or last name: capitalized, not a trade or link word."""
        parts = [part for part in re.split(r"[-']", word) if part]
        is_capitalized = bool(parts) and all(part[:1].isupper() and part[1:] == part[1:].lower() for part in parts)
        folded = fold(word)
        return (
            is_capitalized
            and len(word) >= _MIN_NAME_WORD_CHARS
            and folded not in _TRADE_AND_LEGAL_FORM_WORDS
            and folded not in _NAME_LINK_WORDS
        )


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
            declaration = re.sub(r"\s+", " ", match.group(0)).strip()
            return [
                NameCandidate(
                    first=first,
                    last=last,
                    gender=infer_gender(first),
                    source=self.name,
                    confidence=0.75,
                    primary=False,
                    evidence_group=_GROUP_WEBSITE,
                    provenance=f"Mentions légales du site : « {declaration[:120]} »",
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

    @staticmethod
    def _is_addressed_in(quote: str, name: str) -> bool:
        """
        Whether the quote addresses the person rather than names its head (« Merci beaucoup Jules pour ton avis »).

        The owner's replies thank or greet the customer who wrote the review: that name is a customer's.

        Args:
            quote: The extract the model quoted.
            name: The first name (else the last name) it read there.

        Returns:
            True when a thanking or greeting word comes just before the name.
        """
        if not name:
            return False
        addressed_name_re = rf"{_ADDRESSING_CUE_RE}[^.!?\n]{{0,30}}\b{re.escape(fold(name))}\b"
        return re.search(addressed_name_re, fold(quote)) is not None

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

        if fold(quote)[:60] not in fold(corpus) or self._is_addressed_in(quote, first or last or ""):
            return []
        return [
            NameCandidate(
                first=first,
                last=last,
                gender=infer_gender(first),
                source=self.name,
                confidence=0.6,
                primary=False,
                evidence_group=_GROUP_SCRAPED_TEXT,
                provenance=f"IA sur le texte public — citation : « {quote[:120]} »",
                raw={"quote": quote[:200]},
            )
        ]


class RbqOfficerStrategy:
    """Primary — the officer the Québec licence registry (RBQ) names for the business's own licence.

    The licence was tied to the business by its name and its town when the business was enriched, so its
    officer is the head: the one answering for the administration and the management of the business.
    """

    name = "registre_rbq"

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Read the officers of the business's licence in the registry."""
        if not context.licence_number:
            return []
        from services.professional_license_service import RbqLicenseRegistryClient

        officers = await RbqLicenseRegistryClient().officers_of(context.licence_number)
        return self.candidates_of(officers or [], licence_number=context.licence_number)

    def candidates_of(self, officers: list[RbqLicenceOfficer], *, licence_number: str) -> list[NameCandidate]:
        """
        The head among a licence's officers (pure — testable).

        The officer answering for the administration and the management runs the business; several such
        officers, or none, leave each one a proposal, the first ahead.

        Args:
            officers: The officers the registry names for the licence.
            licence_number: The licence number, quoted in the provenance.

        Returns:
            One candidate per officer running the business.
        """
        running = [officer for officer in officers if officer.runs_the_business] or officers
        is_sole_head = len(running) == 1
        candidates: list[NameCandidate] = []
        for rank, officer in enumerate(running):
            first = (title_case_name(officer.first_name) or "").split(" ")[0] or None
            candidates.append(
                NameCandidate(
                    first=first,
                    last=title_case_name(officer.last_name),
                    gender=infer_gender(first),
                    source=self.name,
                    confidence=0.9 if is_sole_head else (0.75 if rank == 0 else 0.6),
                    primary=True,
                    geo_confirmed=True,
                    evidence_group=_GROUP_REGISTRY,
                    provenance=f"Registre des licences RBQ : licence {licence_number}, dirigeant",
                    anchored=is_sole_head,
                )
            )
        return candidates
