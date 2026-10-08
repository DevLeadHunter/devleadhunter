"""
The person a business's own email address is named after — whoever reads « jules.exemple@… » is Jules Exemple.

An artisan's address is often their own name, glued or dotted, with a number or a trade word around it
(« julesexemple64@ », « exemple.jules@ », « jardinsjulesexemple@ »). An address that only repeats the business
name (« garagejulesexemple@ » for « Garage Jules Exemple ») says nothing more than the name does.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from services.decision_maker.given_names import GivenNames
from services.decision_maker.normalize import fold, infer_gender, title_case_name
from services.decision_maker.types import NameCandidate, ResolutionContext
from services.prospect_search.trade_catalog import TradeCatalog

_LOCAL_PART_SEPARATOR_RE: re.Pattern[str] = re.compile(r"[._+\-\d]+")
_BUSINESS_NAME_SEPARATOR_RE: re.Pattern[str] = re.compile(r"[^a-z0-9]+")
_VOWELS_RE: re.Pattern[str] = re.compile(r"[aeiouy]")
_MIN_NAME_CHARS: int = 3
_MAX_INITIALS_CHARS: int = 2
_EMAIL_EVIDENCE_GROUP: str = "email"
_NOT_A_NAME_WORDS: frozenset[str] = frozenset(
    {
        "info",
        "infos",
        "contact",
        "contacts",
        "mail",
        "email",
        "admin",
        "office",
        "bureau",
        "secretariat",
        "compta",
        "comptabilite",
        "devis",
        "commande",
        "accueil",
        "sav",
        "hello",
        "bonjour",
        "direction",
        "gerance",
        "pro",
        "web",
        "garages",
        "auto",
        "autos",
        "moto",
        "motos",
        "mecanique",
        "mecaniques",
        "meca",
        "electrique",
        "elec",
        "telecom",
        "paysager",
        "paysagement",
        "jardinier",
        "jardinage",
        "carrosserie",
        "depannage",
        "pneu",
        "pneus",
        "batiment",
        "construction",
        "energie",
        "solaire",
        "deneigement",
        "pelouse",
        "elagage",
        "terrassement",
        "exterieur",
        "utilitaires",
        "diesel",
    }
)


@dataclass(frozen=True)
class EmailPerson:
    """The person an email address is named after, and whether the business's own name names them too."""

    first_name: str
    last_name: str
    is_in_business_name: bool


