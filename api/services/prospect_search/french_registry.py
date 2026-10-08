"""
French company register — whether a French business a search found is still open, as the official registry says.

A garage struck off last spring keeps its Google listing for months. The registry (recherche-entreprises) is read only
for a candidate about to be proposed: the companies of its name in its département, at its address.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from typing import Any

from services.decision_maker.normalize import town_key
from services.prospect_search.business_name import BusinessName
from services.prospect_search.candidate_facts import CandidateFacts

_RESULTS_PER_PAGE: int = 10
_CEASED_STATE: str = "C"
_ACTIVE_STATE: str = "A"
_POSTAL_CODE_RE: re.Pattern[str] = re.compile(r"\b(\d{5})\b")
_BRACKETS_RE: re.Pattern[str] = re.compile(r"\([^)]*\)")
_RECENT_CLOSING: timedelta = timedelta(days=3 * 365)
_REGISTER_SOURCE: str = "Registre des entreprises (INSEE)"


class FrenchRegistry:
    """Reads the French company registry for the closing of a French business."""

    async def read_closing(self, facts: CandidateFacts) -> None:
        """
        Take the registry's recent closing of the business's company as the closing of the business.

        Only a company of the business's name (its legal name or a trade name it declared) at the business's place
        (its postal code, else its town) counts. An open one there clears the business; so does an open company of
        its name elsewhere in the département, or of its trade at its street address, run by the same person (a sole
        trader turned into a company, the seat moved to the owner's home); otherwise one closed less than three
        years ago closes it, a newcomer at the address being another business.

        Args:
            facts: The candidate, completed in place.
        """
        if facts.country != "FR" or facts.is_closed or not facts.name:
            return
        from services.decision_maker.french_departments import FrenchDepartments

        postal_code = self.postal_code_of(facts.address)
        department = FrenchDepartments.of_postal_code(postal_code) or await FrenchDepartments.of_town(facts.town)
        if not department:
            return
        named: dict[str, dict[str, Any]] = {}
        for query in await self._queries(facts):
            for company in await self._companies(query, department=department):
                if self.is_named_like_the_business(company, facts):
                    named.setdefault(str(company.get("siren") or len(named)), company)
            if any(self.is_at_place(company, facts, postal_code=postal_code) for company in named.values()):
                break
        await self._read_closing_of(facts, list(named.values()), department=department, postal_code=postal_code)

    async def _read_closing_of(
        self, facts: CandidateFacts, named: list[dict[str, Any]], *, department: str, postal_code: str | None
    ) -> None:
        """Close the business when the companies of its name at its place all ceased, one lately, and nobody went on."""
        here = [company for company in named if self.is_at_place(company, facts, postal_code=postal_code)]
        if not here or any(company.get("etat_administratif") == _ACTIVE_STATE for company in here):
            return
        closed_on = max((closing for company in here if (closing := self.closing_date(company))), default=None)
        if closed_on is None or datetime.now(UTC).date() - closed_on > _RECENT_CLOSING:
            return
        heads = {person for company in here for person in self.heads_of(company)}
        if any(
            company.get("etat_administratif") == _ACTIVE_STATE and heads & self.heads_of(company) for company in named
        ):
            return
        if await self._is_carried_on(facts, heads, department=department, postal_code=postal_code):
            return
        facts.is_closed = True
        facts.add_evidence("closed", f"cessée le {closed_on:%d/%m/%Y}", source=_REGISTER_SOURCE)

    @staticmethod
    async def _queries(facts: CandidateFacts) -> list[str]:
        """
        The spellings of the name the registry may file the business under: as written, then without its trade words
        (« Garage Exemple Auto 46 » as « Exemple Auto 46 »), then without the communes it names (« Exemple-Auto
        Pau-Lescar » as « Exemple Auto »).
        """
        from services.decision_maker.french_departments import FrenchDepartments
        from services.decision_maker.strategies import TradeName

        name = BusinessName.without_legal_form(facts.name)
        place_free_words = [
            word
            for word in re.findall(r"[^\s-]+", name)
            if town_key(word) != town_key(facts.town) and not await FrenchDepartments.is_town_name(word)
        ]
        spellings = [name, TradeName.searchable(name), TradeName.without_trade_words(name), " ".join(place_free_words)]
        return list(dict.fromkeys(spelling for spelling in spellings if spelling.strip()))

    @staticmethod
    def postal_code_of(address: str | None) -> str | None:
        """The French postal code an address holds, if any."""
        match = _POSTAL_CODE_RE.search(address or "")
        return match.group(1) if match else None

    @staticmethod
    def is_named_like_the_business(company: dict[str, Any], facts: CandidateFacts) -> bool:
        """Whether one of a registry company's names (its legal name, a trade name it declared) is the business's."""
        from services.decision_maker.strategies import RegistreGouvStrategy

        siege = company.get("siege") or {}
        names = [
            *RegistreGouvStrategy.names_in(str(company.get("nom_complet") or "")),
            *(str(trade_name) for trade_name in siege.get("liste_enseignes") or []),
        ]
        return any(BusinessName.is_named_like(name, facts.name, town=facts.town) for name in names if name)

    @staticmethod
    def is_at_place(company: dict[str, Any], facts: CandidateFacts, *, postal_code: str | None) -> bool:
        """Whether a registry company sits at the business's postal code, else in its town (pure — testable)."""
        siege = company.get("siege") or {}
        if postal_code:
            return str(siege.get("code_postal") or "") == postal_code
        town = town_key(facts.town)
        return bool(town) and town_key(str(siege.get("libelle_commune") or "")) == town

    @staticmethod
    def closing_date(company: dict[str, Any]) -> date | None:
        """When a ceased company closed, as the registry dates it; None for an open one or an undated closing."""
        if company.get("etat_administratif") != _CEASED_STATE:
            return None
        closed_on = str(company.get("date_fermeture") or (company.get("siege") or {}).get("date_fermeture") or "")
        return date.fromisoformat(closed_on) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", closed_on) else None

    async def _is_carried_on(
        self, facts: CandidateFacts, heads: set[str], *, department: str, postal_code: str | None
    ) -> bool:
        """
        Whether the person who ran the closed company runs a company of the trade open at the business's street
        address: a sole trader turned into a company carries the business on, a newcomer at the address does not.
        """
        from services.decision_maker.activity import activity_codes_of, has_known_activity
        from services.decision_maker.strategies import RegistreGouvStrategy
        from services.decision_maker.types import ResolutionContext
        from services.trade_normalizer import TradeNormalizer

        street = RegistreGouvStrategy.street_of(facts.address)
        trade = TradeNormalizer.normalize(facts.trade_key)
        if street is None or not heads or not has_known_activity(trade):
            return False
        context = ResolutionContext(company_name=facts.name, city=facts.town, postal_code=postal_code)
        companies = await self._companies(street, department=department, activity_codes=activity_codes_of(trade))
        return any(
            RegistreGouvStrategy.has_establishment_at(company, street, context=context, trade=trade)
            and heads & self.heads_of(company)
            for company in companies
        )

    @staticmethod
    def heads_of(company: dict[str, Any]) -> set[str]:
        """
        The people who run a registry company, as « last name|first name » keys: a liquidator runs nothing, and the
        name of use the registry adds in brackets (« EXEMPLE (EXEMPLE) ») is left out.
        """
        from services.decision_maker.normalize import fold

        return {
            f"{fold(_BRACKETS_RE.sub('', str(head.get('nom') or ''))).strip()}|"
            f"{fold(str(head.get('prenoms') or '')).split(' ')[0]}"
            for head in company.get("dirigeants") or []
            if head.get("nom") and "liquidat" not in fold(str(head.get("qualite") or ""))
        }

    @staticmethod
    async def _companies(
        query: str, *, department: str, activity_codes: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """The registry's companies for a query in a département, closed ones included; empty when it does not answer."""
        from services.decision_maker.strategies import RegistreGouvStrategy

        companies = await RegistreGouvStrategy.search(
            query, department=department, per_page=_RESULTS_PER_PAGE, activity_codes=activity_codes
        )
        return companies or []


french_registry = FrenchRegistry()
