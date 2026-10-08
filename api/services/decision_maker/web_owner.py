"""
The owner the web names for a business: on the head's own profile, on the business's page, or on a page about it.

Google's results for the business name and « propriétaire » show it the way people write it: « Marc Exemple -
Propriétaire chez Exemple Paysage » (a LinkedIn profile), « propriétaire at Garage Exemple » (a Facebook profile),
« Cordialement, Alain Exemple Propriétaire Modèle A.E » (the business's page), « grâce à son propriétaire Luc
Exemple » (a page about it). A person counts only when the result ties them to this business, by its name or its
phone, and in its town when the result says where; never a former owner, nor one of several owners.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from services.decision_maker.given_names import GivenNames
from services.decision_maker.normalize import (
    company_tokens,
    fold,
    infer_gender,
    initials_in,
    join_dotted_initials,
    title_case_name,
    town_key,
)
from services.decision_maker.types import NameCandidate, ResolutionContext

logger = logging.getLogger(__name__)

_EVIDENCE_GROUP: str = "web_owner"
_SEARCHES: int = 3
_SEARCH_RETRY_PAUSE_SECONDS: float = 5.0
_SELF_DECLARED_CONFIDENCE: float = 0.75
_REPORTED_CONFIDENCE: float = 0.65
_INITIALS_BONUS: float = 0.1
_MAX_CONFIDENCE: float = 0.9
_MIN_KEY_WORD_CHARS: int = 4
_PHONE_DIGITS_COMPARED: int = 9
_CONTEXT_BEFORE_ROLE_CHARS: int = 120
_MAX_EXCERPT_CHARS: int = 120
_ROLE: str = (
    r"(?i:propri[ée]taire|proprio|fondat(?:eur|rice)|cr[ée]at(?:eur|rice)|pr[ée]sident(?:e)?|g[ée]rante?|owner|founder)"
)
_NAME_WORD: str = r"[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+(?:-[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+)?"
_PERSON: str = rf"{_NAME_WORD}(?:\s+{_NAME_WORD}){{1,2}}"
_TITLE_ROLE_RE: re.Pattern[str] = re.compile(rf"^(?P<person>{_PERSON})\s*[-–—|·,]\s*(?P<role>{_ROLE})\b(?P<after>.*)$")
_PROFILE_ROLE_RE: re.Pattern[str] = re.compile(
    rf"(?P<role>{_ROLE})\s+(?i:at|chez|à|de|du|of|@)\s+(?P<after>[^;·|\n.!?…]+)"
)
_SIGNED_ROLE_RE: re.Pattern[str] = re.compile(
    rf"(?P<person>{_PERSON}),?\s+(?:(?i:le|la)\s+)?(?P<role>{_ROLE})\b(?P<after>[^|\n]{{0,100}})"
)
_ROLE_THEN_PERSON_RE: re.Pattern[str] = re.compile(
    rf"(?P<role>{_ROLE})(?P<plural>s)?\b\s*[,:]?\s*(?:(?i:est|is)\s+)?"
    rf"(?:(?i:m\.|mme|monsieur|madame|mr\.?)\s+)?(?P<person>{_PERSON})"
)
_NOT_THE_OWNER_BEFORE_ROLE_RE: re.Pattern[str] = re.compile(
    r"\b(?i:former|ancien(?:ne)?|ex|previously|anciennement|co)[\s-]*$"
)
_FAMILY_LINK_WORDS: frozenset[str] = frozenset({"fils", "freres", "pere", "jr", "junior", "senior", "sr", "cie"})
_PROFILE_TITLE_SEPARATOR_RE: re.Pattern[str] = re.compile(r"\s*[(|·–—]\s*|\s+-\s+")
_PHONE_RE: re.Pattern[str] = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_PLACE_RES: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i:location|lieu)\s*:\s*(?P<place>[^·|;\n]+)"),
    re.compile(r"(?i:lives in|habite à|vit à)\s+(?P<place>[^;·|\n,]+)"),
    re.compile(r"(?P<place>[A-ZÀ-Þ][\w'’.-]+(?:[ -][A-ZÀ-Þ][\w'’.-]+){0,3}),?\s+(?:Quebec|Québec|QC)\b"),
)
_TOWN_AFTER_A_RE: re.Pattern[str] = re.compile(
    r"\bà\s+(?P<place>[A-ZÀ-Þ][\w'’-]+(?:[ -](?:[A-ZÀ-Þ][\w'’-]+|sur|sous|en|de|la|le|les|du|des)){0,4})"
)
_SELF_INTRODUCTION_RE: re.Pattern[str] = re.compile(rf"^\s*(?P<person>{_PERSON})\s*[-–—,:]\s*(?P<after>[^.\n]{{3,80}})")
_SELF_EMPLOYED_WORDS: frozenset[str] = frozenset({"independant", "independante", "artisan"})
_OWN_TEXT_EVIDENCE_GROUP: str = "scraped_text"
_REGION_WORDS: frozenset[str] = frozenset(
    {"area", "region", "greater", "metropolitan", "canada", "quebec", "province", "suisse", "switzerland", "france"}
)
_INITIALS_DOT_RE: re.Pattern[str] = re.compile(r"\b([A-Z]{2,3})\.(?=\s)")
_CLAUSE_END_RE: re.Pattern[str] = re.compile(r"\.\.\.|…|[.!?](?=\s|$)|[|·;]|\s-\s")


@dataclass(frozen=True)
class OwnerMention:
    """A person a search result names as the business's owner, and how it says so."""

    first_name: str
    last_name: str
    excerpt: str
    host: str
    #: The person's own profile, or the business's own page, says it.
    is_self_declared: bool


