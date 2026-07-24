"""Name normalisation + French first-name gender lookup.

Registries return names in UPPERCASE (« GUILLAUME Léo ») and websites in any
casing — everything is normalised to a clean title-case before storage, with
French particles kept lowercase (« de », « le »…).
"""

from __future__ import annotations

import re
import unicodedata

# Lowercase particles kept as-is inside a title-cased name.
_PARTICLES: frozenset[str] = frozenset({"de", "du", "des", "le", "la", "les", "d'", "l'", "van", "von", "da", "di"})

# Legal-form / company suffixes stripped when comparing company names.
_COMPANY_NOISE: frozenset[str] = frozenset(
    {
        "sarl",
        "sas",
        "sasu",
        "eurl",
        "sci",
        "sa",
        "snc",
        "ei",
        "eirl",
        "entreprise",
        "ets",
        "etablissements",
        "societe",
        "société",
        "auto",
        "ste",
        "monsieur",
        "madame",
        "m",
        "mme",
    }
)

# Compact gender lookup for common French first names — used ONLY for the
# « Bonjour M./Mme {Nom} » case (last name without first name). Deliberately
# conservative: an unknown first name yields no gender, hence a neutral greeting.
_MALE_FIRST_NAMES: frozenset[str] = frozenset(
    [
        "jean",
        "pierre",
        "michel",
        "andre",
        "philippe",
        "rene",
        "louis",
        "alain",
        "jacques",
        "bernard",
        "marcel",
        "daniel",
        "roger",
        "robert",
        "paul",
        "claude",
        "christian",
        "henri",
        "georges",
        "nicolas",
        "patrick",
        "antoine",
        "francois",
        "pascal",
        "eric",
        "david",
        "olivier",
        "stephane",
        "laurent",
        "frederic",
        "sebastien",
        "christophe",
        "thierry",
        "vincent",
        "julien",
        "alexandre",
        "thomas",
        "maxime",
        "romain",
        "kevin",
        "florian",
        "anthony",
        "jeremy",
        "mathieu",
        "guillaume",
        "benjamin",
        "lucas",
        "hugo",
        "leo",
        "theo",
        "nathan",
        "enzo",
        "louis",
        "gabriel",
        "raphael",
        "arthur",
        "jules",
        "adam",
        "liam",
        "noe",
        "sacha",
        "eliott",
        "marc",
        "luc",
        "yves",
        "gerard",
        "serge",
        "gilles",
        "bruno",
        "didier",
        "joel",
        "francis",
        "dominique",
        "remy",
        "fabrice",
        "gregory",
        "cedric",
        "ludovic",
        "damien",
        "aurelien",
        "quentin",
        "clement",
        "valentin",
        "baptiste",
        "martin",
        "simon",
        "victor",
        "axel",
        "mohamed",
        "karim",
        "mehdi",
        "rachid",
        "samir",
        "yanis",
        "geoffrey",
        "gregoire",
        "tanguy",
        "erwan",
        "loic",
        "mickael",
        "jonathan",
        "dylan",
        "bastien",
        "alexis",
    ]
)

_FEMALE_FIRST_NAMES: frozenset[str] = frozenset(
    [
        "marie",
        "jeanne",
        "francoise",
        "monique",
        "catherine",
        "nathalie",
        "isabelle",
        "sylvie",
        "anne",
        "martine",
        "jacqueline",
        "christiane",
        "nicole",
        "helene",
        "laurence",
        "sandrine",
        "valerie",
        "celine",
        "karine",
        "stephanie",
        "sophie",
        "aurelie",
        "julie",
        "camille",
        "emilie",
        "laura",
        "manon",
        "lea",
        "chloe",
        "emma",
        "sarah",
        "pauline",
        "mathilde",
        "lucie",
        "marion",
        "elodie",
        "audrey",
        "melanie",
        "delphine",
        "severine",
        "virginie",
        "patricia",
        "veronique",
        "brigitte",
        "danielle",
        "josiane",
        "yvette",
        "madeleine",
        "therese",
        "suzanne",
        "charlotte",
        "juliette",
        "louise",
        "alice",
        "clara",
        "ines",
        "jade",
        "lina",
        "mila",
        "rose",
        "eva",
        "anna",
        "lou",
        "zoe",
        "nadia",
        "samira",
        "fatima",
        "leila",
        "amina",
    ]
)


def fold(value: str) -> str:
    """Lowercase + strip accents + trim (comparison key)."""
    text = unicodedata.normalize("NFD", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.strip().lower()


def title_case_name(value: str | None) -> str | None:
    """Normalise a person-name fragment to clean title-case.

    Handles UPPERCASE registry output, hyphenated names (« jean-pierre » →
    « Jean-Pierre ») and French particles (« de la Tour » stays lowercase).
    """
    if not value or not value.strip():
        return None
    # Person names never legitimately carry parentheses — registries sometimes
    # append the commercial name (« LESNE (LESNE SERVICE) ») → drop it.
    value = re.sub(r"\([^)]*\)", " ", value)
    if not value.strip():
        return None
    words: list[str] = []
    for word in re.split(r"\s+", value.strip()):
        if not word:
            continue
        lower = word.lower()
        if lower in _PARTICLES and words:  # never lowercase the leading word
            words.append(lower)
            continue
        words.append("-".join(part[:1].upper() + part[1:].lower() for part in lower.split("-") if part))
    return " ".join(words) or None


def infer_gender(first_name: str | None) -> str | None:
    """Best-effort gender from a French first name ('M' / 'F' / None).

    Only the FIRST token is considered (« Jean-Pierre » → « jean »… actually
    the full hyphenated token is looked up first, then its head). Unknown →
    None, and callers must fall back to a neutral greeting.
    """
    if not first_name:
        return None
    key = fold(first_name).split(" ")[0]
    for probe in (key, key.split("-")[0]):
        if probe in _MALE_FIRST_NAMES:
            return "M"
        if probe in _FEMALE_FIRST_NAMES:
            return "F"
    return None


def company_tokens(name: str) -> set[str]:
    """Significant tokens of a company name (noise/legal forms removed)."""
    tokens = {t for t in re.split(r"[^a-z0-9]+", fold(name)) if len(t) > 1}
    return tokens - _COMPANY_NOISE


def company_similarity(a: str, b: str) -> float:
    """Token-overlap similarity between two company names (0..1)."""
    ta, tb = company_tokens(a), company_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def split_registry_full_name(full_name: str) -> tuple[str | None, str | None]:
    """Split a registry « NOM Prenom » (EI denomination) into (first, last).

    French registries write the LAST name in uppercase followed by the first
    name(s) — when that pattern is detected we use it; otherwise the safe
    guess is « first token = first name » only when there are exactly two.
    Parenthesized segments (« DUPONT Jean (PLOMBERIE DUPONT) ») are dropped.
    """
    cleaned = re.sub(r"\([^)]*\)", " ", full_name or "")
    parts = [p for p in re.split(r"\s+", cleaned.strip()) if p]
    if len(parts) < 2:
        return None, None
    uppercase = [p for p in parts if p.isupper() and len(p) > 1]
    lowercase_like = [p for p in parts if not p.isupper()]
    if uppercase and lowercase_like:
        return title_case_name(" ".join(lowercase_like)), title_case_name(" ".join(uppercase))
    if len(parts) == 2:
        # Ambiguous casing: registries order it « NOM Prénom » → assume that.
        return title_case_name(parts[1]), title_case_name(parts[0])
    return None, None
