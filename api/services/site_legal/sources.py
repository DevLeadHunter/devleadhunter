"""The facts a site's legal block is computed from, read from the database when the site is served.

A demo is published by the DevLeadHunter user who prepared it, not by the business it presents. The
users are established in France (``DEMO_PUBLISHER_COUNTRY_CODE``): a demo's own notice and privacy
section follow French law and the GDPR, whatever the country of the business.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from enums.contact_name_status import ContactNameStatus
from enums.demo_site_status import DemoSiteStatus
from enums.order_status import WON_STATUSES
from models.demo_site import DemoSite
from models.order import Order
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from models.user import User
from services.country_profiles import CountryProfile, CountryProfiles
from services.enrichment_service import enrichment_service
from services.sms.phone_normalizer import format_phone_for_display
from services.templates import registry as template_registry
from services.templates.visitor_data import TemplateVisitorData

DEMO_PUBLISHER_COUNTRY_CODE: str = "FR"

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_REGISTRY_BACKED_CONTACT_STATUSES: frozenset[str] = frozenset(
    {ContactNameStatus.AUTO.value, ContactNameStatus.CONFIRMED.value}
)
_TRUSTED_CONTACT_STATUSES: frozenset[str] = frozenset(
    {*_REGISTRY_BACKED_CONTACT_STATUSES, ContactNameStatus.MANUAL.value}
)


@dataclass(frozen=True)
class BusinessLegalIdentity:
    """The business a site presents, with only the facts known for sure.

    Attributes:
        name: The invoiced name of a sale, or the name the demo shows.
        trade_name: The name the site shows, when it differs from the invoiced name.
        address: The public address, or the reviewed billing address of a sale that has no public one.
        phone: The public phone number, in the country's display shape.
        email: The public email address.
        legal_id: The registry identifier given at the sale, or the SIREN of the trusted registry match.
        vat_number: The VAT number given at the sale.
        professional_license_label: The name of a professional licence (« Licence RBQ »).
        professional_license_number: Its number.
        publication_director: The person answerable for a delivered site's content.
    """

    name: str
    trade_name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    legal_id: str | None = None
    vat_number: str | None = None
    professional_license_label: str | None = None
    professional_license_number: str | None = None
    publication_director: str | None = None


@dataclass(frozen=True)
class DemoPublisherIdentity:
    """The DevLeadHunter user who publishes a demo, as their profile states them.

    Attributes:
        name: The user's name.
        company_name: Their trading name.
        postal_address: The postal address of their profile.
        email: Their public contact email (never the login address).
        phone: Their public contact phone.
        website_url: Their company website.
    """

    name: str
    company_name: str | None = None
    postal_address: str | None = None
    email: str | None = None
    phone: str | None = None
    website_url: str | None = None

    @property
    def label(self) -> str:
        """How a sentence names the publisher: their trading name, else their own name."""
        return self.company_name or self.name

    @property
    def person_name(self) -> str | None:
        """The publisher's own name when it differs from their trading name, shown under it."""
        return self.name if self.name != self.company_name else None


@dataclass(frozen=True)
class SiteLegalSources:
    """Everything the legal block of one site is computed from.

    Attributes:
        country: The profile of the business's country.
        is_demo: Whether the site is still a prospection demo, not yet delivered on the client's domain.
        business: The business the site presents.
        publisher: The demo's publisher, ``None`` once the site is delivered.
        visitor_data: What the template's layer does with a visitor's data.
        accent_color: The site's action colour, the accent of its legal page.
    """

    country: CountryProfile
    is_demo: bool
    business: BusinessLegalIdentity
    publisher: DemoPublisherIdentity | None
    visitor_data: TemplateVisitorData
    accent_color: str | None = None

    @property
    def publisher_label(self) -> str:
        """How a sentence names the demo's publisher, generic when their profile cannot be read."""
        return self.publisher.label if self.publisher else "l'éditeur de la démonstration"


