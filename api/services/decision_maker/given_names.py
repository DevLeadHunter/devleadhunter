"""
Given names — the first names people are given in France, Québec and Switzerland, and the sex their bearers have.

The list (given_names.tsv) comes from the official birth statistics of France and Québec, plus the names of
communities they count too few of; scripts/build_given_names.py rebuilds it. A name few people are given is
often a last name (« Marty », « Roy »): only a common one tells where a last name stops.
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from services.decision_maker.normalize import fold

_LIST_PATH: Path = Path(__file__).with_name("given_names.tsv")
_SEXES: frozenset[str] = frozenset({"M", "F"})
_COMMON_MARK: str = "1"


class GivenNames:
    """Tells whether a word is a first name people are given, how common it is, and the sex its bearers have."""

    _sex_by_name: ClassVar[dict[str, str] | None] = None
    _common_names: ClassVar[frozenset[str]] = frozenset()

    @classmethod
    def is_given_name(cls, word: str | None) -> bool:
        """
        Whether a word is a first name people are given (« Franck », « Jean-Pierre », « Arben », « Marty »).

        Args:
            word: A word, in any case and with or without accents.

        Returns:
            True when the list knows it.
        """
        return fold(word or "") in cls._names()

    @classmethod
    def is_common_given_name(cls, word: str | None) -> bool:
        """
        Whether a word is a first name many people are given, rarely a last name (« Franck », not « Marty »).

        Args:
            word: A word, in any case and with or without accents.

        Returns:
            True when the list knows it as a common first name.
        """
        cls._names()
        return fold(word or "") in cls._common_names

    @classmethod
    def sex_of(cls, word: str | None) -> str | None:
        """
        The sex nearly all bearers of a first name have.

        Args:
            word: A first name, in any case and with or without accents.

        Returns:
            « M » or « F »; None for a name both sexes bear (« Dominique ») or an unknown one.
        """
        sex = cls._names().get(fold(word or ""))
        return sex if sex in _SEXES else None

    @classmethod
    def _names(cls) -> dict[str, str]:
        """The sex of every listed name (« M », « F », « X » for both), read once with the common ones."""
        if cls._sex_by_name is None:
            rows = [line.split("\t") for line in _LIST_PATH.read_text(encoding="utf-8").splitlines() if line]
            cls._common_names = frozenset(name for name, _, common in rows if common == _COMMON_MARK)
            cls._sex_by_name = {name: sex for name, sex, _ in rows}
        return cls._sex_by_name
