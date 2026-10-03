"""The identity section of a site's legal page: who publishes the site, who answers for it, who hosts it."""

from __future__ import annotations

import re

from schemas.site_legal_notice import SiteLegalBlock, SiteLegalLine, SiteLegalSection
from services.country_profiles import CountryProfile, CountryProfiles
from services.site_legal.hosting import SITE_HOSTING_PROVIDER
from services.site_legal.lines import SiteLegalLines
from services.site_legal.sources import DEMO_PUBLISHER_COUNTRY_CODE, SiteLegalSources

_FRANCE_CODE = "FR"
_FRENCH_ESTABLISHMENT_ID_DIGITS = 14
_NON_DIGIT = re.compile(r"\D")


class LegalNoticeBuilder:
    """Builds the « Mentions légales » section of a site (« Impressum », « Renseignements sur l'entreprise »).

    A delivered site is published by the business: its identity comes first, then the publication
    director and the host where the country's law asks for them. A demo is published by the
    DevLeadHunter user who prepared it, established in France: the notice names that publisher, its
    director and the host under French law, then the business the demo presents.
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
                cls._demo_publisher_block(sources, lines),
                *cls._demo_director_blocks(sources, lines, publisher_rules.is_publication_director_required),
                cls._business_block(lines.localize("Entreprise présentée"), sources, lines),
            ]
            is_host_disclosure_required = publisher_rules.is_host_disclosure_required
        else:
            blocks = [
                cls._business_block(facts.publisher_heading, sources, lines),
                *cls._director_blocks(sources, lines),
            ]
            is_host_disclosure_required = facts.is_host_disclosure_required
        if is_host_disclosure_required:
            blocks.append(cls._host_block(lines))
        return SiteLegalSection(
            anchor=SiteLegalLines.anchor(facts.legal_notice_title),
            title=facts.legal_notice_title,
            blocks=[block for block in blocks if block.lines],
        )

    @classmethod
    def _business_block(cls, heading: str, sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalBlock:
        """The business's identity: name, address, contacts, registry identifier, VAT number and licence."""
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
                *lines.value(cls._legal_id_label(country, business.legal_id), business.legal_id),
                *lines.value(country.site_legal.vat_number_label, business.vat_number),
                *lines.value(license_label, business.professional_license_number),
            ],
        )

    @staticmethod
    def _director_blocks(sources: SiteLegalSources, lines: SiteLegalLines) -> list[SiteLegalBlock]:
        """The publication director of a delivered site, where the country's law asks for one."""
        if not sources.country.site_legal.is_publication_director_required:
            return []
        director = lines.plain(sources.business.publication_director)
        return [SiteLegalBlock(heading=lines.localize("Directeur de la publication"), kind="identity", lines=director)]

    @staticmethod
    def _demo_publisher_block(sources: SiteLegalSources, lines: SiteLegalLines) -> SiteLegalBlock:
        """The DevLeadHunter user who publishes the demo, as their profile states them."""
        publisher = sources.publisher
        heading = lines.localize("Éditeur de la démonstration")
        if publisher is None:
            return SiteLegalBlock(heading=heading, kind="identity", lines=[])
        return SiteLegalBlock(
            heading=heading,
            kind="identity",
            lines=[
                *lines.plain(publisher.company_name),
                *lines.plain(publisher.person_name),
                *lines.plain(publisher.postal_address),
                *lines.phone(publisher.phone, DEMO_PUBLISHER_COUNTRY_CODE),
                *lines.email(publisher.email),
                *lines.website(publisher.website_url),
            ],
        )

    @staticmethod
    def _demo_director_blocks(
        sources: SiteLegalSources, lines: SiteLegalLines, is_publication_director_required: bool
    ) -> list[SiteLegalBlock]:
        """The demo's publication director: its publisher, who answers for what the demo says."""
        if not is_publication_director_required or sources.publisher is None:
            return []
        director = lines.plain(sources.publisher.name)
        return [SiteLegalBlock(heading=lines.localize("Directeur de la publication"), kind="identity", lines=director)]

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
