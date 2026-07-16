"""Email greeting rules — Léo's decisions (2026-07-16).

  - first name known            → « Bonjour Léo »         (FIRST NAME ONLY —
                                    never « Bonjour Léo Guillaume », it reads
                                    like a mail-merge)
  - nothing known               → « Bonjour »
  - last name only, gender SURE → « Bonjour M. Guillaume » / « Bonjour Mme … »
  - last name only, no gender   → « Bonjour »              (a wrong civility is
                                    worse than a neutral greeting)

The returned string never ends with punctuation — templates add their own
comma (« {salutation}, »).
"""
from __future__ import annotations

from typing import Optional

from services.decision_maker.normalize import title_case_name


def build_greeting(
    first_name: Optional[str], last_name: Optional[str], gender: Optional[str]
) -> str:
    """Build the salutation line for a (possibly partial) resolved contact.

    Args:
        first_name: Resolved first name, or None.
        last_name: Resolved last name, or None.
        gender: 'M' / 'F' when known — only used for the last-name-only case.

    Returns:
        The greeting, e.g. « Bonjour Léo » — always safe, never a company word.
    """
    first = title_case_name(first_name)
    last = title_case_name(last_name)

    if first:
        return f"Bonjour {first}"
    if last and gender in ("M", "F"):
        civility = "M." if gender == "M" else "Mme"
        return f"Bonjour {civility} {last}"
    return "Bonjour"
