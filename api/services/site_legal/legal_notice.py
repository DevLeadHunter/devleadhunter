"""The identity section of a site's legal page: who publishes the site, who answers for it, who hosts it."""

from __future__ import annotations

import re

from schemas.site_legal_notice import SiteLegalBlock, SiteLegalLine, SiteLegalSection
from services.country_profiles import CountryProfile, CountryProfiles
from services.site_legal.hosting import SITE_HOSTING_PROVIDER
from services.site_legal.lines import SiteLegalLines
from services.site_legal.sources import DEMO_PUBLISHER_COUNTRY_CODE, SiteLegalSources

_FRANCE_CODE = "FR"
_FRENCH_COMPANY_ID_DIGITS = 9
_FRENCH_ESTABLISHMENT_ID_DIGITS = 14
_FRENCH_REGISTRY_ID_LENGTHS = frozenset({_FRENCH_COMPANY_ID_DIGITS, _FRENCH_ESTABLISHMENT_ID_DIGITS})
_NON_DIGIT = re.compile(r"\D")


class LegalNoticeBuilder:
    """Builds the « Mentions légales » section of a site (« Impressum », « Renseignements sur l'entreprise »).

    A delivered site is published by the business: its identity comes first, closed by the publication
    director where the country's law asks for one, then the host. A demo is published by the
    DevLeadHunter user who prepared it, established in France: the notice names that publisher with
    their SIRET and their director under French law, then the business the demo presents and the host.
    """

    @classmethod
    def build(cls, sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalSection:
        """
        Build the identity section of one site.

        Args:
            sources: The facts of the site.
            lines: The line writer of the site's country.

        Returns:
            The section, with every block that has at least one known fact.
        """
        facts = sources.country.site_legal
        if sources.is_demo:
            publisher_rules = CountryProfiles.get(DEMO_PUBLISHER_COUNTRY_CODE).site_legal
            blocks = [
                cls._demo_publisher_block(sources, lines, publisher_rules.is_publication_director_required),
                cls._business_block(lines.localize("Entreprise présentée"), sources, lines, director=None),
            ]
            is_host_disclosure_required = publisher_rules.is_host_disclosure_required
        else:
            director = sources.business.publication_director if facts.is_publication_director_required else None
            blocks = [cls._business_block(facts.publisher_heading, sources, lines, director=director)]
            is_host_disclosure_required = facts.is_host_disclosure_required
        if is_host_disclosure_required:
            blocks.append(cls._host_block(lines))
        return SiteLegalSection(
            anchor=SiteLegalLines.anchor(facts.legal_notice_title),
            title=facts.legal_notice_title,
            blocks=[block for block in blocks if block.lines],
        )

    @classmethod
    def _business_block(
        cls, heading: str, sources: SiteLegalSources, lines: SiteLegalLines, *, director: str | None
    ) -> SiteLegalBlock:
        """The business's identity: name, address, contacts, identifiers, licence, then its director if any."""
        business = sources.business
        country = sources.country
        license_label = business.professional_license_label or "Licence professionnelle"
        return SiteLegalBlock(
            heading=heading,
            kind="identity",
            lines=[
                *lines.plain(business.name),
                *lines.value("Nom commercial", business.trade_name),
                *lines.plain(business.address),
                *lines.phone(business.phone, country.code),
                *lines.email(business.email),
                *lines.value(
                    cls._legal_id_label(country, business.legal_id), cls._shown_legal_id(country, business.legal_id)
                ),
                *lines.value(country.site_legal.vat_number_label, business.vat_number),
                *lines.value(license_label, business.professional_license_number),
                *lines.value("Directeur de la publication", director),
            ],
        )

    @classmethod
    def _demo_publisher_block(
        cls, sources: SiteLegalSources, lines: SiteLegalLines, is_publication_director_required: bool
    ) -> SiteLegalBlock:
        """The DevLeadHunter user who publishes the demo, as their profile states them, director of its content."""
        publisher = sources.publisher
        heading = lines.localize("Éditeur de la démonstration")
        if publisher is None:
            return SiteLegalBlock(heading=heading, kind="identity", lines=[])
        director = publisher.name if is_publication_director_required else None
        return SiteLegalBlock(
            heading=heading,
            kind="identity",
            lines=[
                *lines.plain(publisher.company_name),
                *lines.plain(publisher.person_name),
                *lines.address(publisher.postal_address),
                *lines.phone(publisher.phone, DEMO_PUBLISHER_COUNTRY_CODE),
                *lines.email(publisher.email),
                *lines.website(publisher.website_url),
                *lines.value("SIRET", cls._grouped_french_id(publisher.siret)),
                *lines.value("Directeur de la publication", director),
            ],
        )

    @staticmethod
    def _host_block(lines: SiteLegalLines) -> SiteLegalBlock:
        """The provider hosting every generated site, with the phone number the French notice requires."""
        host = SITE_HOSTING_PROVIDER
        return SiteLegalBlock(
            heading=lines.localize("Hébergeur"),
            kind="identity",
            lines=[
                SiteLegalLine(text=host.name),
                SiteLegalLine(text=host.address),
                SiteLegalLine(label=lines.localize("Téléphone"), text=host.phone, href=f"tel:{host.phone_e164}"),
                *lines.website(host.website_url),
            ],
        )

    @staticmethod
    def _legal_id_label(country: CountryProfile, legal_id: str | None) -> str:
        """The name of the business identifier; a French one of 14 digits is an establishment's SIRET."""
        digits = _NON_DIGIT.sub("", legal_id or "")
        if country.code == _FRANCE_CODE and len(digits) == _FRENCH_ESTABLISHMENT_ID_DIGITS:
            return "SIRET"
        return country.site_legal.legal_id_label

    @classmethod
    def _shown_legal_id(cls, country: CountryProfile, legal_id: str | None) -> str | None:
        """The business identifier as published: a French SIREN or SIRET in its usual groups, any other as given."""
        return cls._grouped_french_id(legal_id) if country.code == _FRANCE_CODE else legal_id

    @staticmethod
    def _grouped_french_id(legal_id: str | None) -> str | None:
        """A SIREN or SIRET written in its usual groups (« 988 307 906 00020 »), anything else as given."""
        digits = _NON_DIGIT.sub("", legal_id or "")
        if len(digits) not in _FRENCH_REGISTRY_ID_LENGTHS:
            return legal_id
        return " ".join(group for group in (digits[:3], digits[3:6], digits[6:9], digits[9:]) if group)
