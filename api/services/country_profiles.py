"""Country profiles — the facts the software needs about a prospect's country.

``prospects.country`` (ISO 3166-1 alpha-2) is the pivot of every behaviour that depends
on the country. This registry states, for each country, what the services must read
instead of assuming France: the French label, the currency and how a sale price is shown
in it, the timezone of the send window, the dial code, the postal code shape, whether
cold SMS is open and how a recipient opts out, whether an email needs a postal address in
its footer, which fiscal identifier an invoice client carries, the domain extensions to
suggest, the regional words a generated text swaps, and what the legal page of a generated
site says there.

A profile only STATES the facts. Each service applies them where it renders or decides:
the email and SMS variables, the send policy, the SMS service, the sale drawer, the
site content builder, the site legal block. A country can be declared here before it is
opened to prospection: ``enabled`` is what ``SUPPORTED_COUNTRIES`` and the front catalog expose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar

from enums.privacy_regime import PrivacyRegime
from enums.sms_opt_out_mode import SmsOptOutMode

DEFAULT_COUNTRY_CODE: str = "FR"

# A converted price rounds to the ten from 200 up (« ≈ 470 CHF »), to the unit below: 79 € reads « ≈ 74 CHF ».
_CONVERTED_PRICE_STEP: int = 10
_CONVERTED_PRICE_STEP_FROM: int = 200
_APPROXIMATION_SIGN_PREFIX: str = "≈ "
# A civic number alone in its segment, as Canada Post writes it before the street (« 123, rue X »).
_CIVIC_NUMBER_SEGMENT: re.Pattern[str] = re.compile(r"\d+[A-Za-z]?(?:-\d+[A-Za-z]?)?")


def _format_euro_amount(cents: int) -> str:
    """Render a cents amount the French way: ``500`` or ``499,90`` (no currency)."""
    if cents % 100 == 0:
        return str(cents // 100)
    return f"{cents / 100:.2f}".replace(".", ",")


@dataclass(frozen=True)
class SiteLegalFacts:
    """What the legal page of a generated site says in a country, and how its footer links to it.

    Attributes:
        locale: The language tag of the site (``fr-CH``), the ``lang`` of its legal page.
        page_title: The title of the legal page.
        legal_notice_title: The title of the section naming who publishes the site.
        legal_notice_link_label: Its footer link, ``None`` where no such notice is customary.
        privacy_notice_title: The title of the privacy section.
        privacy_link_label: Its footer link.
        publisher_heading: The heading of the business's identity on a delivered site.
        legal_id_label: How the business identifier reads on the page (« SIREN », « IDE », « NEQ »).
        vat_number_label: How the VAT number reads on the page.
        is_publication_director_required: Whether the law asks for a publication director (France).
        is_host_disclosure_required: Whether the law asks the legal notice to name the hosting provider.
        privacy_regime: The data protection law the privacy section follows.
        privacy_authority_name: The authority a visitor can turn to.
        privacy_authority_url: Its website.
    """

    locale: str
    page_title: str
    legal_notice_title: str
    legal_notice_link_label: str | None
    privacy_notice_title: str
    privacy_link_label: str
    publisher_heading: str
    legal_id_label: str
    vat_number_label: str
    is_publication_director_required: bool
    is_host_disclosure_required: bool
    privacy_regime: PrivacyRegime
    privacy_authority_name: str
    privacy_authority_url: str


@dataclass(frozen=True)
class CountryProfile:
    """Everything country-dependent about a prospect, in one place."""

    code: str
    label: str
    # The word appended to a search query (Maps, SERP, Facebook) to pin the country: the region
    # the prospects read in their own listings (« Québec », not « Canada (Québec) »); empty in France.
    search_label: str
    enabled: bool
    in_european_union: bool
    currency: str
    # 1 EUR expressed in ``currency`` (1.0 for the euro zone).
    eur_rate: float
    # ``{amount}`` is the formatted number; a foreign price shows its approximation sign.
    price_format: str
    timezone: str
    dial_code: str
    postal_code_pattern: str
    # A real-looking postal code, the placeholder of a form field (« 35000 », « H2X 1Y4 »).
    postal_code_example: str
    sms_prospecting_open: bool
    sms_opt_out: SmsOptOutMode
    email_footer_needs_postal_address: bool
    tax_id_label: str
    # A real-looking fiscal identifier, the placeholder of a form field (« 123 456 789 », « CHE-123.456.789 »).
    tax_id_example: str
    tax_id_required: bool
    domain_tlds: tuple[str, ...]
    site_legal: SiteLegalFacts
    # Regional words a generated text swaps (lower-case, whole words), empty when none.
    lexicon: dict[str, str] = field(default_factory=dict)
    # Names an address writes after its city that are never a city: the country (« Suisse », « Canada »)
    # and the province code (« QC »). Luxembourg has none: its capital bears the country's name.
    address_trailing_names: tuple[str, ...] = ()
    # Province names written after the city (« Montréal (Québec) », « Laval, Québec ») that are also a
    # city's name: a bare one is only dropped when another segment, the city, precedes it.
    address_region_names: tuple[str, ...] = ()
    # North America writes the city before the postal code (« Montréal (Québec) H2X 1Y4 »), Europe after it.
    city_precedes_postal_code: bool = False

    @property
    def is_euro(self) -> bool:
        """Whether prices are charged in euros without conversion."""
        return self.currency == "EUR"

    @property
    def postal_code_regex(self) -> re.Pattern[str]:
        """The postal code shape as a bounded, case-insensitive regex whose group 1 is the code.

        Shared by every address parser (scrapers, enrichment guard, sale finalization) so a
        Swiss « 1204 », a Belgian « 1000 » or a Québec « H2X 1Y4 » is read where France only
        knew five digits.
        """
        return re.compile(rf"\b({self.postal_code_pattern})\b", re.IGNORECASE)

    def strip_address_tail(self, text: str) -> str:
        """Cut an address after its city: drop the country and the province written there.

        « 12 Rue X, Laval, QC, Canada » ends on Laval, « 123, rue X, Montréal (Québec) » on Montréal and
        « Rue du Rhône 12, Genève, Suisse » on Genève, while « 123, rue X, Québec » keeps Québec City.

        Args:
            text: An address, or the part of one that precedes its postal code.

        Returns:
            The address ending on its city, trimmed; unchanged for a country without such names.
        """
        segments = [segment.strip() for segment in text.split(",") if segment.strip()]
        trailing_names = {name.lower() for name in self.address_trailing_names}
        region_names = {name.lower() for name in self.address_region_names}
        while segments:
            last = segments[-1].lower()
            street_and_city = [segment for segment in segments[:-1] if not _CIVIC_NUMBER_SEGMENT.fullmatch(segment)]
            is_country_or_code = last in trailing_names
            is_province_after_city = last in region_names and len(street_and_city) >= 2
            if not (is_country_or_code or is_province_after_city):
                break
            segments.pop()
        if segments and (trailing_names or region_names):
            segments[-1] = self._glued_tail_regex().sub("", segments[-1]).strip()
        return ", ".join(segment for segment in segments if segment)

    def _glued_tail_regex(self) -> re.Pattern[str]:
        """A country or province written in the city's own segment: « Montréal (Québec) », « MONTRÉAL QC »."""
        bracketed = "|".join(re.escape(name) for name in (*self.address_trailing_names, *self.address_region_names))
        spaced = "|".join(re.escape(name) for name in self.address_trailing_names) or r"(?!)"
        return re.compile(rf"\s*\((?:{bracketed})\)$|\s+(?:{spaced})$", re.IGNORECASE)

    def format_price(self, cents: int) -> str:
        """Render a euro sale price as the prospect reads it in his country.

        A euro country keeps the exact amount (« 500 € », « 499,90 € »); another currency gets
        the converted amount with an approximation sign, rounded to the nearest ten from 200 up
        (« ≈ 470 CHF ») and to the unit below (« ≈ 74 CHF »).

        Args:
            cents: The sale price in euro cents.

        Returns:
            The price string to put in an email, an SMS or a site.
        """
        if self.is_euro:
            return self.price_format.format(amount=_format_euro_amount(cents))
        converted = cents / 100 * self.eur_rate
        step = _CONVERTED_PRICE_STEP if converted >= _CONVERTED_PRICE_STEP_FROM else 1
        rounded = int(round(converted / step) * step)
        return self.price_format.format(amount=rounded)

    def format_price_without_approximation(self, cents: int) -> str:
        """Render a euro sale price as a plain amount, the converted one without its « ≈ » (« 470 CHF »).

        For a price shown alone, where « ≈ » would read as a price that can still move: the demo's
        banner card. An email keeps ``format_price``, next to the euro amount.

        Args:
            cents: The sale price in euro cents.

        Returns:
            The price string.
        """
        return self.format_price(cents).removeprefix(_APPROXIMATION_SIGN_PREFIX)