class OwnerMentions:
    """Reads the people Google's results name as a business's owner (pure — testable)."""

    @classmethod
    def candidates_in(
        cls, results: list[dict[str, Any]], context: ResolutionContext, *, is_own_text: bool = False
    ) -> list[NameCandidate]:
        """
        One candidate per person the results name as the owner of this business.

        Args:
            results: Google's results, each with its link, title and description.
            context: The business looked for.
            is_own_text: Whether the « results » are the business's own text (its presentation), not Google's.

        Returns:
            The candidates, the surest statement of each person kept.
        """
        best_by_person: dict[str, NameCandidate] = {}
        for result in results:
            for mention in cls.mentions_in(result, context, is_own_text=is_own_text):
                candidate = cls._candidate_of(mention, context)
                key = candidate.identity_key()
                if key not in best_by_person or candidate.confidence > best_by_person[key].confidence:
                    best_by_person[key] = candidate
        return sorted(best_by_person.values(), key=lambda candidate: (-candidate.confidence, candidate.identity_key()))

    @classmethod
    def in_presentation(cls, context: ResolutionContext) -> list[NameCandidate]:
        """
        The owner the business's own presentation names: « Paul Exemple - Paysagiste indépendant à … », « Le
        propriétaire, Paul Exemple, … ».

        Args:
            context: The business, with its presentation.

        Returns:
            The candidates; none when the presentation names nobody.
        """
        presentation = {"title": context.company_name, "description": context.description or "", "link": ""}
        return cls.candidates_in([presentation], context, is_own_text=True)

    @classmethod
    def mentions_in(
        cls, result: dict[str, Any], context: ResolutionContext, *, is_own_text: bool = False
    ) -> list[OwnerMention]:
        """
        The owners one result names for this business.

        A profile's title (« Marc Exemple - Propriétaire chez … ») or its description (« propriétaire at … ») is the
        person speaking of themselves; a signature (« Alain Exemple Propriétaire … ») is the business speaking when
        the result is its own page, and so is its presentation opening with a person and a trade (« Luc Exemple -
        Paysagiste indépendant »). A result counts only when it also places them in the business's town or shows
        its phone, since another business may bear the same name; one placing them in another town names a
        namesake. In Québec a « gérant » manages a shop for its owner: only the owner's words count there.

        Args:
            result: One of Google's results, with its link, title and description.
            context: The business looked for.
            is_own_text: Whether the result is the business's own text, its place and page by construction.

        Returns:
            The owners it names, tied to the business by its name or its phone.
        """
        title = cls._with_joined_initials(str(result.get("title") or "").strip())
        description = cls._with_joined_initials(str(result.get("description") or "").strip())
        host = (urlparse(str(result.get("link") or "")).hostname or "").removeprefix("www.")
        text = f"{title} · {description}"
        is_here = is_own_text or cls._is_placed_here(text, context.city) or cls._shows_phone(text, context.phone)
        if not is_here or cls._is_elsewhere(text, context.city):
            return []
        mentions: list[OwnerMention] = []
        title_match = _TITLE_ROLE_RE.match(title)
        if (
            title_match
            and cls._is_head_role(title_match["role"], context)
            and cls._names_business_in_title(cls._clause_after(title_match["after"]), description, context)
        ):
            mentions += cls._mention(title_match["person"], title_match.group(0), host, is_self_declared=True)
        title_person = _PROFILE_TITLE_SEPARATOR_RE.split(title, maxsplit=1)[0]
        for match in _PROFILE_ROLE_RE.finditer(description):
            if cls._is_owner_role(description, match, context) and cls._names_business(match["after"], context):
                mentions += cls._mention(title_person, match.group(0), host, is_self_declared=True)
        is_own_page = is_own_text or cls._is_business_page(title, context)
        for match in _SIGNED_ROLE_RE.finditer(description):
            ties = is_own_page or cls._names_business(cls._clause_after(match["after"]), context)
            if ties and cls._is_owner_role(description, match, context):
                mentions += cls._mention(match["person"], match.group(0), host, is_self_declared=is_own_page)
        for match in _ROLE_THEN_PERSON_RE.finditer(description):
            before = cls._clause_before(description[max(match.start() - _CONTEXT_BEFORE_ROLE_CHARS, 0) : match.start()])
            is_single_owner = not match["plural"] and cls._is_owner_role(description, match, context)
            if is_single_owner and (is_own_page or cls._names_business(before, context)):
                mentions += cls._mention(match["person"], match.group(0), host, is_self_declared=is_own_page)
        introduction = _SELF_INTRODUCTION_RE.match(description) if is_own_text else None
        if introduction and cls._names_a_trade(introduction["after"]):
            mentions += cls._mention(introduction["person"], introduction.group(0), host, is_self_declared=True)
        return mentions

    @staticmethod
    def _names_a_trade(words: str) -> bool:
        """Whether the words after a person's name say a trade (« Paysagiste indépendant », « artisan électricien »)."""
        from services.prospect_search.trade_catalog import TradeCatalog

        folded_words = re.findall(r"[a-z]+", fold(words))[:2]
        return any(TradeCatalog.is_trade_word(word) or word in _SELF_EMPLOYED_WORDS for word in folded_words)

    @staticmethod
    def _is_head_role(role: str, context: ResolutionContext) -> bool:
        """Whether a role names the head of the business where it works: a Québec « gérant » runs a shop for its owner."""
        return not (context.country == "CA" and fold(role).startswith("gerant"))

    @classmethod
    def _names_business_in_title(cls, title_after_role: str, description: str, context: ResolutionContext) -> bool:
        """
        Whether a profile titled with an owner's role owns this business: the title names it (« … chez Exemple
        Paysage »), or names no business and the description does (« Proprietaire mecanicien », then « Jt.exemple »).
        """
        from services.prospect_search.business_name import BusinessName

        if cls._names_business(title_after_role, context):
            return True
        return not BusinessName.distinctive_words(title_after_role) and cls._names_business(description, context)

    @staticmethod
    def _clause_after(text: str) -> str:
        """The words that follow a role, up to the end of its clause: never the next sentence's."""
        return _CLAUSE_END_RE.split(text, maxsplit=1)[0]

    @staticmethod
    def _clause_before(text: str) -> str:
        """The words that precede a role, from the start of its clause."""
        return _CLAUSE_END_RE.split(text)[-1]

    @staticmethod
    def _with_joined_initials(text: str) -> str:
        """The text with its initials written as one word, so their dots end no sentence (« J.T. Exemple »)."""
        return _INITIALS_DOT_RE.sub(r"\1", join_dotted_initials(text))

    @staticmethod
    def _mention(person: str, excerpt: str, host: str, *, is_self_declared: bool) -> list[OwnerMention]:
        """The mention of a person, when the words are a known first name followed by a last name."""
        words = person.split()
        first_words = [words.pop(0)]
        while len(words) > 1 and GivenNames.is_common_given_name(words[0]):
            first_words.append(words.pop(0))
        first_name = "-".join(first_words)
        if not words or not (GivenNames.is_given_name(first_name) or GivenNames.is_given_name(first_words[0])):
            return []
        return [
            OwnerMention(
                first_name=title_case_name(first_name) or first_name,
                last_name=title_case_name(" ".join(words)) or " ".join(words),
                excerpt=" ".join(excerpt.split())[:_MAX_EXCERPT_CHARS],
                host=host,
                is_self_declared=is_self_declared,
            )
        ]

    @staticmethod
    def _candidate_of(mention: OwnerMention, context: ResolutionContext) -> NameCandidate:
        """The candidate a mention gives, surer when the business name holds the person's initials (« A.E »)."""
        from services.prospect_search.business_name import BusinessName

        confidence = _SELF_DECLARED_CONFIDENCE if mention.is_self_declared else _REPORTED_CONFIDENCE
        full_name = f"{mention.first_name} {mention.last_name}"
        person_initials = {
            (mention.first_name[:1] + mention.last_name[:1]).upper(),
            "".join(word[:1] for word in re.split(r"[\s-]+", full_name)).upper(),
        }
        business_initials = set(initials_in(BusinessName.without_legal_form(context.company_name or "")))
        initials_note = ""
        if person_initials & business_initials:
            confidence = min(confidence + _INITIALS_BONUS, _MAX_CONFIDENCE)
            initials_note = ", initiales du nom de l'entreprise"
        return NameCandidate(
            first=mention.first_name,
            last=mention.last_name,
            gender=infer_gender(mention.first_name),
            source="web_owner",
            confidence=round(confidence, 2),
            evidence_group=_EVIDENCE_GROUP if mention.host else _OWN_TEXT_EVIDENCE_GROUP,
            provenance=(
                f"Recherche Google : « {mention.excerpt} » ({mention.host}){initials_note}"
                if mention.host
                else f"Présentation de l'entreprise : « {mention.excerpt} »{initials_note}"
            ),
            raw={"excerpt": mention.excerpt, "host": mention.host},
            self_declared=mention.is_self_declared,
        )

    @classmethod
    def _is_owner_role(cls, text: str, match: re.Match[str], context: ResolutionContext) -> bool:
        """Whether the role read there is the head's: not a former owner's, a co-owner's nor a Québec manager's."""
        is_former_or_co_owner = _NOT_THE_OWNER_BEFORE_ROLE_RE.search(text[: match.start("role")]) is not None
        return not is_former_or_co_owner and cls._is_head_role(match["role"], context)

    @classmethod
    def _names_business(cls, text: str, context: ResolutionContext) -> bool:
        """
        Whether a piece of a result names this business: its distinctive words, all its words when those are too
        short or too common to tell it apart (« J.T. Mécanique », « Garage Modèle et Fils »), or its phone number.
        """
        from services.prospect_search.business_name import NAME_LINK_WORDS, BusinessName

        words = company_tokens(join_dotted_initials(text))
        key_words = BusinessName.distinctive_words(context.company_name, town=context.city)
        has_telling_word = any(
            len(word) >= _MIN_KEY_WORD_CHARS and word not in NAME_LINK_WORDS | _FAMILY_LINK_WORDS for word in key_words
        )
        name_words = company_tokens(join_dotted_initials(BusinessName.without_legal_form(context.company_name)))
        named = key_words <= words if has_telling_word else name_words - NAME_LINK_WORDS <= words
        return bool(key_words and named) or cls._shows_phone(text, context.phone)

    @staticmethod
    def _shows_phone(text: str, phone: str | None) -> bool:
        """Whether a piece of a result shows the business's phone number."""
        phone_digits = re.sub(r"\D", "", phone or "")[-_PHONE_DIGITS_COMPARED:]
        return len(phone_digits) == _PHONE_DIGITS_COMPARED and any(
            re.sub(r"\D", "", number).endswith(phone_digits) for number in _PHONE_RE.findall(text)
        )

    @staticmethod
    def _is_business_page(title: str, context: ResolutionContext) -> bool:
        """Whether a result is the business's own page: its title is the business's name."""
        from services.prospect_search.business_name import BusinessName

        page_name = _PROFILE_TITLE_SEPARATOR_RE.split(title, maxsplit=1)[0]
        return bool(page_name) and BusinessName.is_named_like(page_name, context.company_name, town=context.city)

    @classmethod
    def _is_elsewhere(cls, text: str, city: str | None) -> bool:
        """Whether a result places the person in another town than the business's (a region tells nothing)."""
        places = cls._places_in(text)
        return bool(city and places) and not cls._is_placed_here(text, city)

    @classmethod
    def _is_placed_here(cls, text: str, city: str | None) -> bool:
        """Whether a result places the person or the business in the business's town (« Location: … », « … à Pau »)."""
        town = town_key(city or "")
        places = [*cls._places_in(text), *(town_key(match["place"]) for match in _TOWN_AFTER_A_RE.finditer(text))]
        return bool(town) and any(place and (town in place or place in town) for place in places)

    @staticmethod
    def _places_in(text: str) -> list[str]:
        """The towns a result places the person or the business in, as comparison keys (a region left aside)."""
        places = [
            town_key(match["place"])
            for pattern in _PLACE_RES
            for match in pattern.finditer(text)
            if not company_tokens(match["place"]) & _REGION_WORDS
        ]
        return [place for place in places if place]