class SiteLegalSourceLoader:
    """Reads the facts of a site's legal block from its records, the served content only refreshing contact lines."""

    @classmethod
    def load(cls, db: Session, site: DemoSite, content: dict[str, Any]) -> SiteLegalSources:
        """
        Gather the facts of one site's legal block.

        A contact line (address, phone, email) follows the served content, so a client's Storyblok edit shows,
        but an emptied field falls back on the records: a publication can update a mention, never erase it.

        Args:
            db: Active database session.
            site: The served site.
            content: The content served with it (flat ``SiteContent``).

        Returns:
            The facts, ready for the legal notice and the privacy policy.
        """
        prospect = cls._prospect(db, site)
        enrichment = cls._enrichment(db, site)
        is_demo = site.status != DemoSiteStatus.DELIVERED.value
        sale = None if is_demo else cls._sale(db, site)
        country = CountryProfiles.get(
            (prospect.country if prospect else None) or (sale.billing_country_code if sale else None)
        )
        business = cls._business(site, content, country, prospect, enrichment, sale)
        return SiteLegalSources(
            country=country,
            is_demo=is_demo,
            business=business,
            publisher=cls._publisher(site.user) if is_demo else None,
            visitor_data=template_registry.visitor_data(site.template_id),
            accent_color=cls._accent_color(site.template_id, content),
        )

    @staticmethod
    def _prospect(db: Session, site: DemoSite) -> ProspectDB | None:
        """The prospect the site was made for, when linked."""
        if not site.prospect_id:
            return None
        return enrichment_service.get_prospect_for_user(db, site.user_id, site.prospect_id)

    @staticmethod
    def _enrichment(db: Session, site: DemoSite) -> ProspectEnrichment | None:
        """The enrichment record of the site's prospect, when linked."""
        if not site.prospect_id:
            return None
        return enrichment_service.get_for_prospect(db, site.user_id, site.prospect_id)

    @staticmethod
    def _sale(db: Session, site: DemoSite) -> Order | None:
        """The latest won sale of a delivered site: the one tied to the site, else to its prospect."""
        won_orders = db.query(Order).filter(
            Order.user_id == site.user_id,
            Order.status.in_(WON_STATUSES),
            Order.deleted_at.is_(None),
        )
        by_site = won_orders.filter(Order.demo_site_id == site.id).order_by(Order.id.desc()).first()
        if by_site is not None or not site.prospect_id:
            return by_site
        return won_orders.filter(Order.prospect_id == site.prospect_id).order_by(Order.id.desc()).first()

    @classmethod
    def _business(
        cls,
        site: DemoSite,
        content: dict[str, Any],
        country: CountryProfile,
        prospect: ProspectDB | None,
        enrichment: ProspectEnrichment | None,
        sale: Order | None,
    ) -> BusinessLegalIdentity:
        """The business identity, from the sale first, then the records, the served content refreshing contacts."""
        shown_name = cls._text(content.get("businessName")) or site.business_name
        invoiced_name = cls._text(sale.business_name) if sale else None
        name = invoiced_name or shown_name
        raw_phone = cls._text(content.get("phone")) or site.phone or (prospect.phone if prospect else None)
        license_number = cls._text(enrichment.professional_license_number) if enrichment else None
        return BusinessLegalIdentity(
            name=name,
            trade_name=shown_name if cls._differs(shown_name, name) else None,
            address=cls._public_address(content, country, prospect, enrichment) or cls._billing_address(sale, country),
            phone=format_phone_for_display(raw_phone, country=country.code) or None,
            email=cls._text(content.get("email"))
            or cls._text(site.email)
            or cls._text(prospect.email if prospect else None),
            legal_id=cls._text(sale.billing_tax_id if sale else None) or cls._registry_siren(enrichment),
            vat_number=cls._text(sale.billing_vat_number) if sale else None,
            professional_license_label=(
                cls._text(enrichment.professional_license_label) if enrichment and license_number else None
            ),
            professional_license_number=license_number,
            publication_director=cls._publication_director(sale, enrichment),
        )

    @classmethod
    def _registry_siren(cls, enrichment: ProspectEnrichment | None) -> str | None:
        """The SIREN of the registry company the decision maker came from, only when that match is trusted.

        A proposal still « à confirmer », or a name typed by hand over an older match, may belong to
        another company: its SIREN is never published.
        """
        if enrichment is None or enrichment.contact_name_status not in _REGISTRY_BACKED_CONTACT_STATUSES:
            return None
        return cls._text(enrichment.contact_siren)

    @classmethod
    def _publication_director(cls, sale: Order | None, enrichment: ProspectEnrichment | None) -> str | None:
        """The person answerable for a delivered site: the sale's customer, else the trusted decision maker."""
        if sale is None:
            return None
        customer = cls._text(sale.customer_name)
        if customer:
            return customer
        if enrichment is None or enrichment.contact_name_status not in _TRUSTED_CONTACT_STATUSES:
            return None
        return cls._text(f"{enrichment.contact_first_name or ''} {enrichment.contact_last_name or ''}")

    @classmethod
    def _public_address(
        cls,
        content: dict[str, Any],
        country: CountryProfile,
        prospect: ProspectDB | None,
        enrichment: ProspectEnrichment | None,
    ) -> str | None:
        """The public street address, completed with its postal code and town when it only names the street."""
        street = cls._text(content.get("address")) or cls._text(prospect.address if prospect else None)
        if street is None:
            return None
        city = (
            cls._text(prospect.city if prospect else None)
            or cls._text(enrichment.place_city if enrichment else None)
            or cls._text(content.get("city"))
        )
        postal_code = cls._text(enrichment.place_postal_code) if enrichment else None
        return cls._with_locality(street, postal_code, city, country)

    @classmethod
    def _billing_address(cls, sale: Order | None, country: CountryProfile) -> str | None:
        """The billing address reviewed at the sale, on one line."""
        if sale is None:
            return None
        street = cls._text(sale.billing_address)
        city = cls._text(sale.billing_city)
        postal_code = cls._text(sale.billing_zip_code)
        if street is None:
            return cls._locality(postal_code, city, country)
        return cls._with_locality(street, postal_code, city, country)

    @classmethod
    def _with_locality(cls, street: str, postal_code: str | None, city: str | None, country: CountryProfile) -> str:
        """A street line followed by its locality in the country's order, unless the line already names the town."""
        if city is None or city.lower() in street.lower():
            return street
        if postal_code is not None and postal_code.lower() in street.lower():
            postal_code = None
        return f"{street}, {cls._locality(postal_code, city, country)}"

    @staticmethod
    def _locality(postal_code: str | None, city: str | None, country: CountryProfile) -> str | None:
        """The postal code and the town in the order the country writes them (« 34090 Montpellier », « Laval H7N 1A1 »)."""
        if city is None:
            return postal_code
        if postal_code is None:
            return city
        if country.city_precedes_postal_code:
            return f"{city} {postal_code}"
        return f"{postal_code} {city}"

    @classmethod
    def _publisher(cls, user: User | None) -> DemoPublisherIdentity | None:
        """The identity a demo's publisher gives in their profile."""
        if user is None:
            return None
        return DemoPublisherIdentity(
            name=user.name,
            company_name=cls._text(user.company_name),
            postal_address=cls._text(user.postal_address),
            email=cls._text(user.contact_email),
            phone=cls._text(user.contact_phone),
            website_url=cls._text(user.company_website_url),
        )

    @staticmethod
    def _accent_color(template_id: str, content: dict[str, Any]) -> str | None:
        """The served palette's action colour, when it is a plain hex colour."""
        palette = content.get("palette")
        if not isinstance(palette, dict):
            return None
        color = palette.get(template_registry.brand_color_key(template_id))
        return color if isinstance(color, str) and _HEX_COLOR_RE.match(color) else None

    @staticmethod
    def _differs(shown_name: str, legal_name: str) -> bool:
        """Whether two business names differ beyond case and spacing."""
        return " ".join(shown_name.lower().split()) != " ".join(legal_name.lower().split())

    @staticmethod
    def _text(value: object) -> str | None:
        """A trimmed string, ``None`` when empty or not a string."""
        if not isinstance(value, str):
            return None
        cleaned = " ".join(value.split())
        return cleaned or None
