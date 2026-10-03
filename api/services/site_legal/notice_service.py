"""Assembles the legal block served with a site: its footer links, its legal notice and its privacy policy."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from models.demo_site import DemoSite
from schemas.site_legal_notice import SiteLegalLink, SiteLegalNotice, SiteLegalSection
from services.site_legal.legal_notice import LegalNoticeBuilder
from services.site_legal.lines import SiteLegalLines
from services.site_legal.privacy_notice import PrivacyNoticeBuilder
from services.site_legal.sources import SiteLegalSourceLoader, SiteLegalSources

logger = logging.getLogger(__name__)


class SiteLegalNoticeService:
    """Computes the legal block of a site each time it is served, from its records and its country's profile."""

    def build_for_site(self, db: Session, site: DemoSite, content: dict[str, Any]) -> SiteLegalNotice | None:
        """
        Compute the legal block of a served site.

        Never raises: the site must render even when a fact cannot be read, its footer then simply
        shows no legal link.

        Args:
            db: Active database session.
            site: The served site, demo or delivered.
            content: The content served with it.

        Returns:
            The block, or ``None`` when it could not be computed.
        """
        try:
            return self.build(SiteLegalSourceLoader.load(db, site, content))
        except Exception:
            logger.exception("Legal block of site %s could not be computed", site.slug)
            return None

    @staticmethod
    def build(sources: SiteLegalSources) -> SiteLegalNotice:
        """
        Compute the legal block from facts already gathered.

        Args:
            sources: The facts of the site.

        Returns:
            The block: page title, demo notice, footer links and the two sections.
        """
        facts = sources.country.site_legal
        lines = SiteLegalLines(sources.country.code)
        legal_notice = LegalNoticeBuilder.build(sources, lines)
        privacy_notice = PrivacyNoticeBuilder.build(sources, lines)
        return SiteLegalNotice(
            locale=facts.locale,
            page_title=facts.page_title,
            accent_color=sources.accent_color,
            demo_notice=SiteLegalNoticeService._demo_notice(sources, lines),
            links=SiteLegalNoticeService._footer_links(
                legal_notice, facts.legal_notice_link_label, privacy_notice, facts.privacy_link_label
            ),
            sections=[legal_notice, privacy_notice],
        )

    @staticmethod
    def _footer_links(
        legal_notice: SiteLegalSection,
        legal_notice_label: str | None,
        privacy_notice: SiteLegalSection,
        privacy_label: str,
    ) -> list[SiteLegalLink]:
        """The footer links: the legal notice where the country customarily links it, then the privacy policy."""
        links: list[SiteLegalLink] = []
        if legal_notice_label:
            links.append(SiteLegalLink(label=legal_notice_label, anchor=legal_notice.anchor))
        links.append(SiteLegalLink(label=privacy_label, anchor=privacy_notice.anchor))
        return links

    @staticmethod
    def _demo_notice(sources: SiteLegalSources, lines: SiteLegalLines) -> str | None:
        """The sentence that opens a demo's legal page: who prepared it, for whom, and who publishes it meanwhile."""
        if not sources.is_demo:
            return None
        return lines.localize(
            "Ce site est une démonstration préparée par {publisher} pour {business}. Tant que {business} ne l'a pas "
            "mis en ligne à son nom, {publisher} en est l'éditeur et le responsable des données décrites ci-dessous.",
            publisher=sources.publisher_label,
            business=sources.business.name,
        )


site_legal_notice_service = SiteLegalNoticeService()
