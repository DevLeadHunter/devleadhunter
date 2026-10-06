"""
Candidate facts — what a search knows about one business while it works on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from enums.prospect_search import EmailProofLevel
from services.country_profiles import CountryProfiles
from services.sms.phone_normalizer import PhoneNumberPlans

_SNIPPET_MAX_CHARS: int = 240


@dataclass
class CandidateFacts:
    """Everything read so far about a candidate, each fact with the page that proves it."""

    name: str
    trade_key: str
    country: str
    origin: str
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
        """Whether the address ends with another country than the search's."""
        return CountryProfiles.foreign_country_of_address(self.address, country=self.country) is not None

    @property
    def has_mobile_phone(self) -> bool:
        """Whether the phone number can receive an SMS in the candidate's country."""
        return PhoneNumberPlans.mobile_of_country(self.phone, country=self.country) is not None

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
