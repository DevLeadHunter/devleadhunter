"""
The person the prospect search read running the business — « Aurélie Exemple (Aurélie Paysages),
auto-entrepreneur » on a directory where tradespeople describe themselves.

A micro-entrepreneur often publishes no register entry: the page the search read is then the only one naming them.
Its word alone is a proposal; the business's own address spelling the same first and last name makes it usable
(« exempleaureliedu17@ » for Aurélie Exemple).
"""

from __future__ import annotations

import re

from services.decision_maker.given_names import GivenNames
from services.decision_maker.normalize import fold, infer_gender, title_case_name
from services.decision_maker.types import NameCandidate, ResolutionContext

_NAME_WORD_RE: re.Pattern[str] = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ'’-]+")
_NON_LETTERS_RE: re.Pattern[str] = re.compile(r"[^a-z]+")
_MIN_NAME_CHARS: int = 3
_SEARCH_OWNER_EVIDENCE_GROUP: str = "search_owner"


class SearchOwnerStrategy:
    """Supporting — the owner the prospect search read on a page about the business."""

    name = "search_owner"

    async def resolve(self, context: ResolutionContext) -> list[NameCandidate]:
        """Propose the owner the search read."""
        return self.candidates_of(context)

    def candidates_of(self, context: ResolutionContext) -> list[NameCandidate]:
        """
        The owner the search read, as a candidate (pure — testable).

        A proposal on the page's word alone; usable on its own when one of the business's addresses holds their
        first and last name, glued or not, in any order (« exempleaureliedu17@ »): the person and the business
        then name each other.
        """
        owner = context.searched_owner
        person = self.first_and_last_name(owner.name) if owner is not None else None
        if owner is None or person is None:
            return []
        first_name, last_name = person
        spelling_email = next(
            (email for email in context.emails if self.spells_person(email, first_name, last_name)), None
        )
        page_note = f" sur {owner.source}" if owner.source else ""
        email_note = f", et l'adresse mail « {spelling_email} » porte ce nom" if spelling_email else ""
        return [
            NameCandidate(
                first=first_name,
                last=last_name,
                gender=infer_gender(first_name),
                source=self.name,
                confidence=0.75 if spelling_email else 0.6,
                evidence_group=_SEARCH_OWNER_EVIDENCE_GROUP,
                provenance=f"Lu par la recherche de prospects{page_note}{email_note}",
                raw={"url": owner.url, "email": spelling_email},
                self_declared=spelling_email is not None,
            )
        ]

    @staticmethod
    def first_and_last_name(full_name: str) -> tuple[str, str] | None:
        """
        A person's first and last name, written first name first or last (« EXEMPLE Aurélie »).

        Args:
            full_name: The name as the page wrote it.

        Returns:
            The first and last name, or None when no common first name opens or closes it.
        """
        words = _NAME_WORD_RE.findall(full_name)
        if len(words) < 2:
            return None
        if GivenNames.is_common_given_name(words[0]):
            first_name, last_name = title_case_name(words[0]), title_case_name(" ".join(words[1:]))
        elif GivenNames.is_common_given_name(words[-1]):
            first_name, last_name = title_case_name(words[-1]), title_case_name(" ".join(words[:-1]))
        else:
            return None
        return (first_name, last_name) if first_name and last_name else None

    @staticmethod
    def spells_person(email: str, first_name: str, last_name: str) -> bool:
        """
        Whether the words before an address's « @ » hold a person's first and last name, glued or not, in any order.

        Args:
            email: One of the business's addresses.
            first_name: The person's first name.
            last_name: The person's last name.

        Returns:
            True when both names, of three letters at least, are in the address.
        """
        local_part = _NON_LETTERS_RE.sub("", fold(email.partition("@")[0]))
        names = [_NON_LETTERS_RE.sub("", fold(name)) for name in (first_name, last_name)]
        return all(len(name) >= _MIN_NAME_CHARS and name in local_part for name in names)
