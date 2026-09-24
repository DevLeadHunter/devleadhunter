"""Accent- and case-insensitive folding of free text, shared by the keyword and stem matchers."""

from __future__ import annotations

import unicodedata


class TextNormalizer:
    """Folds free text so « Fermé », « FERME » and « ferme » compare equal."""

    @staticmethod
    def fold(value: str) -> str:
        """
        Lower-case a text and drop its diacritics.

        Args:
            value: Any text.

        Returns:
            The folded text (« Fermé » → « ferme »).
        """
        decomposed = unicodedata.normalize("NFD", value.lower())
        return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
