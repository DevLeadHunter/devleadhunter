"""
Register spelling — a French register's capitals written the way a site shows them.

The RGE list writes « SAINT-AMAND ELECTRICITE », « RUE DE L'ORNE - ZI » and « LEFEVRE CEDRIC »; a site shows
« Saint-Amand Électricité », « Rue de l'Orne, ZI, 14570 Saint-Rémy » and « Cédric Lefevre ». Link words stay in
lowercase, legal forms and acronyms in capitals, a trade's common words and first names take their accents, and the
commune its official spelling (see ``FrenchDepartments.commune_name``).
"""

from __future__ import annotations

import re

from services.decision_maker.given_names import GivenNames
from services.decision_maker.normalize import fold

_LINK_WORDS: frozenset[str] = frozenset({"de", "du", "des", "et", "en", "sur", "sous", "au", "aux"})
_ARTICLES: frozenset[str] = frozenset({"le", "la", "les"})
_ELIDED_WORDS: frozenset[str] = frozenset({"d", "l"})
_CAPITALS_WORDS: frozenset[str] = frozenset(
    {"sarl", "sas", "sasu", "eurl", "sa", "snc", "sci", "ei", "eirl", "scop", "selarl", "gie"}
    | {"za", "zac", "zae", "zi", "bp", "cs", "rn", "rd"}
)
_STREET_TYPES: frozenset[str] = frozenset(
    {
        "rue",
        "avenue",
        "av",
        "boulevard",
        "bd",
        "chemin",
        "impasse",
        "route",
        "place",
        "allee",
        "quai",
        "cours",
        "square",
        "passage",
        "voie",
        "sentier",
        "ruelle",
        "chaussee",
        "faubourg",
        "promenade",
        "esplanade",
        "clos",
        "cite",
        "residence",
        "lotissement",
        "hameau",
        "lieu-dit",
    }
)
_HOUSE_NUMBER_SUFFIXES: frozenset[str] = frozenset({"bis", "ter", "quater"})
_ADDRESS_PART_MARKERS: frozenset[str] = frozenset(
    {"za", "zac", "zae", "zi", "zone", "parc", "bp", "cs", "hameau", "lieu-dit", "lotissement", "residence"}
)
_ACCENTED_WORDS: dict[str, str] = {
    fold(word): word
    for word in (
        "électricité",
        "électrique",
        "électriques",
        "électricien",
        "électriciens",
        "électro",
        "électronique",
        "électrotechnique",
        "énergie",
        "énergies",
        "énergétique",
        "associé",
        "associés",
        "bâtiment",
        "bâtiments",
        "rénovation",
        "rénovations",
        "société",
        "sécurité",
        "réseau",
        "réseaux",
        "dépannage",
        "réparation",
        "réparations",
        "général",
        "générale",
        "frères",
        "père",
        "établissements",
        "éts",
        "élagage",
        "élagueur",
        "aménagement",
        "aménagements",
        "mécanique",
        "étanchéité",
        "création",
        "créations",
        "décoration",
        "éclairage",
        "études",
        "métallerie",
        "maçonnerie",
        "façade",
        "façades",
        "écologique",
        "éco",
        "système",
        "systèmes",
        "génie",
        "allée",
        "allées",
        "chaussée",
        "cité",
        "résidence",
        "église",
        "école",
        "écoles",
        "étang",
        "étangs",
        "château",
        "maréchal",
        "président",
        "côte",
        "côtes",
        "hôtel",
        "hôpital",
        "libération",
        "république",
        "liberté",
        "égalité",
        "pré",
        "prés",
        "abbé",
        "étable",
        "forêt",
        "vallée",
        "rivière",
        "gué",
        "prieuré",
        "écluse",
        "étoile",
        "île",
        "chênes",
        "hêtres",
        "genêts",
        "bruyères",
        "carrières",
        "érables",
        "mûriers",
        "métairie",
    )
}
_SOLE_TRADER_NAME_WORDS: int = 2
_BUSINESS_WORDS: frozenset[str] = frozenset(
    {
        "garage",
        "chez",
        "atelier",
        "ateliers",
        "entreprise",
        "maison",
        "groupe",
        "agence",
        "cabinet",
        "espace",
        "elec",
        "plomberie",
        "chauffage",
        "renov",
        "service",
        "services",
        "habitat",
        "jardin",
        "jardins",
        "paysage",
        "paysages",
        "clim",
        "auto",
        "pro",
    }
)
_ACRONYM_NAME_MAX_CHARS: int = 4
_VOWEL_RE: re.Pattern[str] = re.compile(r"[aeiouy]")
_WORD_PIECES_RE: re.Pattern[str] = re.compile(r"([-'’&.])")
_PIECE_SEPARATORS: frozenset[str] = frozenset("-'’&.")
_APOSTROPHES: frozenset[str] = frozenset("'’")
_DOTTED_LETTERS_RE: re.Pattern[str] = re.compile(r"\b[A-Za-z](?:\.[A-Za-z])+\b\.?")
_ELISION_WITHOUT_APOSTROPHE_RE: re.Pattern[str] = re.compile(r"\b([DL])\s+(?=[AEIOUYH])", re.IGNORECASE)