class WebOwnerStrategy:
    """Supporting — the owner Google's results name for the business, on a profile, its page or a page about it."""

    name = "web_owner"

    def __init__(self, client: Any | None = None) -> None:
        """Wire the Bright Data client (injectable for tests)."""
        if client is not None:
            self._client = client
        else:
            from scrappers.brightdata_client import BrightDataClient

            self._client = BrightDataClient()

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """
        Read the owner the business's presentation names, then search Google for its name with « propriétaire » (and
        « gérant » outside Québec, where it names the head too) and read the owners the results name.
        """
        from services.prospect_search.business_name import BusinessName

        candidates = OwnerMentions.in_presentation(context)
        name = BusinessName.without_legal_form(context.company_name or "").strip()
        is_telling_name = bool(BusinessName.distinctive_words(name, town=context.city))
        if not is_telling_name or not getattr(self._client, "is_configured", False):
            return candidates
        roles = "propriétaire" if context.country == "CA" else "gérant OR propriétaire"
        query = f'"{name}" {roles}'
        for search in range(_SEARCHES):
            try:
                page = await self._client.google_parsed(query, country=context.country or "FR")
            except Exception as exc:
                logger.warning("web_owner search failed for %r: %s", query, exc)
                return candidates
            if page is not None:
                return [*candidates, *OwnerMentions.candidates_in(page.get("organic") or [], context)]
            await asyncio.sleep(_SEARCH_RETRY_PAUSE_SECONDS * (search + 1))
        logger.warning("web_owner search answered nothing for %r", query)
        return candidates
