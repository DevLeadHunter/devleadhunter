"""
Candidate facts — what a search knows about one business while it works on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from enums.prospect_search import EmailProofLevel
from enums.website_status import WebsiteStatus
from services.country_profiles import CountryProfiles
from services.french_overseas import FrenchOverseas, OverseasDepartment
from services.sms.phone_normalizer import PhoneNumberPlans, is_number_of_country, to_e164

_SNIPPET_MAX_CHARS: int = 240
_MAINLAND_LANDLINE_LEADS: tuple[str, ...] = ("+331", "+332", "+333", "+334", "+335")


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
