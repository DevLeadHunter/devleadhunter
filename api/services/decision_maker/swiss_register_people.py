"""
Swiss register people — who runs a Swiss business, read from its publications in the official gazette (FOSC).

Zefix gives no person list, only the FOSC publications of each firm. Since about 2020 they read
« Personne(s) inscrite(s): Exemple, Paul, de Lausanne, à Morges, associé et gérant, avec signature
individuelle »; older ones « Titulaire: Exemple Paul, de … » or « Administration: Exemple Paul, de …,
à …, président, Modèle Anne, de …, à …, lesquels signent individuellement », and « Exemple Paul n'est
plus directeur ». Read in date order, entries and departures give the people registered today, and
their roles say who runs the business.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, replace
from datetime import date

from services.decision_maker.normalize import fold, title_case_name

# The headings that list people entering the register, and those that strike them off (French, German).
_ENTERING_HEADINGS: tuple[str, ...] = (
    "personne(s) inscrite(s)",
    "personnes inscrites",
    "inscription ou modification de personne(s)",
    "nouvelles personnes inscrites ou modifications des personnes inscrites",
    "titulaire",
    "associés gérants",
    "associés-gérants",
    "associé gérant",
    "associé-gérant",
    "associés",
    "associé",
    "gérants",
    "gérant",
    "gérance",
    "administrateur unique",
    "administrateurs",
    "administration",
    "eingetragene personen",
    "inhaber",
)
_LEAVING_HEADINGS: tuple[str, ...] = (
    "personne(s) et signature(s) radiée(s)",
    "personnes et signatures radiées",
    "personnes dont les pouvoirs sont radiés",
    "ausgeschiedene personen und erloschene unterschriften",
)
# Headings naming a role: the people listed under them hold it.
_ROLE_HEADINGS: frozenset[str] = frozenset(
    {
        "titulaire",
        "inhaber",
        "associés gérants",
        "associés-gérants",
        "associé gérant",
        "associé-gérant",
        "gérants",
        "gérant",
        "gérance",
        "administrateur unique",
    }
)
_HEADING_RE: re.Pattern[str] = re.compile(
    r"(?<![\w-])("
    + "|".join(
        re.escape(heading) for heading in sorted((*_ENTERING_HEADINGS, *_LEAVING_HEADINGS), key=len, reverse=True)
    )
    + r")(?:\s+avec\s+signature[^:.]{0,40})?\s*:",
    re.IGNORECASE,
)
# A section ends with its sentence; « St. Gallen » or « p. 12 » do not end one.
_SENTENCE_END_RE: re.Pattern[str] = re.compile(r"\.\s+(?=[A-ZÀ-Ý])")
_ABBREVIATIONS: frozenset[str] = frozenset({"st", "ste", "dr", "me", "mme", "p", "no", "art", "al"})
# In the older lists, people follow one another with a comma: a new one starts « Nom Prénom, … ».
_NEXT_PERSON_RE: re.Pattern[str] = re.compile(r",\s+(?:et\s+)?(?=[A-ZÀ-Ý][\w'’-]+(?:\s+[A-ZÀ-Ý][\w'’-]+)+,\s)")
# « l'associé Exemple Paul avec signature individuelle », « lequel est en outre gérant avec signature… »
_ROLE_PREFIX_RE: re.Pattern[str] = re.compile(
    r"^(?:l['’]associée?\s+|(?:lequel|laquelle)\s+est\s+(?:en\s+outre\s+)?)", re.IGNORECASE
)
_SIGNATURE_SUFFIX_RE: re.Pattern[str] = re.compile(
    r"\s+(?:avec|sans|mit|ohne)\s+(?:signature|unterschrift)\b.*$", re.IGNORECASE
)
# « Exemple Paul n'est plus directeur; ses pouvoirs sont radiés. »
_DEPARTURE_RE: re.Pattern[str] = re.compile(
    r"([A-ZÀ-Ý][\w'’-]+(?:[ -][A-ZÀ-Ý][\w'’-]+)+)\s+n['’]est plus\b", re.UNICODE
)
_ORIGIN_RE: re.Pattern[str] = re.compile(r"^(?:de\s|d['’]|von\s|du\s|des\s|tous\s+deux\s+de\s)", re.IGNORECASE)
_DOMICILE_RE: re.Pattern[str] = re.compile(r"^(?:à|a|in|en)\s", re.IGNORECASE)
_NOT_A_ROLE_RE: re.Pattern[str] = re.compile(
    r"\b(?:signature|signent|signe|unterschrift|pour\s+\d|für\s+\d|mit\s+\d|parts?|renoncé|exerce)\b", re.IGNORECASE
)
_COMPANY_RE: re.Pattern[str] = re.compile(r"\b(?:sa|sàrl|sarl|ag|gmbh|fiduciaire|revision|révision)\b|che-\d")
# A UTF-8 accent read as Latin-1 (« SÃ rl », « Ã Porrentruy ») in some publications.
_MOJIBAKE_RE: re.Pattern[str] = re.compile("[ÂÃ][\u0080-¿]")

# Roles from the one running the business to the ones only signing for it.
_OWNER_ROLES: tuple[str, ...] = ("titulaire", "inhaber", "inhaberin")
_CHAIR_ROLES: tuple[str, ...] = (
    "président",
    "présidente",
    "administrateur unique",
    "administratrice unique",
    "präsident",
    "präsidentin",
    "einziges mitglied",
)
_MANAGER_ROLES: tuple[str, ...] = (
    "gérant",
    "gérante",
    "gérance",
    "geschäftsführer",
    "geschäftsführerin",
)
_DIRECTOR_ROLES: tuple[str, ...] = ("directeur", "directrice", "direktor", "direktorin")


@dataclass(frozen=True)
class RegisteredPerson:
    """A person the register lists for a firm, with what they do there."""

    first_name: str | None
    last_name: str
    roles: tuple[str, ...]
    #: « Nom, Prénom » says which word is the first name; « Nom Prénom » of three words or more does not.
    is_name_certain: bool = True

    @property
    def rank(self) -> int:
        """How much the person runs the business: 4 owner, 3 chair, 2 manager, 1 director, 0 otherwise."""
        roles = " ".join(fold(role) for role in self.roles)
        if "vice" in roles:
            return 0
        for rank, vocabulary in ((4, _OWNER_ROLES), (3, _CHAIR_ROLES), (2, _MANAGER_ROLES), (1, _DIRECTOR_ROLES)):
            if any(fold(role) in roles for role in vocabulary):
                return rank
        return 0

    @property
    def key(self) -> str:
        """The person's identity across publications."""
        return fold(f"{self.last_name} {self.first_name or ''}").strip()


