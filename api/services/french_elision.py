"""French elision and contraction of the word written before a template variable.

Templates write « le site de {entreprise} », « à {ville} », « que {prenom_receptionniste} ». Pasted as
is, some values break the French: « le site de Atelier Dupont », « le site de Le Jardin de Kyllian »,
« à Le Mans », « que Inès ». Every renderer of an email template applies this service to the template
BEFORE substituting its variables, with the substitution map it is about to use:

- « de » before a value starting with a vowel is elided: « d'Atelier Dupont », « d'Électricité Faure »;
- « de » before the article « Le » or « Les » contracts with it: « du Jardin de Kyllian »,
  « des Jardins Tournaisiens »; « à » does the same: « au Mans », « aux Herbiers »;
- « que » before a vowel is elided: « qu'Inès ».

Any other value keeps its word as written: « de La Bonne Frite », « de L'Oasis », « de 3D Rénovation »,
and « de Haut-Plateau » (most company and place names read their « h » aspirated, and « y » too:
« de Yannick »). A value that is not a word (a link, an HTML block, a price) is never touched. The
capital of the word is kept: « De {entreprise} » opening a sentence gives « D'Atelier Dupont ».
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import ClassVar


class FrenchElision:
    """Writes « de », « à » and « que » before a variable the way its value requires."""

    _WORD_BEFORE_VARIABLE: ClassVar[re.Pattern[str]] = re.compile(r"\b(de|De|à|À|que|Que) \{([a-zA-Z_][a-zA-Z0-9_]*)\}")
    _VOWEL_START: ClassVar[re.Pattern[str]] = re.compile(r"^[aeiouàâäéèêëîïôöùûü]", re.IGNORECASE)
    _CONTRACTING_ARTICLE: ClassVar[re.Pattern[str]] = re.compile(r"^(les?)\s+(?=\S)", re.IGNORECASE)
    _CONTRACTIONS: ClassVar[dict[tuple[str, str], str]] = {
        ("de", "le"): "du",
        ("de", "les"): "des",
        ("à", "le"): "au",
        ("à", "les"): "aux",
    }
    _ELIDING_WORDS: ClassVar[dict[str, str]] = {"de": "d'", "que": "qu'"}

    @classmethod
    def apply(cls, text: str, variables: Mapping[str, object]) -> str:
        """
        Rewrite each « de / à / que {variable} » of *text* for the value the variable will receive.

        Args:
            text: A template subject or body, its ``{variables}`` not yet substituted.
            variables: The substitution map the renderer is about to apply.

        Returns:
            The text with « d'Atelier Dupont », « du Jardin », « au Mans », « qu'Inès » written out; the
            words and variables that need no change are left for the substitution.
        """
        return cls._WORD_BEFORE_VARIABLE.sub(lambda match: cls._rewritten(match, variables), text)

    @classmethod
    def _rewritten(cls, match: re.Match[str], variables: Mapping[str, object]) -> str:
        """
        One « word {variable} » of the template, rewritten for the value of its variable.

        Args:
            match: The word and the variable name, as matched in the template.
            variables: The substitution map the renderer is about to apply.

        Returns:
            The joined form, or the matched text unchanged when the value is missing or needs nothing.
        """
        value: object = variables.get(match.group(2))
        if not isinstance(value, str) or not value:
            return match.group(0)
        return cls._joined(match.group(1), value) or match.group(0)

    @classmethod
    def _joined(cls, word: str, value: str) -> str | None:
        """
        *word* joined to *value* when French requires it.

        Args:
            word: « de », « à » or « que », capitalised or not.
            value: The value of the variable that follows it.

        Returns:
            The contracted or elided form, or None when the word stays as written.
        """
        lowered: str = word.lower()
        article: re.Match[str] | None = cls._CONTRACTING_ARTICLE.match(value)
        contraction: str | None = cls._CONTRACTIONS.get((lowered, article.group(1).lower())) if article else None
        if article and contraction:
            return f"{cls._with_case_of(word, contraction)} {value[article.end() :]}"
        elided: str | None = cls._ELIDING_WORDS.get(lowered)
        if elided and cls._VOWEL_START.match(value):
            return f"{cls._with_case_of(word, elided)}{value}"
        return None

    @staticmethod
    def _with_case_of(word: str, replacement: str) -> str:
        """*replacement* capitalised like *word* (« De » gives « D' », « Du »)."""
        return replacement[0].upper() + replacement[1:] if word[0].isupper() else replacement
