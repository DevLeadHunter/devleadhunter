"""Regional French: rewrite a text in the words a prospect's country uses.

The software writes one French (emails, SMS, site copy). A Québécois reads « soumission » where a
French artisan reads « devis », « courriel » for « e-mail », « cellulaire » for « portable ». Rather
than a template per country, each :class:`~services.country_profiles.CountryProfile` carries a small
dictionary and this service applies it at TWO places only: the rendered body of an email or an SMS,
and the text fields of a generated site. A country without a lexicon (France, Switzerland…) is left
untouched, character for character.

Rules: whole words only, case kept (« Devis » → « Soumission », « DEVIS » → « SOUMISSION »), plural
kept (« e-mails » → « courriels », « des devis » → « des soumissions »), and the determiner or the
usual adjective agrees when the new word changes gender (« un devis gratuit » → « une soumission
gratuite »). HTML tags, URLs, email addresses, template variables and words glued to others
(« Gmail », « mailto: ») are never rewritten.

A prospect's substitution map (:class:`~services.email_variables.EmailVariables`,
:class:`~services.sms_variables.SmsVariables`) carries his country under :attr:`RegionalLexicon.COUNTRY_KEY`,
so every renderer of a template localizes what it renders without its callers passing the country.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import ClassVar

from services.country_profiles import CountryProfile, CountryProfiles


class RegionalLexicon:
    """Applies a country's word swaps to a French text, leaving every other country's text intact."""

    # « @ » keeps this entry of a substitution map out of reach of any « {variable} » of a template.
    COUNTRY_KEY: ClassVar[str] = "@pays"
    # Spans never rewritten: HTML tags, URLs, email addresses and ``{variables}`` not yet substituted.
    _PROTECTED_SPAN: ClassVar[re.Pattern[str]] = re.compile(
        r"(<[^>]*>|https?://[^\s<]+|www\.[^\s<]+|[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\{[a-zA-Z_][a-zA-Z0-9_]*\})"
    )
    # The word (and its optional whitespace) right before a swapped word, read for its number and gender.
    _PRECEDING_WORD: ClassVar[re.Pattern[str]] = re.compile(r"([\w'’]+)(\s+)$")
    # What follows a swapped word, candidate for a gender agreement: an optional copula (« est »,
    # « est-il »), an optional adverb (« vraiment »), then the adjective.
    _FOLLOWING_WORDS: ClassVar[re.Pattern[str]] = re.compile(
        r"(\s+)(?:(est-il|sont-ils|est|sont)(\s+))?"
        r"(?:(vraiment|très|aussi|toujours|bien|déjà|encore|donc|plus|tout)(\s+))?([^\W\d_]+)"
    )
    # A further adjective chained to the first (« écrite, détaillée et claire »).
    _CHAINED_ADJECTIVE: ClassVar[re.Pattern[str]] = re.compile(r"(,\s*|\s+(?:et|ou)\s+)([^\W\d_]+)")
    _FEMININE_COPULAS: ClassVar[dict[str, str]] = {"est-il": "est-elle", "sont-ils": "sont-elles"}
    # An article elided before a vowel (« l'e-mail », « d'e-mail ») and the demonstrative « cet »: both
    # take their full form once the new word starts with a consonant (« le courriel », « ce courriel »).
    _ELIDED_ARTICLE: ClassVar[re.Pattern[str]] = re.compile(r"\b(l|d|qu|c|s|n|m|t|j)['’]$", re.IGNORECASE)
    _DEMONSTRATIVE_BEFORE_VOWEL: ClassVar[re.Pattern[str]] = re.compile(r"\b(cet)(\s+)$", re.IGNORECASE)
    _FULL_ARTICLES: ClassVar[dict[str, str]] = {
        "l": "le",
        "d": "de",
        "qu": "que",
        "c": "ce",
        "s": "se",
        "n": "ne",
        "m": "me",
        "t": "te",
        "j": "je",
    }
    _VOWELS: ClassVar[str] = "aeiouyàâäéèêëîïôöùûüÿh"
    # Determiners announcing a plural, the only way to count an invariable word like « devis ».
    _PLURAL_DETERMINERS: ClassVar[frozenset[str]] = frozenset(
        {
            "des",
            "les",
            "aux",
            "ces",
            "mes",
            "tes",
            "ses",
            "nos",
            "vos",
            "leurs",
            "plusieurs",
            "quelques",
            "certains",
            "deux",
            "trois",
            "quatre",
            "cinq",
            "dix",
        }
    )
    _FEMININE_DETERMINERS: ClassVar[dict[str, str]] = {
        "un": "une",
        "le": "la",
        "ce": "cette",
        "cet": "cette",
        "du": "de la",
        "au": "à la",
        "mon": "ma",
        "ton": "ta",
        "son": "sa",
        "quel": "quelle",
        "aucun": "aucune",
    }
    # Adjectives and participles that follow the swapped noun, masculine singular → feminine singular
    # (« un devis gratuit » → « une soumission gratuite », « le week-end prochain » → « la fin de semaine prochaine »).
    _FEMININE_ADJECTIVES: ClassVar[dict[str, str]] = {
        "gratuit": "gratuite",
        "détaillé": "détaillée",
        "personnalisé": "personnalisée",
        "précis": "précise",
        "clair": "claire",
        "écrit": "écrite",
        "transparent": "transparente",
        "chiffré": "chiffrée",
        "complet": "complète",
        "validé": "validée",
        "signé": "signée",
        "accepté": "acceptée",
        "envoyé": "envoyée",
        "demandé": "demandée",
        "établi": "établie",
        "compris": "comprise",
        "inclus": "incluse",
        "prochain": "prochaine",
        "dernier": "dernière",
        "suivant": "suivante",
    }
    # « tous les week-ends » → « toutes les fins de semaine »: the quantifier before a feminine plural.
    _MASCULINE_PLURAL_QUANTIFIER: ClassVar[re.Pattern[str]] = re.compile(
        r"\b(tous)(\s+(?:les|ces|mes|tes|ses|nos|vos|leurs)\s+)$", re.IGNORECASE
    )
    # Replacement words that are feminine where the French word was masculine.
    _FEMININE_WORDS: ClassVar[frozenset[str]] = frozenset({"soumission", "fin de semaine"})
    _patterns: ClassVar[dict[str, re.Pattern[str]]] = {}

    @classmethod
    def localize(cls, text: str | None, country: str | None) -> str:
        """Rewrite ``text`` with the regional words of ``country``.

        Args:
            text: Any French text, plain or HTML; ``None`` reads as empty.
            country: ISO code of the reader's country; a country without a lexicon, an unknown or a
                closed one leaves the text untouched.

        Returns:
            The localized text, or the input unchanged when nothing applies.
        """
        if not text:
            return text or ""
        profile = CountryProfiles.get(country)
        if not profile.lexicon:
            return text
        pattern = cls._pattern_for(profile)
        spans = cls._PROTECTED_SPAN.split(text)
        # ``split`` with a capturing group alternates free text (even indexes) and protected spans.
        return "".join(
            span if index % 2 else cls._localize_span(span, pattern, profile.lexicon)
            for index, span in enumerate(spans)
        )

    @classmethod
    def localize_rendered(cls, text: str, variables: Mapping[str, str]) -> str:
        """Rewrite a template just rendered from a prospect's substitution map, in the country the map carries.

        Args:
            text: The rendered subject or body.
            variables: The substitution map it was rendered from.

        Returns:
            The localized text; unchanged when the map carries no country (a sample preview, a hand-built map).
        """
        return cls.localize(text, variables.get(cls.COUNTRY_KEY))

    @classmethod
    def _pattern_for(cls, profile: CountryProfile) -> re.Pattern[str]:
        """The whole-word regex of a profile's lexicon (longest keys first, optional plural « s »), cached."""
        pattern = cls._patterns.get(profile.code)
        if pattern is None:
            keys = sorted(profile.lexicon, key=len, reverse=True)
            alternation = "|".join(re.escape(key) for key in keys)
            # A hyphen glues a word to a compound (« portable-pro »); a key may carry its own (« e-mail », « week-end »).
            pattern = re.compile(rf"(?<!-)\b({alternation})(s?)\b(?!-)", re.IGNORECASE)
            cls._patterns[profile.code] = pattern
        return pattern

    @classmethod
    def _localize_span(cls, span: str, pattern: re.Pattern[str], lexicon: dict[str, str]) -> str:
        """Swap every lexicon word of a free-text span, agreeing the words around it."""
        pieces: list[str] = []
        cursor = 0
        for match in pattern.finditer(span):
            if match.start() < cursor:
                continue
            word, plural_suffix = match.group(1), match.group(2)
            replacement = lexicon[word.lower()]
            before = span[cursor : match.start()]
            is_invariable = word.lower().endswith("s")
            is_plural = bool(plural_suffix) or (is_invariable and cls._is_preceded_by_plural(before))
            turns_feminine = replacement in cls._FEMININE_WORDS
            if turns_feminine:
                before = cls._feminize_quantifier(before) if is_plural else cls._feminize_determiner(before)
            if word[0].lower() in cls._VOWELS and replacement[0].lower() not in cls._VOWELS:
                before = cls._undo_elision(before, feminine=turns_feminine)
            pieces.append(before)
            pieces.append(cls._match_case(word, cls._plural(replacement) if is_plural else replacement))
            cursor = match.end()
            if turns_feminine:
                agreed = cls._agree_following_words(span, cursor, plural=is_plural)
                if agreed is not None:
                    pieces.append(agreed[0])
                    cursor = agreed[1]
        pieces.append(span[cursor:])
        return "".join(pieces)

    @classmethod
    def _agree_following_words(cls, span: str, cursor: int, *, plural: bool) -> tuple[str, int] | None:
        """Feminize the copula and the adjectives after a word that turned feminine.

        Args:
            span: The free-text span being rewritten.
            cursor: Where the swapped word ends.
            plural: Whether the swapped word is plural (« week-ends compris » → « fins de semaine comprises »).

        Returns:
            ``(rewritten text, new cursor)`` when something agrees, ``None`` when nothing follows that must.
        """
        following = cls._FOLLOWING_WORDS.match(span, cursor)
        if following is None:
            return None
        copula, adverb, adjective = following.group(2), following.group(4), following.group(6)
        feminine_copula = cls._FEMININE_COPULAS.get(copula.lower()) if copula else None
        feminine_adjective = cls._feminine_adjective(adjective, plural=plural)
        if feminine_copula is None and feminine_adjective is None:
            return None
        rewritten = following.group(1)
        if copula:
            rewritten += (cls._match_case(copula, feminine_copula) if feminine_copula else copula) + following.group(3)
        if adverb:
            rewritten += adverb + following.group(5)
        rewritten += feminine_adjective or adjective
        end = following.end()
        while feminine_adjective is not None:
            chained = cls._CHAINED_ADJECTIVE.match(span, end)
            feminine_adjective = cls._feminine_adjective(chained.group(2), plural=plural) if chained else None
            if chained is None or feminine_adjective is None:
                break
            rewritten += chained.group(1) + feminine_adjective
            end = chained.end()
        return rewritten, end

    @classmethod
    def _feminine_adjective(cls, adjective: str, *, plural: bool) -> str | None:
        """The feminine of a known adjective, plural when the noun or the adjective itself is (« gratuits »).

        Args:
            adjective: The adjective as written, any case.
            plural: Whether the noun it qualifies is plural.

        Returns:
            The agreed adjective in the case of the input, ``None`` when it is not a known one.
        """
        lowered = adjective.lower()
        feminine = cls._FEMININE_ADJECTIVES.get(lowered)
        if feminine is None and lowered.endswith("s"):
            feminine = cls._FEMININE_ADJECTIVES.get(lowered[:-1])
            plural = feminine is not None
        if feminine is None:
            return None
        return cls._match_case(adjective, f"{feminine}s" if plural else feminine)

    @staticmethod
    def _plural(replacement: str) -> str:
        """The plural of a replacement: its head word takes the « s » (« soumissions », « fins de semaine »)."""
        head, separator, rest = replacement.partition(" ")
        return f"{head}s{separator}{rest}"

    @classmethod
    def _undo_elision(cls, before: str, *, feminine: bool) -> str:
        """Give an elided article or « cet » its full form, the new word starting with a consonant."""
        article = cls._ELIDED_ARTICLE.search(before)
        if article is not None:
            full = (
                "la" if feminine and article.group(1).lower() == "l" else cls._FULL_ARTICLES[article.group(1).lower()]
            )
            return before[: article.start()] + cls._match_case(article.group(1), full) + " "
        demonstrative = cls._DEMONSTRATIVE_BEFORE_VOWEL.search(before)
        if demonstrative is not None:
            return (
                before[: demonstrative.start()] + cls._match_case(demonstrative.group(1), "ce") + demonstrative.group(2)
            )
        return before

    @classmethod
    def _is_preceded_by_plural(cls, before: str) -> bool:
        """Whether the text ends with a determiner that announces a plural (« des », « vos »…)."""
        preceding = cls._PRECEDING_WORD.search(before)
        return preceding is not None and preceding.group(1).lower() in cls._PLURAL_DETERMINERS

    @classmethod
    def _feminize_quantifier(cls, before: str) -> str:
        """Turn « tous les » before a feminine plural into « toutes les », keeping the case."""
        quantifier = cls._MASCULINE_PLURAL_QUANTIFIER.search(before)
        if quantifier is None:
            return before
        return before[: quantifier.start()] + cls._match_case(quantifier.group(1), "toutes") + quantifier.group(2)

    @classmethod
    def _feminize_determiner(cls, before: str) -> str:
        """Turn a trailing masculine singular determiner into its feminine form, keeping its case."""
        preceding = cls._PRECEDING_WORD.search(before)
        if preceding is None:
            return before
        feminine = cls._FEMININE_DETERMINERS.get(preceding.group(1).lower())
        if feminine is None:
            return before
        return before[: preceding.start()] + cls._match_case(preceding.group(1), feminine) + preceding.group(2)

    @staticmethod
    def _match_case(source: str, replacement: str) -> str:
        """Give ``replacement`` the case of ``source`` (upper, capitalized or lower)."""
        if len(source) > 1 and source.isupper():
            return replacement.upper()
        if source[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement
