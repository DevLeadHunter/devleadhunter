"""Builders of the text of a legal block: lines in the country's words, linked contacts, section anchors."""

from __future__ import annotations

import re
import unicodedata

from schemas.site_legal_notice import SiteLegalLine
from services.regional_lexicon import RegionalLexicon
from services.sms.phone_normalizer import to_e164

_NON_ANCHOR_CHARACTERS = re.compile(r"[^a-z0-9]+")
_HYPHENATED_EMAIL_WORD = re.compile(r"\b([eE])-(mails?)\b")
_NON_BREAKING_HYPHEN = "‑"
_DOUBLED_PERIOD = re.compile(r"(?<!\.)\.\.(?!\.)")


class SiteLegalLines:
    """Writes the lines of one site's legal block in its country's words, skipping every unknown fact."""

    def __init__(self, country: str) -> None:
        self._country = country

    def localize(self, template: str, **facts: str) -> str:
        """
        Write a sentence in the country's words, then fill in its facts.

        The template is localized before the facts go in, so a business name is never rewritten
        (« Mail Coiffure » keeps its name in Québec). « e-mail » keeps its hyphen unbreakable, so a
        line never ends on « e- », and a name ending a sentence on its own period (« Toitures Gagnon
        inc. ») does not get a second one.

        Args:
            template: The French sentence, its facts as ``{placeholders}``.
            **facts: The values of the placeholders.

        Returns:
            The sentence, ready to show.
        """
        localized = RegionalLexicon.localize(template, self._country)
        unbreakable = _HYPHENATED_EMAIL_WORD.sub(rf"\1{_NON_BREAKING_HYPHEN}\2", localized)
        return _DOUBLED_PERIOD.sub(".", unbreakable.format(**facts))

    def sentence(self, template: str, href: str | None = None, **facts: str) -> SiteLegalLine:
        """A sentence line, linked when ``href`` is given."""
        return SiteLegalLine(text=self.localize(template, **facts), href=href)

    def value(self, label: str, text: str | None) -> list[SiteLegalLine]:
        """A labelled value, or nothing when the value is unknown."""
        if not text:
            return []
        return [SiteLegalLine(label=self.localize(label), text=text)]

    @staticmethod
    def plain(text: str | None) -> list[SiteLegalLine]:
        """An unlabelled fact (a name, an address), or nothing when it is unknown."""
        if not text:
            return []
        return [SiteLegalLine(text=text)]

    def email(self, email: str | None) -> list[SiteLegalLine]:
        """An email address opening the visitor's mail app, or nothing."""
        if not email:
            return []
        return [SiteLegalLine(label=self.localize("E-mail"), text=email, href=f"mailto:{email}")]

    def phone(self, phone: str | None, number_country: str) -> list[SiteLegalLine]:
        """
        A phone number, dialled in international form when it is recognised, or nothing.

        Args:
            phone: The number as displayed.
            number_country: The country whose national form the number may be written in.

        Returns:
            The line, or nothing for an unknown number.
        """
        if not phone:
            return []
        international = to_e164(phone, country=number_country)
        href = f"tel:{international}" if international else None
        return [SiteLegalLine(label=self.localize("Téléphone"), text=phone, href=href)]

    def website(self, url: str | None) -> list[SiteLegalLine]:
        """A website shown without its scheme and linked to itself, or nothing."""
        if not url:
            return []
        href = url if url.startswith(("http://", "https://")) else f"https://{url}"
        without_scheme = href.removeprefix("https://").removeprefix("http://")
        shown_address = without_scheme.removeprefix("www.").removesuffix("/")
        return [SiteLegalLine(label=self.localize("Site"), text=shown_address, href=href)]

    @staticmethod
    def anchor(title: str) -> str:
        """The anchor of a section: its title in lower-case ASCII words joined by hyphens (« mentions-legales »)."""
        letters_and_accents = unicodedata.normalize("NFKD", title.lower())
        without_accents = letters_and_accents.encode("ascii", "ignore").decode("ascii")
        return _NON_ANCHOR_CHARACTERS.sub("-", without_accents).strip("-")