def registered_people(publications: list[tuple[date, str]]) -> list[RegisteredPerson]:
    """
    The people registered today, from a firm's publications read oldest first.

    Args:
        publications: ``(date, text)`` of each FOSC publication, in any order.

    Returns:
        The people entered and not struck off since, latest entry kept.
    """
    people: dict[str, RegisteredPerson] = {}
    for _, text in sorted(publications, key=lambda publication: publication[0]):
        clean = _plain_text(text)
        for heading, entries in _sections(clean):
            for entry in entries:
                person = _person(entry, heading=heading)
                if person is None:
                    continue
                if heading in _LEAVING_HEADINGS:
                    people.pop(person.key, None)
                    continue
                known = people.get(person.key)
                # A later mention without a role (« Signature individuelle est conférée à … ») keeps the known one.
                people[person.key] = person if person.roles or known is None else replace(person, roles=known.roles)
        for departure in _DEPARTURE_RE.finditer(clean):
            words = departure.group(1).split()
            people.pop(fold(" ".join([*words[:-1], words[-1]])), None)
            people.pop(fold(" ".join([*words[1:], words[0]])), None)
    return list(people.values())


def lead_people(people: list[RegisteredPerson]) -> list[RegisteredPerson]:
    """The people holding the highest running role (owner, chair, manager, director); none when nobody runs it."""
    top = max((person.rank for person in people), default=0)
    return [person for person in people if top and person.rank == top]


def _plain_text(text: str) -> str:
    """A publication as plain text, its tags gone and its mis-decoded accents repaired."""
    plain = _MOJIBAKE_RE.sub(_repaired_accent, html.unescape(re.sub(r"<[^>]+>", " ", text)))
    return re.sub(r"\s+", " ", plain)


def _repaired_accent(match: re.Match[str]) -> str:
    """The accent a UTF-8 pair read as Latin-1 stood for (« Ã© » → « é »), or the pair when it is not one."""
    try:
        return match.group(0).encode("latin-1").decode("utf-8")
    except UnicodeError:
        return match.group(0)


def _sections(text: str) -> list[tuple[str, list[str]]]:
    """The people headings of a publication and their entries (« Nom, Prénom, de …, à …, rôle »)."""
    sections: list[tuple[str, list[str]]] = []
    matches = list(_HEADING_RE.finditer(text))
    for index, match in enumerate(matches):
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = _first_sentence(text[match.end() : body_end])
        entries = [
            person.strip(" .")
            for entry in body.split(";")
            for person in _NEXT_PERSON_RE.split(entry)
            if person.strip(" .")
        ]
        sections.append((match.group(1).lower(), entries))
    return sections


def _first_sentence(text: str) -> str:
    """The text up to its first sentence end, abbreviations aside."""
    for end in _SENTENCE_END_RE.finditer(text):
        last_word = re.findall(r"[\w'’-]+$", text[: end.start()])
        if not last_word or fold(last_word[0]) not in _ABBREVIATIONS:
            return text[: end.start()]
    return text


def _person(entry: str, *, heading: str) -> RegisteredPerson | None:
    """One person of a section entry, or ``None`` when the entry names a company (an auditor) or nobody."""
    parts = [
        _SIGNATURE_SUFFIX_RE.sub("", _ROLE_PREFIX_RE.sub("", part.strip())).strip()
        for part in entry.split(",")
        if part.strip()
    ]
    parts = [part for part in parts if part]
    if not parts or _COMPANY_RE.search(fold(parts[0])):
        return None
    is_name_certain = True
    if len(parts) > 1 and re.match(r"^[A-ZÀ-Ý]", parts[1]) and not _ORIGIN_RE.match(parts[1]):
        last_name, first_name, details = parts[0], parts[1], parts[2:]
    else:
        # The older lists write « Exemple Paul, de … »: the first name after the last name.
        words = parts[0].split()
        if len(words) < 2:
            return None
        last_name, first_name, details = " ".join(words[:-1]), words[-1], parts[1:]
        is_name_certain = len(words) == 2
    if not re.match(r"^[A-ZÀ-Ý]", last_name):
        return None
    roles = tuple(
        part
        for part in details
        if not (_ORIGIN_RE.match(part) or _DOMICILE_RE.match(part) or _NOT_A_ROLE_RE.search(part))
    )
    if heading in _ROLE_HEADINGS:
        roles = (heading, *roles)
    return RegisteredPerson(
        first_name=title_case_name(first_name),
        last_name=title_case_name(last_name) or last_name,
        roles=roles,
        is_name_certain=is_name_certain,
    )
