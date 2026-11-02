"""
Name in an address — whose name the words of an email address or of a domain spell.

An address is often made of its owner's name: « gld-automobiles@orange.fr » is GLD Automobiles's
address and « ag-garage.fr » AG Automobiles's domain, whatever the page that shows them. An address
may as well spell another business (« brd.auto.performance@gmail.com » on Garage Exemple's directory
page), or a person (« claire.exemple@gmail.com »), which names no business at all. The address is
read as an operator reads it: the words of a trade and the words any name carries say nothing about
whose it is, what is left is a name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from scrappers.email_candidate_scoring import ROLE_LOCAL_PARTS, email_candidate_scorer
from services.decision_maker.normalize import fold
from services.prospect_search.business_name import COMMON_NAME_WORDS, NAME_LINK_WORDS
from services.prospect_search.candidate_facts import CandidateFacts

# Words saying an activity, not a name: an address carrying one belongs to a business (« garage », « paysage »).
_ACTIVITY_WORDS: frozenset[str] = frozenset(
    {
        "garage",
        "garages",
        "garagiste",
        "gge",
        "auto",
        "autos",
        "automobile",
        "automobiles",
        "automotive",
        "car",
        "cars",
        "carrosserie",
        "carrossier",
        "mecanique",
        "mecanicien",
        "meca",
        "moto",
        "motos",
        "motor",
        "motors",
        "motorsport",
        "pneu",
        "pneus",
        "pneumatique",
        "pneumatiques",
        "depannage",
        "depanneur",
        "remorquage",
        "reparation",
        "repair",
        "vehicule",
        "vehicules",
        "voiture",
        "voitures",
        "occasion",
        "occasions",
        "negoce",
        "diag",
        "diagnostic",
        "vo",
        "vn",
        "paysage",
        "paysages",
        "paysager",
        "paysagiste",
        "paysagistes",
        "jardin",
        "jardins",
        "jardinier",
        "jardinage",
        "garden",
        "gardens",
        "elagage",
        "elagueur",
        "tonte",
        "arbre",
        "arbres",
        "cloture",
        "clotures",
        "arrosage",
        "electricite",
        "electricien",
        "electrique",
        "elec",
        "domotique",
        "eclairage",
        "plomberie",
        "plombier",
        "chauffage",
        "chauffagiste",
        "sanitaire",
        "sanitaires",
        "climatisation",
        "clim",
        "couverture",
        "couvreur",
        "toiture",
        "toitures",
        "zinguerie",
        "zingueur",
        "charpente",
        "charpentier",
        "menuiserie",
        "menuisier",
        "ebeniste",
        "ebenisterie",
        "barbier",
        "barber",
        "barbershop",
        "coiffure",
        "coiffeur",
        "foodtruck",
        "food",
        "truck",
        "pizza",
        "pizzeria",
        "burger",
        "snack",
        "traiteur",
    }
)
# Words any name or address may carry without telling whose it is: common and linking words, role inboxes,
# legal forms, family words (« et fils »).
_FILLER_WORDS: frozenset[str] = (
    COMMON_NAME_WORDS
    | NAME_LINK_WORDS
    | ROLE_LOCAL_PARTS
    | frozenset(
        {
            "fils",
            "freres",
            "frere",
            "pere",
            "cie",
            "pro",
            "groupe",
            "group",
            "france",
            "mail",
            "email",
            "sarl",
            "sas",
            "sasu",
            "eurl",
            "ets",
            "ei",
            "sa",
        }
    )
)
_LEGAL_FORM_WORDS: frozenset[str] = frozenset(
    {
        "sarl",
        "sas",
        "sasu",
        "eurl",
        "eirl",
        "ets",
        "ei",
        "sa",
        "snc",
        "sci",
        "gmbh",
        "sagl",
        "inc",
        "enr",
        "ltee",
        "ltd",
    }
)
# « AG » is a legal form where German is spoken; in France it is a business's initials (« AG Automobiles »).
_COUNTRIES_WRITING_AG_AS_LEGAL_FORM: tuple[str, ...] = ("CH", "DE", "AT", "LI")
_WORD_SEPARATORS_RE: re.Pattern[str] = re.compile(r"[^a-z0-9]+")
_DIGITS_RE: re.Pattern[str] = re.compile(r"\d+")
# A trade word marking a business must be long enough not to sit inside any word by chance.
_ACTIVITY_MARKER_MIN_CHARS: int = 4
# A stretch of four letters or more no known word explains is a name; shorter ones are initials or noise.
_NAME_MIN_CHARS: int = 4
# Initials (« ag », « gld ») name a business only beside a trade word (« ag-garage »).
_STANDALONE_NAME_MIN_CHARS: int = 5
# A word of the business's own name, found inside an address, must have three letters at least.
_OWN_WORD_MIN_CHARS: int = 3
_NAMED_PEOPLE_SOURCE_REGISTER: str = "le registre des entreprises"
_NAMED_PEOPLE_SOURCE_PAGE: str = "une page lue par la recherche"
_NAMED_PEOPLE_SOURCE_LISTING: str = "le nom de sa fiche Google"


@dataclass(frozen=True)
class EmailPersonMismatch:
    """The person an email is named after, and the one a record of the business names instead."""

    email_person: str
    named_person: str
    named_by: str


class NameInAddress:
    """Tells whether the words of an email address or a domain spell a business's own name, or another's."""

    @classmethod
    def email_names_business(cls, email: str, facts: CandidateFacts) -> bool:
        """
        Whether the words before the « @ » are the business's own name (« gld-automobiles » for GLD Automobiles).

        Args:
            email: The address.
            facts: The business: its name and town.

        Returns:
            True when the address spells the business's own words, the trade's and common words aside.
        """
        return cls._spells_business(email.rpartition("@")[0], facts)

    @classmethod
    def domain_names_business(cls, domain: str, facts: CandidateFacts) -> bool:
        """
        Whether a domain's registered name spells the business's own name (« ag-garage.fr » for AG Automobiles).

        Args:
            domain: The domain, without scheme (« ag-garage.fr »).
            facts: The business: its name and town.

        Returns:
            True when the domain spells the business's own words, the trade's and common words aside.
        """
        return cls._spells_business(email_candidate_scorer.registrable_label(domain), facts)

    @classmethod
    def email_names_another_business(cls, email: str, facts: CandidateFacts) -> bool:
        """
        Whether the words before the « @ » plainly name a business other than this one.

        The address must carry a trade's word (« auto », « garage »), a name the business's own name does not
        hold (« brd.auto.performance », « garageautohouse » for Garage Exemple Auto), and no word of the
        business's name or its owner's. A person's address (« claire.exemple@… ») names no business.

        Args:
            email: The address.
            facts: The business: its name, town and owner.

        Returns:
            True when the address is another business's.
        """
        return cls._spells_another_business(email.rpartition("@")[0], facts)

    @classmethod
    def domain_names_another_business(cls, domain: str, facts: CandidateFacts) -> bool:
        """
        Whether a domain's registered name plainly names a business other than this one (« temoin-auto.ch »).

        A group's domain (« groupe-exemple.ch ») carries no trade's word: it names no other business.

        Args:
            domain: The domain, without scheme.
            facts: The business: its name, town and owner.

        Returns:
            True when the domain is another business's.
        """
        return cls._spells_another_business(email_candidate_scorer.registrable_label(domain), facts)

    @classmethod
    def email_person_mismatch(cls, email: str, facts: CandidateFacts) -> EmailPersonMismatch | None:
        """
        A person the business's records name, whose name the person its email is named after does not bear.

        « temoin.jules@ », read on a page a search found, is a namesake's address when the registry writes Jules
        Exemple at the head of the business's company; the owner a page names and the person the listing's name
        spells count too. An address naming no person, or a person bearing one of their names, says nothing.

        Args:
            email: The business's email.
            facts: The business: its name, its owner and the heads the registry writes.

        Returns:
            Both people and who names the second one, or None.
        """
        from services.decision_maker.email_owner import PersonInEmail

        person = PersonInEmail.person_of(email, facts.name)
        if person is None:
            return None
        email_last_name = "".join(cls._words(person.last_name))
        for named_person, named_by in cls._people_named_for(facts):
            named_words = cls._words(named_person)
            bears_a_named_word = any(
                word == email_last_name or (len(word) >= _OWN_WORD_MIN_CHARS and word in email_last_name)
                for word in named_words
            )
            if named_words and not bears_a_named_word:
                return EmailPersonMismatch(f"{person.first_name} {person.last_name}", named_person, named_by)
        return None

    @classmethod
    def foreign_name_words(cls, email: str, facts: CandidateFacts) -> list[str]:
        """
        The names an email's words hold beyond the business's own, its trade and its town (« franzen » in
        « garagefranzen@ » for a Garage de la Gare).

        Args:
            email: The business's email.
            facts: The business: its name and town.

        Returns:
            The folded names, four letters at least, in their order.
        """
        own_words = frozenset(word for word in cls.own_words(facts) if len(word) >= _OWN_WORD_MIN_CHARS)
        vocabulary = _ACTIVITY_WORDS | _FILLER_WORDS | cls._town_words(facts) | own_words
        return [
            run
            for segment in cls._segments(email.rpartition("@")[0])
            for run in cls._unexplained_runs(segment, vocabulary)
            if len(run) >= _NAME_MIN_CHARS
        ]

    @staticmethod
    def _people_named_for(facts: CandidateFacts) -> list[tuple[str, str]]:
        """Who the registry, a page the search read and the listing's name say runs the business, and who says it."""
        from services.decision_maker.strategies import BusinessNameOwnerStrategy
        from services.decision_maker.types import ResolutionContext

        people = [
            (str(line["value"]), _NAMED_PEOPLE_SOURCE_REGISTER)
            for line in facts.evidence
            if line.get("fact") == "registered_head" and line.get("value")
        ]
        if facts.owner_name:
            owner_line = next(
                (
                    line
                    for line in facts.evidence
                    if line.get("fact") == "owner" and line.get("value") == facts.owner_name
                ),
                {},
            )
            people.append((facts.owner_name, str(owner_line.get("source") or _NAMED_PEOPLE_SOURCE_PAGE)))
        for candidate in BusinessNameOwnerStrategy().candidates_of(ResolutionContext(company_name=facts.name)):
            if candidate.first and candidate.last:
                people.append((f"{candidate.first} {candidate.last}", _NAMED_PEOPLE_SOURCE_LISTING))
        return people

    @classmethod
    def _spells_another_business(cls, address_part: str, facts: CandidateFacts) -> bool:
        """Whether words of an address carry a trade's word and a name of their own, none of the business's."""
        segments = cls._segments(address_part)
        compact = "".join(segments)
        is_business_address = any(
            word in compact for word in _ACTIVITY_WORDS if len(word) >= _ACTIVITY_MARKER_MIN_CHARS
        )
        if not is_business_address:
            return False
        owner_words = cls._words(facts.owner_name or "")
        own_words = [word for word in (*cls.own_words(facts), *owner_words) if len(word) >= _OWN_WORD_MIN_CHARS]
        if any(word in compact for word in own_words):
            return False
        vocabulary = _ACTIVITY_WORDS | _FILLER_WORDS | cls._town_words(facts)
        return any(
            len(run) >= _NAME_MIN_CHARS for segment in segments for run in cls._unexplained_runs(segment, vocabulary)
        )

    @classmethod
    def own_words(cls, facts: CandidateFacts) -> list[str]:
        """
        The words of the business's name that are its own, in their order: no legal form, trade, common word or town.

        Args:
            facts: The business: its name and town.

        Returns:
            The folded words, digits left out (« lucens » for « SARL Lucens Automobiles Montluçon »).
        """
        left_out = _ACTIVITY_WORDS | _FILLER_WORDS | _LEGAL_FORM_WORDS | cls._town_words(facts)
        if facts.country in _COUNTRIES_WRITING_AG_AS_LEGAL_FORM:
            left_out |= {"ag"}
        return [word for word in cls._words(facts.name) if word not in left_out]

    @classmethod
    def _spells_business(cls, address_part: str, facts: CandidateFacts) -> bool:
        """
        Whether an address part is the business's own words, surrounded by words that say nothing about whose it is.

        Initials are not enough on their own (« ag.fr »): they need a trade word beside them (« ag-garage.fr »).
        """
        own_name = "".join(cls.own_words(facts))
        compact = "".join(cls._segments(address_part))
        if not own_name:
            return False
        vocabulary = _ACTIVITY_WORDS | _FILLER_WORDS | cls._town_words(facts)
        for match in re.finditer(f"(?={re.escape(own_name)})", compact):
            around = (compact[: match.start()], compact[match.start() + len(own_name) :])
            if any(cls._unexplained_runs(part, vocabulary) for part in around):
                continue
            has_trade_word_around = any(word in part for part in around for word in _ACTIVITY_WORDS)
            if len(own_name) >= _STANDALONE_NAME_MIN_CHARS or has_trade_word_around:
                return True
        return False

    @staticmethod
    def _unexplained_runs(text: str, vocabulary: frozenset[str]) -> list[str]:
        """
        The stretches of *text* no known word explains, read the way that leaves the fewest letters unexplained.

        « garageautohouse » leaves « house »; « gldautomobiles » with « gld » known leaves nothing.
        """
        length = len(text)
        unexplained_letters = [0] + [length + 1] * length
        previous_step: list[tuple[int, bool]] = [(0, True)] * (length + 1)
        for position in range(length):
            cost = unexplained_letters[position]
            if cost + 1 < unexplained_letters[position + 1]:
                unexplained_letters[position + 1] = cost + 1
                previous_step[position + 1] = (position, False)
            for word in vocabulary:
                end = position + len(word)
                if text.startswith(word, position) and cost < unexplained_letters[end]:
                    unexplained_letters[end] = cost
                    previous_step[end] = (position, True)
        is_unexplained = [False] * length
        position = length
        while position > 0:
            previous, is_known_word = previous_step[position]
            if not is_known_word:
                is_unexplained[previous] = True
            position = previous
        return "".join(
            letter if is_letter_unexplained else " "
            for letter, is_letter_unexplained in zip(text, is_unexplained, strict=True)
        ).split()

    @staticmethod
    def _segments(address_part: str) -> list[str]:
        """The parts of an address between its separators, folded, digits left out (« garagecsauto86 » gives « garagecsauto »)."""
        return [
            segment
            for segment in (_DIGITS_RE.sub("", part) for part in _WORD_SEPARATORS_RE.split(fold(address_part)))
            if segment
        ]

    @classmethod
    def _words(cls, text: str) -> list[str]:
        """The folded words of a name, digits left out, single letters dropped."""
        return [word for word in cls._segments(text) if len(word) > 1]

    @classmethod
    def _town_words(cls, facts: CandidateFacts) -> frozenset[str]:
        """The words of the business's town and of the town searched, which an address may carry (« daxcarrosserie »)."""
        return frozenset(word for town in (facts.city, facts.searched_city) for word in cls._words(town or ""))