class PersonInEmail:
    """Reads the person an email address is named after."""

    @classmethod
    def person_of(cls, email: str, business_name: str) -> EmailPerson | None:
        """
        The person a business's email address is named after (pure — testable).

        A common first name must open a word of the address; the next word, or the rest of
        a glued word, is the last name (« exemple.jules@ », « julesexemple@ »), and initials ending a glued word
        drop (« julesexemplejx@ »). A first name alone takes the last name that follows it in the business name,
        else names nobody: « martin_lps@ » may spell a last name. Trade and mailbox words around the name are left
        out. The business name names the person too when it holds the last name or the person's initials; a glued
        name it does not hold names nobody: « julesexemplemodele@ » may join a double last name.

        Args:
            email: One of the business's addresses.
            business_name: The business's name.

        Returns:
            The person; ``None`` for an address of the business (« info@ », the business name) or without a full name.
        """
        from services.prospect_search.business_name import COMMON_NAME_WORDS, BusinessName

        business_name_words = [
            word
            for word in _BUSINESS_NAME_SEPARATOR_RE.split(fold(BusinessName.without_legal_form(business_name)))
            if word
        ]
        business_words = set(business_name_words)
        vocabulary = (
            _NOT_A_NAME_WORDS
            | COMMON_NAME_WORDS
            | {word for word in business_words if TradeCatalog.is_trade_word(word)}
        )
        words: list[str] = []
        has_trade_word = False
        for token in _LOCAL_PART_SEPARATOR_RE.split(fold(email.partition("@")[0])):
            remainder = cls._without_words(token, vocabulary)
            has_trade_word = has_trade_word or remainder != token
            if remainder:
                words.append(remainder)
        person = cls._person_in_words(words)
        if person is None:
            return None
        first_name, last_name = person
        business_name_beside_trade = "".join(word for word in business_name_words if word not in vocabulary)
        if has_trade_word and first_name + (last_name or "") in business_name_beside_trade:
            return None
        if last_name is None and first_name in business_name_words:
            following = business_name_words[business_name_words.index(first_name) + 1 :][:1]
            last_name = next((word for word in following if cls._last_name(word) == word), None)
        if last_name is None:
            return None
        initials = first_name[:1] + last_name[:1]
        is_in_business_name = last_name in business_words or initials in business_words
        if len(words) == 1 and not is_in_business_name:
            return None
        return EmailPerson(
            first_name=title_case_name(first_name) or first_name,
            last_name=title_case_name(last_name) or last_name,
            is_in_business_name=is_in_business_name,
        )

    @classmethod
    def _person_in_words(cls, words: list[str]) -> tuple[str, str | None] | None:
        """The first and last name the words of an address spell, first name first or last."""
        if len(words) == 1:
            return cls._person_in_glued_word(words[0])
        for index, word in enumerate(words):
            if len(word) < _MIN_NAME_CHARS or not GivenNames.is_common_given_name(word):
                continue
            neighbours = [*words[index + 1 : index + 2], *words[max(index - 1, 0) : index]]
            last_names = (cls._last_name(neighbour) for neighbour in neighbours)
            return word, next((last_name for last_name in last_names if last_name), None)
        return None

    @classmethod
    def _person_in_glued_word(cls, word: str) -> tuple[str, str | None] | None:
        """The first name opening a glued word and the last name it is glued to (« julesexemple »)."""
        if GivenNames.is_common_given_name(word):
            return word, None
        for cut in range(len(word) - 1, _MIN_NAME_CHARS - 1, -1):
            first_name, rest = word[:cut], word[cut:]
            if not GivenNames.is_common_given_name(first_name):
                continue
            initials = first_name[:1] + rest[:1]
            if len(rest) > _MAX_INITIALS_CHARS + _MIN_NAME_CHARS and rest.endswith(initials):
                return first_name, rest[: -len(initials)]
            return first_name, cls._last_name(rest)
        return None

    @staticmethod
    def _last_name(word: str) -> str | None:
        """A word read as a last name: three letters at least, a vowel, and not itself a common first name."""
        if len(word) < _MIN_NAME_CHARS or GivenNames.is_common_given_name(word) or not _VOWELS_RE.search(word):
            return None
        return word

    @staticmethod
    def _without_words(token: str, vocabulary: frozenset[str]) -> str:
        """A word of an address without the trade and mailbox words glued at its start or its end."""
        remainder = token
        while remainder:
            piece = next(
                (
                    piece
                    for cut in range(len(remainder), _MIN_NAME_CHARS - 1, -1)
                    for piece in (remainder[:cut], remainder[-cut:])
                    if piece in vocabulary
                ),
                None,
            )
            if piece is None:
                break
            remainder = remainder[len(piece) :] if remainder.startswith(piece) else remainder[: -len(piece)]
        return remainder


class EmailOwnerStrategy:
    """Supporting — the person the business's own email address is named after."""

    name = "email"

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Read the person behind each of the business's addresses."""
        return self.candidates_of(context)

    def candidates_of(self, context: ResolutionContext) -> list[NameCandidate]:
        """
        One candidate per address named after a person (pure — testable).

        A full name the business name holds too (« jules.exemple@ » at « Exemple Paysage ») is self-declared twice
        and usable on its own; a full name alone is a proposal.
        """
        candidates: list[NameCandidate] = []
        for email in context.emails:
            person = PersonInEmail.person_of(email, context.company_name)
            if person is None:
                continue
            confidence = 0.75 if person.is_in_business_name else 0.6
            business_name_note = f", et le nom de l'entreprise « {context.company_name} »"
            candidates.append(
                NameCandidate(
                    first=person.first_name,
                    last=person.last_name,
                    gender=infer_gender(person.first_name),
                    source=self.name,
                    confidence=confidence,
                    evidence_group=_EMAIL_EVIDENCE_GROUP,
                    provenance=f"Adresse mail « {email} »{business_name_note if person.is_in_business_name else ''}",
                    raw={"email": email},
                    self_declared=person.is_in_business_name,
                )
            )
        return candidates
