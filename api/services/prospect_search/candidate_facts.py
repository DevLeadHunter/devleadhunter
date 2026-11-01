"""
Candidate facts — what a search knows about one business while it works on it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from enums.prospect_search import CandidateOrigin, EmailProofLevel
from enums.website_status import WebsiteStatus
from services.country_profiles import CountryProfiles
from services.decision_maker.normalize import fold
from services.french_overseas import FrenchOverseas, OverseasDepartment
from services.sms.phone_normalizer import PhoneNumberPlans, is_number_of_country, to_e164

_SNIPPET_MAX_CHARS: int = 240
_WORD_SEPARATORS_RE: re.Pattern[str] = re.compile(r"[^a-z0-9]+")
_MAINLAND_LANDLINE_LEADS: tuple[str, ...] = ("+331", "+332", "+333", "+334", "+335")
# The chain evidence of a brand's agent or dealer reads « marque Peugeot ».
BRAND_OUTLET_EVIDENCE_PREFIX: str = "marque "
# Where the Google listing's own website is read: its « Site Web » button, its panel.
_LISTING_WEBSITE_SOURCES: tuple[str, ...] = ("Bouton « Site Web » de la fiche Google", "Fiche Google")
# How the evidence names a domain the business writes from: a website read there is guessed, Google never gave it.
EMAIL_DOMAIN_SUBJECT: str = "Le domaine de son email"
PRIVACY_PROXIED_DOMAIN_SUBJECT: str = "Le domaine masqué par un service d'anonymat"
_EMAIL_DOMAIN_SUBJECTS: tuple[str, ...] = (EMAIL_DOMAIN_SUBJECT, PRIVACY_PROXIED_DOMAIN_SUBJECT)


@dataclass
class CandidateFacts:
    """Everything read so far about a candidate, each fact with the page that proves it."""

    name: str
    trade_key: str
    country: str
    origin: str
    region: str | None = None
    city: str | None = None
    searched_city: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    email_proof_level: str | None = None
    website: str | None = None
    website_status: str | None = None
    google_cid: str | None = None
    google_maps_url: str | None = None
    facebook_url: str | None = None
    google_rating: float | None = None
    google_reviews_count: int | None = None
    google_category: str | None = None
    owner_name: str | None = None
    registry_number: str | None = None
    has_website_button: bool | None = None
    is_closed: bool = False
    is_chain: bool = False
    is_other_business: bool = False
    refuses_advertising: bool = False
    matches_trade: bool = True
    is_facebook_page_read: bool = False
    is_verified: bool = False
    evidence: list[dict[str, str]] = field(default_factory=list)

    @property
    def town(self) -> str:
        """Town of the business, or the searched town when the listing gave none."""
        return self.city or self.searched_city or ""

    def is_town_named_in(self, text: str) -> bool:
        """
        Whether a text names the business's town, however its words are joined (« Saint Paul les Dax » for
        « Saint-Paul-lès-Dax »).

        Args:
            text: A page, a result's text, an address.

        Returns:
            True when the town's words follow one another in the text.
        """
        town_words = _WORD_SEPARATORS_RE.sub(" ", fold(self.town)).strip()
        return bool(town_words) and f" {town_words} " in f" {_WORD_SEPARATORS_RE.sub(' ', fold(text))} "

    @property
    def is_swiss_directory_unanswered(self) -> bool:
        """Whether search.ch did not answer for the candidate, so its asterisk could not be read."""
        return any(line.get("fact") == "directory_unanswered" for line in self.evidence)

    @property
    def is_abroad(self) -> bool:
        """
        Whether the business is in another country than the search's.

        Its address ends with another country or, when it gives no address, its phone carries
        another country's dial code (a French firm surfacing in a Swiss border town). A French
        overseas number (``+596 …``) is French.
        """
        if CountryProfiles.foreign_country_of_address(self.address, country=self.country) is not None:
            return True
        international = to_e164(self.phone, country=self.country)
        home = CountryProfiles.declared(self.country)
        return (
            not self.address
            and international is not None
            and home is not None
            and not is_number_of_country(international, country=home.code)
        )

    @property
    def searched_department(self) -> OverseasDepartment | None:
        """The overseas department the search walks, ``None`` for a search of a whole country."""
        return FrenchOverseas.by_code(self.region)

    @property
    def is_outside_region(self) -> bool:
        """
        Whether a candidate of an overseas department's search is placed elsewhere.

        Its address places it (a mainland postal code, another department's code or name) or, when the
        address tells nothing, its number does (another department's, a mainland landline). A mobile
        alone places nobody: a business in Martinique may keep a mainland 06.
        """
        department = self.searched_department
        if department is None:
            return False
        address_department = FrenchOverseas.of_address(self.address)
        if address_department is not None or FrenchOverseas.postal_code_in(self.address) is not None:
            return address_department != department
        international = to_e164(self.phone, country=self.country) or ""
        number_department = FrenchOverseas.of_e164(international)
        if number_department is not None:
            return number_department != department
        return international.startswith(_MAINLAND_LANDLINE_LEADS)

    @property
    def has_email_on_another_site(self) -> bool:
        """Whether the email's domain runs a live site that does not name the business (a group's, another business's)."""
        domain = (self.email or "").rsplit("@", 1)[-1]
        return bool(domain) and any(
            line.get("fact") == "email_domain_site" and line.get("value") == domain for line in self.evidence
        )

    @property
    def outlet_brand(self) -> str | None:
        """The brand the business is the agent or the dealer of, when its listing says so."""
        for line in self.evidence:
            value = line.get("value", "")
            if line.get("fact") == "chain" and value.startswith(BRAND_OUTLET_EVIDENCE_PREFIX):
                return value.removeprefix(BRAND_OUTLET_EVIDENCE_PREFIX)
        return None

    @property
    def is_facebook_page_the_listed_website(self) -> bool:
        """Whether the business's Facebook page is the website its Google listing gives, not a page a search found."""
        return any(
            line.get("fact") == "facebook" and line.get("source") in _LISTING_WEBSITE_SOURCES for line in self.evidence
        )

    @property
    def is_website_guessed_from_email_domain(self) -> bool:
        """
        Whether the known website is only the front page of the domain the business writes from.

        Google never tied that page to the business: a parked « exemple.fr » does not stand for the website its
        listing declares, which may be another address (« exemple-automobiles.fr »).
        """
        sources = [
            line.get("source", "")
            for line in self.evidence
            if line.get("fact") == "website" and line.get("value") == self.website
        ]
        return bool(sources) and all(source.startswith(_EMAIL_DOMAIN_SUBJECTS) for source in sources)

    @property
    def contact_elsewhere(self) -> dict[str, str] | None:
        """The other place than the business's that its email or its Facebook page names (« 89 », « occitanie »)."""
        return next((line for line in self.evidence if line.get("fact") == "contact_elsewhere"), None)

    @property
    def is_email_unplaced(self) -> bool:
        """Whether the email was read on a third party's page that does not say where the business is."""
        return self._has_email_doubt("email_unplaced")

    @property
    def is_email_beside_another_phone(self) -> bool:
        """Whether the email was read beside another number than the business's (a namesake, or its manager's)."""
        return self._has_email_doubt("email_beside_another_phone")

    def _has_email_doubt(self, doubt: str) -> bool:
        """Whether the evidence notes that doubt about the current email."""
        return self.email is not None and any(
            line.get("fact") == doubt and line.get("value") == self.email for line in self.evidence
        )

    @property
    def is_placed_by_the_search_only(self) -> bool:
        """Whether a Google listing gave neither address nor town: its town is only the one searched."""
        return self.origin == CandidateOrigin.GOOGLE_LOCAL.value and not self.address and self.city is None

    @property
    def is_addressed_at_town_hall(self) -> bool:
        """Whether the listing gives a town hall's address while no company of the business's name is registered nearby."""
        return any(line.get("fact") == "town_hall_address" for line in self.evidence)

    @property
    def activity_of_another_trade(self) -> dict[str, str] | None:
        """The activity of another trade the registry files the company of the business's exact name under (« 52.2A »)."""
        return next((line for line in self.evidence if line.get("fact") == "registered_activity"), None)

    @property
    def register_successor(self) -> dict[str, str] | None:
        """The active firm the register seats at the business's place while the firm holding its name closes."""
        return next((line for line in self.evidence if line.get("fact") == "register_successor"), None)

    @property
    def registered_association(self) -> str | None:
        """The association the registry files the business as, when it is one (« Ass sportive Exemple »)."""
        return next((line["value"] for line in self.evidence if line.get("fact") == "association"), None)

    @property
    def privacy_proxied_domains(self) -> list[str]:
        """The domains a privacy service's address revealed for the business (« exemple.fr@domainsbyproxy.com »)."""
        return [line["value"] for line in self.evidence if line.get("fact") == "privacy_proxied_domain"]

    @property
    def is_ruled_out_before_search(self) -> bool:
        """Whether the candidate is out before any paid search: a chain, a refusal of advertising, a live website."""
        return self.is_chain or self.refuses_advertising or self.website_status == WebsiteStatus.LIVE.value

    @property
    def has_mobile_phone(self) -> bool:
        """Whether the phone number is a mobile of the candidate's country, a Martinique « 0696 … » included."""
        return PhoneNumberPlans.is_mobile_line(self.phone, country=self.country)

    def add_evidence(
        self, fact: str, value: str, *, source: str, url: str | None = None, snippet: str | None = None
    ) -> None:
        """
        Record the page a fact was read on.

        Args:
            fact: What the line proves (``website``, ``email``, ``closed``, ``facebook``, ``owner``…).
            value: The value read.
            source: Where it was read, in plain words (« Fiche Google », « Page Facebook »…).
            url: Address of the page.
            snippet: The words it was read in.
        """
        line: dict[str, str] = {"fact": fact, "value": value, "source": source}
        if url:
            line["url"] = url
        if snippet:
            line["snippet"] = snippet[:_SNIPPET_MAX_CHARS]
        self.evidence.append(line)

    def offer_email(
        self, email: str, proof: EmailProofLevel, *, source: str, url: str | None = None, snippet: str | None = None
    ) -> bool:
        """
        Keep an email when it is better proven than the one already held.

        Args:
            email: The address found.
            proof: How well it is proven to belong to the business.
            source: Where it was read.
            url: Address of the page.
            snippet: The words it was read in.

        Returns:
            Whether the email became the candidate's email.
        """
        if self.email_proof_level is not None and proof.value >= self.email_proof_level:
            return False
        self.email = email.strip().lower()
        self.email_proof_level = proof.value
        self.add_evidence("email", self.email, source=source, url=url, snippet=snippet)
        return True