class CountryProfiles:
    """Registry of the declared countries, keyed by ISO code."""

    _PROFILES: ClassVar[dict[str, CountryProfile]] = {
        "FR": CountryProfile(
            code="FR",
            label="France",
            search_label="",
            enabled=True,
            in_european_union=True,
            currency="EUR",
            eur_rate=1.0,
            price_format="{amount} €",
            timezone="Europe/Paris",
            dial_code="+33",
            postal_code_pattern=r"\d{5}",
            postal_code_example="35000",
            sms_prospecting_open=True,
            sms_opt_out=SmsOptOutMode.SHORT_CODE,
            email_footer_needs_postal_address=False,
            tax_id_label="SIREN / SIRET",
            tax_id_example="123 456 789",
            tax_id_required=True,
            domain_tlds=(".fr",),
            site_legal=SiteLegalFacts(
                locale="fr-FR",
                page_title="Mentions légales et politique de confidentialité",
                legal_notice_title="Mentions légales",
                legal_notice_link_label="Mentions légales",
                privacy_notice_title="Politique de confidentialité",
                privacy_link_label="Confidentialité",
                publisher_heading="Éditeur du site",
                legal_id_label="SIREN",
                vat_number_label="TVA intracommunautaire",
                is_publication_director_required=True,
                is_host_disclosure_required=True,
                privacy_regime=PrivacyRegime.GDPR,
                privacy_authority_name="Commission nationale de l'informatique et des libertés (CNIL)",
                privacy_authority_url="https://www.cnil.fr",
            ),
            address_trailing_names=("France",),
        ),
        "CH": CountryProfile(
            code="CH",
            label="Suisse",
            search_label="Suisse",
            enabled=True,
            in_european_union=False,
            currency="CHF",
            eur_rate=0.94,
            price_format="≈ {amount} CHF",
            timezone="Europe/Zurich",
            dial_code="+41",
            postal_code_pattern=r"\d{4}",
            postal_code_example="1204",
            sms_prospecting_open=True,
            sms_opt_out=SmsOptOutMode.LINK,
            email_footer_needs_postal_address=False,
            tax_id_label="IDE (CHE)",
            tax_id_example="CHE-123.456.789",
            tax_id_required=False,
            domain_tlds=(".ch",),
            site_legal=SiteLegalFacts(
                locale="fr-CH",
                page_title="Mentions légales et protection des données",
                legal_notice_title="Mentions légales",
                legal_notice_link_label="Mentions légales",
                privacy_notice_title="Protection des données",
                privacy_link_label="Protection des données",
                publisher_heading="Éditeur du site",
                legal_id_label="IDE",
                vat_number_label="TVA",
                is_publication_director_required=False,
                is_host_disclosure_required=False,
                privacy_regime=PrivacyRegime.SWISS_FADP,
                privacy_authority_name="Préposé fédéral à la protection des données et à la transparence (PFPDT)",
                privacy_authority_url="https://www.edoeb.admin.ch",
            ),
            address_trailing_names=("Suisse", "Switzerland", "Schweiz", "Svizzera"),
        ),
        "BE": CountryProfile(
            code="BE",
            label="Belgique",
            search_label="Belgique",
            enabled=True,
            in_european_union=True,
            currency="EUR",
            eur_rate=1.0,
            price_format="{amount} €",
            timezone="Europe/Brussels",
            dial_code="+32",
            postal_code_pattern=r"\d{4}",
            postal_code_example="1000",
            # The operators replace a lettered sender by a short code: Léo keeps Belgium email-only.
            sms_prospecting_open=False,
            sms_opt_out=SmsOptOutMode.LINK,
            email_footer_needs_postal_address=False,
            tax_id_label="Numéro BCE",
            tax_id_example="0123.456.789",
            tax_id_required=False,
            domain_tlds=(".be",),
            site_legal=SiteLegalFacts(
                locale="fr-BE",
                page_title="Mentions légales et politique de confidentialité",
                legal_notice_title="Mentions légales",
                legal_notice_link_label="Mentions légales",
                privacy_notice_title="Politique de confidentialité",
                privacy_link_label="Confidentialité",
                publisher_heading="Éditeur du site",
                legal_id_label="Numéro d'entreprise",
                vat_number_label="TVA",
                is_publication_director_required=False,
                is_host_disclosure_required=False,
                privacy_regime=PrivacyRegime.GDPR,
                privacy_authority_name="Autorité de protection des données (APD)",
                privacy_authority_url="https://www.autoriteprotectiondonnees.be",
            ),
            address_trailing_names=("Belgique", "Belgium", "België", "Belgien"),
        ),
        "LU": CountryProfile(
            code="LU",
            label="Luxembourg",
            search_label="Luxembourg",
            enabled=True,
            in_european_union=True,
            currency="EUR",
            eur_rate=1.0,
            price_format="{amount} €",
            timezone="Europe/Luxembourg",
            dial_code="+352",
            postal_code_pattern=r"\d{4}",
            postal_code_example="1234",
            sms_prospecting_open=False,
            sms_opt_out=SmsOptOutMode.LINK,
            email_footer_needs_postal_address=False,
            tax_id_label="Numéro RCS",
            tax_id_example="B123456",
            tax_id_required=False,
            domain_tlds=(".lu",),
            site_legal=SiteLegalFacts(
                locale="fr-LU",
                page_title="Mentions légales et politique de confidentialité",
                legal_notice_title="Mentions légales",
                legal_notice_link_label="Mentions légales",
                privacy_notice_title="Politique de confidentialité",
                privacy_link_label="Confidentialité",
                publisher_heading="Éditeur du site",
                legal_id_label="RCS Luxembourg",
                vat_number_label="TVA",
                is_publication_director_required=False,
                is_host_disclosure_required=False,
                privacy_regime=PrivacyRegime.GDPR,
                privacy_authority_name="Commission nationale pour la protection des données (CNPD)",
                privacy_authority_url="https://cnpd.public.lu",
            ),
        ),
        # Québec by email only: French-speaking, North American phone plan, CASL footer.
        "CA": CountryProfile(
            code="CA",
            label="Canada (Québec)",
            search_label="Québec",
            enabled=True,
            in_european_union=False,
            currency="CAD",
            eur_rate=1.6,
            price_format="≈ {amount} $ CA",
            timezone="America/Toronto",
            dial_code="+1",
            postal_code_pattern=r"[A-Z]\d[A-Z] ?\d[A-Z]\d",
            postal_code_example="H2X 1Y4",
            # No lettered sender, 10DLC registration and CASL consent: no cold SMS in Canada.
            sms_prospecting_open=False,
            sms_opt_out=SmsOptOutMode.LINK,
            email_footer_needs_postal_address=True,
            tax_id_label="NEQ",
            tax_id_example="1234567890",
            tax_id_required=False,
            domain_tlds=(".ca",),
            site_legal=SiteLegalFacts(
                locale="fr-CA",
                page_title="Renseignements sur l'entreprise et politique de confidentialité",
                legal_notice_title="Renseignements sur l'entreprise",
                legal_notice_link_label=None,
                privacy_notice_title="Politique de confidentialité",
                privacy_link_label="Politique de confidentialité",
                publisher_heading="Entreprise",
                legal_id_label="NEQ",
                vat_number_label="Numéros de TPS et de TVQ",
                is_publication_director_required=False,
                is_host_disclosure_required=False,
                privacy_regime=PrivacyRegime.QUEBEC_PRIVATE_SECTOR,
                privacy_authority_name="Commission d'accès à l'information du Québec",
                privacy_authority_url="https://www.cai.gouv.qc.ca",
            ),
            lexicon={
                "devis": "soumission",
                "e-mail": "courriel",
                "email": "courriel",
                "mail": "courriel",
                "portable": "cellulaire",
                "week-end": "fin de semaine",
                "weekend": "fin de semaine",
                "à emporter": "pour emporter",
            },
            address_trailing_names=("Canada", "QC"),
            address_region_names=("Québec", "Quebec"),
            city_precedes_postal_code=True,
        ),
    }

    @classmethod
    def get(cls, code: str | None) -> CountryProfile:
        """Resolve the profile of a country code, France for an unknown or closed country.

        Args:
            code: Raw ISO code from a prospect or a job payload (any case, may be ``None``).

        Returns:
            The enabled profile of that code, or the French one.
        """
        cleaned = (code or "").strip().upper()
        profile = cls._PROFILES.get(cleaned)
        if profile is None or not profile.enabled:
            return cls._PROFILES[DEFAULT_COUNTRY_CODE]
        return profile

    @classmethod
    def declared(cls, code: str) -> CountryProfile | None:
        """The profile of a code whether it is open or not, ``None`` when never declared.

        Args:
            code: ISO code, any case.

        Returns:
            The declared profile, enabled or not.
        """
        return cls._PROFILES.get(code.strip().upper())

    @classmethod
    def enabled(cls) -> list[CountryProfile]:
        """The countries open to prospection, in declaration order."""
        return [profile for profile in cls._PROFILES.values() if profile.enabled]

    @classmethod
    def labels(cls) -> dict[str, str]:
        """ISO code to French label of every open country, the shape ``SUPPORTED_COUNTRIES`` exposes."""
        return {profile.code: profile.label for profile in cls.enabled()}
