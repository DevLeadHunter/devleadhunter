"""
French company register — whether a French business a search found is still open, as the official registry says.

A garage struck off last spring keeps its Google listing for months. The registry (recherche-entreprises) is read only
for a candidate about to be proposed: the companies of its name in its département, at its address. The one open
company of its name at its place gives it its SIREN: two listings of a search with the same SIREN are one business.
Its seat gives a street address without postal code the postal code and town it lacks.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import unquote

from services.decision_maker.french_departments import FrenchDepartments
from services.decision_maker.normalize import company_tokens, fold, town_key
from services.prospect_search.business_name import BusinessName
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.place_of_contact import PlaceOfContact

_RESULTS_PER_PAGE: int = 10
_CEASED_STATE: str = "C"
_ACTIVE_STATE: str = "A"
_POSTAL_CODE_RE: re.Pattern[str] = re.compile(r"\b(\d{5})\b")
_BRACKETS_RE: re.Pattern[str] = re.compile(r"\([^)]*\)")
_RECENT_CLOSING: timedelta = timedelta(days=3 * 365)
_REGISTER_SOURCE: str = "Registre des entreprises (INSEE)"
# The legal forms of associations start with 92 (« 9220 » : association déclarée).
_ASSOCIATION_LEGAL_FORM_PREFIX: str = "92"
# A word of the business's name an association must carry: initials and link words say nothing.
_ASSOCIATION_NAME_WORD_MIN_CHARS: int = 3
_CLUB_WORDS: frozenset[str] = frozenset(
    {"association", "asso", "club", "sportif", "sportive", "amicale", "comite", "federation"}
)


class FrenchRegistry:
    """Reads the French company registry for the closing of a French business."""

    async def read_closing(self, facts: CandidateFacts) -> None:
        """
        Take the registry's recent closing of the business's company as its closing, with its SIREN and postal code.

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
        postal_code = self.postal_code_of(facts.address)
        department = FrenchDepartments.of_postal_code(postal_code) or await FrenchDepartments.of_town(facts.town)
        if not department:
            return
        named: dict[str, dict[str, Any]] = {}
        found: dict[str, dict[str, Any]] = {}
        for query in await self._queries(facts):
            for company in await self._companies(query, department=department):
                found.setdefault(str(company.get("siren") or len(found)), company)
                if self.is_named_like_the_business(company, facts):
                    named.setdefault(str(company.get("siren") or len(named)), company)
            if any(self.is_at_place(company, facts, postal_code=postal_code) for company in named.values()):
                break
        await self.place_listing_without_address(facts, list(named.values()))
        self.take_registry_number(facts, list(named.values()), postal_code=postal_code)
        self.complete_address(facts, list(named.values()))
        self.note_association(facts, list(found.values()))
        self.note_registered_activity(facts, list(named.values()))
        await self._read_closing_of(facts, list(named.values()), department=department, postal_code=postal_code)

    @classmethod
    async def place_listing_without_address(cls, facts: CandidateFacts, named: list[dict[str, Any]]) -> None:
        """
        Give a listing without address nor town the commune of the one open company of its exact name in its département.

        The search placed it in the town it searched; the registry tells where it is (« La petite Maçonnerie »
        found from Reims is in « 51370 Les Mesneux »). Only the postal code and the commune are taken: a sole
        trader's seat is often their home.

        Args:
            facts: The candidate, completed in place.
            named: The registry companies named like the business.
        """
        if facts.address or facts.city is not None:
            return
        carrying_its_name = [
            company
            for company in named
            if company.get("etat_administratif") == _ACTIVE_STATE and cls._carries_exact_name(company, facts)
        ]
        if len(carrying_its_name) != 1:
            return
        siege = carrying_its_name[0].get("siege") or {}
        postal_code = str(siege.get("code_postal") or "")
        commune = str(siege.get("libelle_commune") or "").strip()
        if not _POSTAL_CODE_RE.fullmatch(postal_code) or not commune:
            return
        facts.city = await FrenchDepartments.commune_name(commune)
        facts.address = f"{postal_code} {facts.city}"
        facts.add_evidence("address", facts.address, source=_REGISTER_SOURCE)

    @staticmethod
    def note_association(facts: CandidateFacts, companies: list[dict[str, Any]]) -> None:
        """
        Note the business as an association when the registry and its own words both say so.

        Every open company of the département carrying the words of its name must be an association (« Ass sportive
        Gazelec Gardois football » for « Gazelec S. Gardois »), and its name or its Facebook page's must say a club
        (« Nîmes Gazelec Sportif Gardois »): a community garden association named like a landscaper says nothing of
        the landscaper.

        Args:
            facts: The candidate, completed in place.
            companies: The registry companies its name brought back in its département.
        """
        name_words = {
            word
            for word in company_tokens(BusinessName.without_legal_form(facts.name))
            if len(word) >= _ASSOCIATION_NAME_WORD_MIN_CHARS
        }
        open_companies = [
            company
            for company in companies
            if company.get("etat_administratif") == _ACTIVE_STATE
            and name_words <= company_tokens(str(company.get("nom_complet") or ""))
        ]
        are_associations = (
            bool(name_words)
            and bool(open_companies)
            and all(
                str(company.get("nature_juridique") or "").startswith(_ASSOCIATION_LEGAL_FORM_PREFIX)
                for company in open_companies
            )
        )
        own_names = [facts.name, *map(PlaceOfContact.facebook_page_name, PlaceOfContact.facebook_addresses_of(facts))]
        says_a_club = any(
            word in _CLUB_WORDS for name in own_names for word in re.split(r"[^a-z]+", fold(unquote(name)))
        )
        if are_associations and says_a_club:
            facts.add_evidence("association", str(open_companies[0].get("nom_complet") or ""), source=_REGISTER_SOURCE)

    @classmethod
    def note_registered_activity(cls, facts: CandidateFacts, named: list[dict[str, Any]]) -> None:
        """
        Note the activity of another trade the one open company of the business's exact name declares.

        « Au Jardin de l'Exemple », a landscaper on Google, is filed as a greengrocer (« 52.2A »): the listing may be
        the shop's, a person checks it. An activity close to the trade (earthworks for a landscaper) says nothing.

        Args:
            facts: The candidate, completed in place.
            named: The registry companies named like the business.
        """
        from services.decision_maker.activity import activity_consistency
        from services.trade_normalizer import TradeNormalizer

        carrying_its_name = [
            company
            for company in named
            if company.get("etat_administratif") == _ACTIVE_STATE and cls._carries_exact_name(company, facts)
        ]
        if len(carrying_its_name) != 1:
            return
        company = carrying_its_name[0]
        siege = company.get("siege") or {}
        activity = str(siege.get("activite_principale") or company.get("activite_principale") or "")
        if activity_consistency(TradeNormalizer.normalize(facts.trade_key), activity) is not False:
            return
        facts.add_evidence(
            "registered_activity",
            activity,
            source=_REGISTER_SOURCE,
            snippet=str(company.get("nom_complet") or ""),
        )

    @staticmethod
    def _carries_exact_name(company: dict[str, Any], facts: CandidateFacts) -> bool:
        """Whether one of a registry company's names is the business's, word for word, legal forms aside."""
        from services.decision_maker.strategies import RegistreGouvStrategy

        siege = company.get("siege") or {}
        names = [
            *RegistreGouvStrategy.names_in(str(company.get("nom_complet") or "")),
            *(str(trade_name) for trade_name in siege.get("liste_enseignes") or []),
        ]
        own_words = company_tokens(BusinessName.without_legal_form(facts.name))
        return bool(own_words) and any(
            company_tokens(BusinessName.without_legal_form(name)) == own_words for name in names if name
        )

    @classmethod
    def complete_address(cls, facts: CandidateFacts, named: list[dict[str, Any]]) -> None:
        """
        Give a street address without postal code the postal code and town of the business's company seated there.

        The company must be open, of the business's name, in its town and at the same number and street (« 12 Rue
        Exemple » becomes « 12 Rue Exemple, 03100 Montluçon »).

        Args:
            facts: The candidate, completed in place.
            named: The registry companies named like the business.
        """
        from services.decision_maker.strategies import RegistreGouvStrategy

        street = RegistreGouvStrategy.street_of(facts.address)
        if street is None or cls.postal_code_of(facts.address) is not None:
            return
        for company in named:
            siege = company.get("siege") or {}
            seat_postal_code = str(siege.get("code_postal") or "")
            is_seated_at_street = (
                company.get("etat_administratif") == _ACTIVE_STATE
                and cls.is_at_place(company, facts, postal_code=None)
                and RegistreGouvStrategy.street_of(str(siege.get("adresse") or "")) == street
            )
            if is_seated_at_street and _POSTAL_CODE_RE.fullmatch(seat_postal_code):
                facts.address = f"{facts.address}, {seat_postal_code} {facts.town}"
                facts.city = facts.city or facts.town
                facts.add_evidence("address", facts.address, source=_REGISTER_SOURCE)
                return

    @classmethod
    def take_registry_number(
        cls, facts: CandidateFacts, named: list[dict[str, Any]], *, postal_code: str | None
    ) -> None:
        """
        Give the business the SIREN of the one open company of its name at its place.

        Several open companies there, or none, leave it without: a wrong number would merge two businesses.

        Args:
            facts: The candidate, completed in place.
            named: The registry companies named like the business.
            postal_code: The business's postal code, if its address gives one.
        """
        if facts.registry_number:
            return
        sirens = {
            str(company["siren"])
            for company in named
            if company.get("siren")
            and company.get("etat_administratif") == _ACTIVE_STATE
            and cls.is_at_place(company, facts, postal_code=postal_code)
        }
        if len(sirens) == 1:
            facts.registry_number = sirens.pop()
            facts.add_evidence("registry", facts.registry_number, source=_REGISTER_SOURCE)

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
