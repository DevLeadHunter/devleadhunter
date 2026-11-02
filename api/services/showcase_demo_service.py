"""Permanent showroom demos, one per template, that dibodev.fr embeds in its live workshop.

The « Site internet pour <métier> » pages of dibodev.fr frame ``demo.dibodev.fr/<slug>?_edit=1`` and
drive it through ``dlh:preview`` messages (identity, palette, photos, services), so a visitor sees his
own business on the real template without anything being generated. Those demos belong to no prospect,
never expire, are never withdrawn nor campaigned, and carry ``DemoSite.is_showcase``.

Their slugs are a contract with dibodev.fr (``docs/SHOWCASE_DEMOS.md``): never rename one. The businesses
are fictitious — each name was checked against annuaire-entreprises.data.gouv.fr on 2026-11-02 — and the
phone numbers are the unassigned ``02 99 00 00 0X`` range.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.user import User
from services.activity_log_service import CATEGORY_DEMO_SITE, STATUS_SUCCESS, activity_log_service
from services.demo_site_service import demo_site_service
from services.templates.site_content import apply_section_overrides

logger = logging.getLogger(__name__)

# Far enough that no countdown ever reaches it; the expiry pass skips showcases anyway.
SHOWCASE_EXPIRES_AT: datetime = datetime(2099, 12, 31, 23, 59, 59)

SHOWCASE_VERIFICATION_MESSAGE: str = "Démo vitrine permanente (atelier dibodev.fr) : jamais retirée."


@dataclass(frozen=True)
class ShowcaseDemoSite:
    """One showroom demo: a fictitious business of Rennes Métropole on one template."""

    slug: str
    template_id: str
    business_name: str
    city: str
    phone: str
    # The dibodev.fr trade page this demo serves (plombier, électricien, garage…).
    trade: str
    # Curated « prestations » cards for a multi-trade template whose defaults name no trade.
    service_cards: tuple[dict[str, str], ...] = ()


_CARPENTER_SERVICE_CARDS: tuple[dict[str, str], ...] = (
    {
        "title": "Agencement sur mesure",
        "description": "Bibliothèques, dressings et meubles dessinés pour votre pièce, fabriqués à l'atelier.",
        "image": "",
    },
    {
        "title": "Cuisines en bois massif",
        "description": "Conception, fabrication et pose de cuisines en chêne, frêne ou noyer, finitions huilées.",
        "image": "",
    },
    {
        "title": "Portes et fenêtres bois",
        "description": "Menuiseries extérieures et intérieures, remplacement ou création, isolation comprise.",
        "image": "",
    },
    {
        "title": "Escaliers",
        "description": "Escaliers droits, quart tournant ou hélicoïdaux, en bois ou mixtes bois et métal.",
        "image": "",
    },
    {
        "title": "Parquets et terrasses",
        "description": "Pose de parquet massif ou contrecollé, terrasses en bois et rénovation des anciens planchers.",
        "image": "",
    },
    {
        "title": "Restauration de meubles",
        "description": "Remise en état de mobilier ancien : collage, placage, teinte et vernis à l'ancienne.",
        "image": "",
    },
)

SHOWCASE_DEMO_SITES: tuple[ShowcaseDemoSite, ...] = (
    ShowcaseDemoSite(
        slug="exemple-plombier-signature",
        template_id="plumber-signature",
        business_name="Plomberie Kerhuel",
        city="Rennes",
        phone="02 99 00 00 01",
        trade="plombier",
    ),
    ShowcaseDemoSite(
        slug="exemple-plombier-atelier",
        template_id="plumber-atelier",
        business_name="Atelier Plomberie Kervella",
        city="Cesson-Sévigné",
        phone="02 99 00 00 02",
        trade="plombier",
    ),
    ShowcaseDemoSite(
        slug="exemple-plombier-cuivre",
        template_id="plumber-cuivre",
        business_name="Ty Plomb",
        city="Bruz",
        phone="02 99 00 00 03",
        trade="plombier",
    ),
    ShowcaseDemoSite(
        slug="exemple-electricien-eclat",
        template_id="electrician-eclat",
        business_name="Élec Bréquigny",
        city="Rennes",
        phone="02 99 00 00 04",
        trade="électricien",
    ),
    ShowcaseDemoSite(
        slug="exemple-electricien-lumen",
        template_id="electrician-lumen",
        business_name="Courant d'Ille",
        city="Saint-Grégoire",
        phone="02 99 00 00 05",
        trade="électricien",
    ),
    ShowcaseDemoSite(
        slug="exemple-garage-pitlane",
        template_id="mechanic-pitlane",
        business_name="Atelier Mécanique Kerlann",
        city="Chantepie",
        phone="02 99 00 00 06",
        trade="garage",
    ),
    ShowcaseDemoSite(
        slug="exemple-paysagiste-verdure",
        template_id="landscaper-verdure",
        business_name="Les Jardins de Kerbel",
        city="Betton",
        phone="02 99 00 00 07",
        trade="paysagiste",
    ),
    ShowcaseDemoSite(
        slug="exemple-menuisier-edito",
        template_id="artisan-edito",
        business_name="Atelier Bois Guéhenno",
        city="Vern-sur-Seiche",
        phone="02 99 00 00 08",
        trade="menuisier",
        service_cards=_CARPENTER_SERVICE_CARDS,
    ),
    ShowcaseDemoSite(
        slug="exemple-restaurant",
        template_id="food",
        business_name="Le Bouillon de la Vilaine",
        city="Rennes",
        phone="02 99 00 00 09",
        trade="restaurant",
    ),
    ShowcaseDemoSite(
        slug="exemple-coiffeur",
        template_id="barber",
        business_name="Salon Mezen",
        city="Pacé",
        phone="02 99 00 00 10",
        trade="coiffeur",
    ),
    ShowcaseDemoSite(
        slug="exemple-dentiste",
        template_id="dental",
        business_name="Cabinet dentaire du Thabor",
        city="Rennes",
        phone="02 99 00 00 11",
        trade="dentiste",
    ),
)


class ShowcaseSlugTakenError(ValueError):
    """A showroom slug is held by a real prospect's demo: the showroom never takes it over."""