class RegisterSpelling:
    """Writes the names, streets and addresses a French register gives in capitals."""

    @classmethod
    def business_name(cls, registered_name: str) -> str:
        """
        A business's registered name as a site shows it.

        A single short word is an acronym (« ERE »). A sole trader is registered « NOM PRÉNOM »: two words, the
        second a common first name, the first no business word (« LEFEVRE CEDRIC » is « Cédric Lefevre », « GARAGE
        MARTIN » stays a garage).

        Args:
            registered_name: The name as the register writes it.

        Returns:
            The name in French casing, with the accents of its common words and of its first names.
        """
        words = registered_name.split()
        if len(words) == 1 and len(words[0]) <= _ACRONYM_NAME_MAX_CHARS and words[0].isupper():
            return words[0]
        if cls._is_sole_trader_name(words):
            family_name, first_name = words
            return f"{cls._spelled_text(first_name)} {cls._spelled_text(family_name)}"
        return cls._spelled_text(registered_name)

    @classmethod
    def address(cls, registered_street: str | None, postal_code: str | None, commune: str) -> str | None:
        """
        A registered address as a site shows it, its postal code and commune after the street.

        Args:
            registered_street: The street as the register writes it (« RUE DE L'ORNE - ZI »).
            postal_code: The register's postal code.
            commune: The commune's official spelling.

        Returns:
            « Rue de l'Orne, ZI, 14570 Saint-Rémy »; the street alone without a postal code, None without either.
        """
        street = cls.street(registered_street or "")
        if not postal_code or postal_code in street:
            return street or None
        place = f"{postal_code} {commune}".strip()
        return f"{street}, {place}" if street else place

    @classmethod
    def street(cls, registered_street: str) -> str:
        """
        A registered street in French casing, each part of the address after a comma.

        « 70 RUE DU MONT PIED ZAC LES ARDOISIERES » is « 70 rue du Mont Pied, ZAC Les Ardoisieres », « RUE DE L'ORNE -
        ZI » « Rue de l'Orne, ZI », « HAMEAU D ENGLESQUEVILLE » « Hameau d'Englesqueville ».

        Args:
            registered_street: The street as the register writes it.

        Returns:
            The street, empty for an empty one.
        """
        text = registered_street.strip().replace(" - ", ", ")
        text = _DOTTED_LETTERS_RE.sub(lambda match: match.group(0).replace(".", ""), text)
        text = _ELISION_WITHOUT_APOSTROPHE_RE.sub(r"\1'", text)
        return cls._spelled_text(text, is_street=True)

    @classmethod
    def _is_sole_trader_name(cls, words: list[str]) -> bool:
        """Whether a registered name is « NOM PRÉNOM »: two words, a common first name after a family name."""
        if len(words) != _SOLE_TRADER_NAME_WORDS:
            return False
        family_word = fold(words[0])
        is_business_word = family_word in _BUSINESS_WORDS or family_word in _ACCENTED_WORDS
        is_family_name_shaped = family_word.replace("-", "").isalpha() and _VOWEL_RE.search(family_word) is not None
        return (
            not is_business_word
            and family_word not in _CAPITALS_WORDS
            and is_family_name_shaped
            and GivenNames.is_common_given_name(words[1])
        )

    @classmethod
    def _spelled_text(cls, text: str, *, is_street: bool = False) -> str:
        """Every word of a text in French casing; in a street, a comma before each new part of the address."""
        spelled_tokens: list[str] = []
        previous_word = ""
        follows_house_number = False
        for token in text.split():
            word = token.rstrip(",")
            folded = fold(word)
            starts_part = not spelled_tokens or spelled_tokens[-1].endswith(",")
            follows_link_word = previous_word in _LINK_WORDS or previous_word in _ARTICLES
            is_new_part = is_street and folded in _ADDRESS_PART_MARKERS and not follows_link_word
            if is_new_part and not starts_part:
                spelled_tokens[-1] += ","
                starts_part = True
            is_after_house_number = is_street and follows_house_number
            is_lowercase = is_after_house_number and (folded in _STREET_TYPES or folded in _HOUSE_NUMBER_SUFFIXES)
            spelled = cls._spelled_word(
                word, starts_part=starts_part, follows_link_word=previous_word in _LINK_WORDS, is_lowercase=is_lowercase
            )
            trailing_commas = token[len(word) :]
            spelled_tokens.append(spelled + trailing_commas)
            follows_house_number = word.isdigit() or (follows_house_number and folded in _HOUSE_NUMBER_SUFFIXES)
            previous_word = folded
        return " ".join(spelled_tokens)

    @classmethod
    def _spelled_word(cls, word: str, *, starts_part: bool, follows_link_word: bool, is_lowercase: bool) -> str:
        """
        One word in French casing, piece by piece: « SAINT-AMAND », « PONT-D'OUILLY », « ENE'RJ », « C&JELEC ».

        After an elided « d' » or « l' » the piece is capitalized; after any other apostrophe it stays in lowercase.
        """
        pieces = [piece for piece in _WORD_PIECES_RE.split(word) if piece]
        spelled_pieces: list[str] = []
        for position, piece in enumerate(pieces):
            if piece in _PIECE_SEPARATORS:
                spelled_pieces.append(piece)
                continue
            separator_before = pieces[position - 1] if position > 0 else ""
            piece_before = fold(pieces[position - 2]) if position > 1 else ""
            separator_after = pieces[position + 1] if position + 1 < len(pieces) else ""
            if separator_before in _APOSTROPHES and piece_before not in _ELIDED_WORDS:
                spelled_pieces.append(piece.lower())
                continue
            is_first_piece = starts_part and position == 0
            is_elided = separator_after in _APOSTROPHES and fold(piece) in _ELIDED_WORDS
            spelled_pieces.append(
                cls._spelled_piece(
                    piece,
                    is_first=is_first_piece,
                    follows_link_word=follows_link_word if position == 0 else piece_before in _LINK_WORDS,
                    is_lowercase=is_lowercase or (is_elided and not is_first_piece),
                )
            )
        return "".join(spelled_pieces)

    @staticmethod
    def _spelled_piece(piece: str, *, is_first: bool, follows_link_word: bool, is_lowercase: bool) -> str:
        """One piece of a word: a capitals word, a lowercase one, an acronym without vowel, or a capitalized word."""
        folded = fold(piece)
        if folded in _CAPITALS_WORDS:
            return piece.upper()
        is_first_name = GivenNames.is_common_given_name(piece)
        spelled = _ACCENTED_WORDS.get(folded) or (GivenNames.usual_spelling(piece) if is_first_name else None) or piece
        is_link_word = folded in _LINK_WORDS or (follows_link_word and folded in _ARTICLES)
        if is_lowercase or (is_link_word and not is_first):
            return spelled.lower()
        if folded.isalpha() and not _VOWEL_RE.search(folded):
            return piece.upper()
        return spelled[:1].upper() + spelled[1:].lower()