class ShowcaseDemoService:
    """Creates and refreshes the showroom demos, replayable at will (existing ones are kept)."""

    def ensure_all(self, db: Session, owner: User, *, rebuild_content: bool = False) -> list[tuple[DemoSite, bool]]:
        """
        Make every showroom demo of the catalogue exist, online and flagged.

        Args:
            db: Active database session.
            owner: The account the demos belong to (the public pages sign with its contacts).
            rebuild_content: Regenerate the content of the demos that already exist (drops dashboard colour
                edits); by default only a demo without content gets one.

        Returns:
            Each demo with whether this call created it.

        Raises:
            ShowcaseSlugTakenError: When a catalogue slug belongs to a real prospect's demo.
        """
        return [
            self.ensure_one(db, owner, showcase, rebuild_content=rebuild_content) for showcase in SHOWCASE_DEMO_SITES
        ]

    def ensure_one(
        self, db: Session, owner: User, showcase: ShowcaseDemoSite, *, rebuild_content: bool = False
    ) -> tuple[DemoSite, bool]:
        """
        Make one showroom demo exist, online and flagged; an existing one is brought back to the catalogue.

        Args:
            db: Active database session.
            owner: The account the demo belongs to.
            showcase: The catalogue entry.
            rebuild_content: Regenerate the content even when the demo already has one.

        Returns:
            The demo and whether this call created it.

        Raises:
            ShowcaseSlugTakenError: When the slug belongs to a real prospect's demo.
        """
        site: DemoSite | None = db.query(DemoSite).filter(DemoSite.slug == showcase.slug).first()
        if site is not None and not site.is_showcase and site.prospect_id is not None:
            raise ShowcaseSlugTakenError(
                f"Slug « {showcase.slug} » belongs to the demo of prospect {site.prospect_id}: pick another slug."
            )
        created: bool = site is None
        if site is None:
            site = DemoSite(user_id=owner.id, slug=showcase.slug, expires_at=SHOWCASE_EXPIRES_AT)
            db.add(site)

        site.user_id = owner.id
        site.prospect_id = None
        site.is_showcase = True
        site.template_id = showcase.template_id
        site.business_name = showcase.business_name
        site.city = showcase.city
        site.phone = showcase.phone
        site.email = None
        site.section_overrides = self._section_overrides(showcase)
        site.status = DemoSiteStatus.ACTIVE.value
        site.expires_at = SHOWCASE_EXPIRES_AT
        site.demo_link_sent_at = None
        site.deleted_at = None
        site.demo_url = demo_site_service.demo_url_for_slug(showcase.slug)
        site.vercel_deployment_url = site.demo_url
        site.demo_url_live = True
        site.verification_message = SHOWCASE_VERIFICATION_MESSAGE
        site.error_message = None
        if created or rebuild_content or not site.content_json:
            site.content_json = self._build_content(site)
        db.commit()
        db.refresh(site)

        if created:
            activity_log_service.record(
                category=CATEGORY_DEMO_SITE,
                action="showcase_demo_site_created",
                status=STATUS_SUCCESS,
                title=f"Démo vitrine créée · {site.business_name} ({site.template_id})",
                user_id=owner.id,
                entity_type="demo_site",
                entity_id=site.id,
            )
        logger.info("Showcase demo %s for slug=%s", "created" if created else "refreshed", site.slug)
        return site, created

    @staticmethod
    def _section_overrides(showcase: ShowcaseDemoSite) -> dict | None:
        """The curated cards of a multi-trade template, in the shape the dashboard saves them; None otherwise."""
        if not showcase.service_cards:
            return None
        return {"services": [dict(card) for card in showcase.service_cards], "services_source": "manual"}

    @staticmethod
    def _build_content(site: DemoSite) -> dict:
        """The site content as a prospect's would be generated: template defaults, no enrichment, curated cards."""
        content: dict = demo_site_service.build_preview_content(
            business_name=site.business_name,
            template_id=site.template_id,
            phone=site.phone,
            city=site.city,
        )
        return apply_section_overrides(content, site.section_overrides)


showcase_demo_service = ShowcaseDemoService()
