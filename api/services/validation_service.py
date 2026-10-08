"""
Validation service for prospect data.
"""

import re
import unicodedata
from typing import ClassVar


class ValidationService:
    """
    Service for validating prospect data.

    This service provides utility methods for validating
    and checking prospect information such as websites,
    contact details, etc.
    """

    # Lowercase markers of a platform's OWN meta description scraped by mistake
    # (e.g. the Google Maps page meta instead of the business description).
    GENERIC_PLATFORM_DESCRIPTION_MARKERS: ClassVar[tuple[str, ...]] = (
        "google maps",
        "find local businesses",
        "view maps and get driving directions",
        "trouvez des commerces locaux",
        "consultez des plans et calculez des itinéraires",
    )

    # Tokens too common to prove a description talks about THIS business.
    _WEAK_MENTION_TOKENS: ClassVar[frozenset[str]] = frozenset(
        {"les", "des", "sur", "sous", "chez", "sarl", "sas", "eurl", "ets", "saint", "sainte"}
    )

    # Social pages a business may list as its "website" — never a real website.
    _SOCIAL_DOMAINS: ClassVar[frozenset[str]] = frozenset(
        {
            "facebook.com",
            "fb.com",
            "instagram.com",
            "twitter.com",
            "x.com",
            "linkedin.com",
            "youtube.com",
            "pinterest.com",
            "tiktok.com",
            "snapchat.com",
        }
    )

    # Booking / marketplace / directory platforms a business may list as its "website" — a third-party
    # listing or reservation page, never the business's OWN site. Demoting them keeps the « no website »
    # targeting valid (many barbers/salons only have a Planity page, not a real site).
    _PLATFORM_DOMAINS: ClassVar[frozenset[str]] = frozenset(
        {
            "planity.com",
            "treatwell.fr",
            "treatwell.com",
            "fresha.com",
            "kiute.fr",
            "resalib.fr",
            "balinea.com",
            "wavy.pro",
            "pagesjaunes.fr",
            "thefork.fr",
            "thefork.com",
            "lafourchette.com",
            "deliveroo.fr",
            "deliveroo.com",
            "ubereats.com",
            "just-eat.fr",
            "local.ch",
            "search.ch",
            "localsearch.ch",
            "treatwell.ch",
            "thefork.ch",
            "just-eat.ch",
            "eat.ch",
            "smood.ch",
            "goldenpages.be",
            "pagesdor.be",
            "goudengids.be",
            "treatwell.be",
            "thefork.be",
            "deliveroo.be",
            "takeaway.com",
            "editus.lu",
            "yellow.lu",
            "pagesjaunes.ca",
            "yellowpages.ca",
            "411.ca",
            "canada411.ca",
            "opentable.ca",
            "opentable.com",
            "doordash.com",
            "skipthedishes.com",
        }
    )

    # Media assets a business may list as its "website" by mistake — a poster/logo pulled from a
    # Facebook post, a cloudinary image, an fbcdn photo… — never a real website.
    _ASSET_EXTENSIONS: ClassVar[tuple[str, ...]] = (
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".avif",
        ".bmp",
        ".ico",
        ".mp4",
        ".pdf",
    )
    _ASSET_HOSTS: ClassVar[tuple[str, ...]] = (
        "cloudinary.com",
        "fbcdn.net",
        "cdninstagram.com",
        "googleusercontent.com",
        "lookaside.",
        "imgur.com",
    )

    @classmethod
    def is_asset_url(cls, url: str | None) -> bool:
        """Whether a URL points at a media asset (image / video / pdf), not a website."""
        if not url:
            return False
        low = url.lower()
        path = low.split("?", 1)[0].split("#", 1)[0]
        return path.endswith(cls._ASSET_EXTENSIONS) or any(host in low for host in cls._ASSET_HOSTS)

    @classmethod
    def is_social_url(cls, url: str | None) -> bool:
        """Whether a URL points to a social-media page (Facebook, Instagram…), never a real website."""
        if not url:
            return False
        cleaned = url.lower().replace("http://", "").replace("https://", "").replace("www.", "").strip()
        host = cleaned.split("/")[0]
        # Match the host exactly or as a subdomain, so "x.com" never matches "max.com".
        return any(host == domain or host.endswith("." + domain) for domain in cls._SOCIAL_DOMAINS)

    @classmethod
    def is_platform_url(cls, url: str | None) -> bool:
        """Whether a URL points to a booking/marketplace/directory platform, not the business's own site."""
        if not url:
            return False
        cleaned = url.lower().replace("http://", "").replace("https://", "").replace("www.", "").strip()
        host = cleaned.split("/")[0]
        return any(host == domain or host.endswith("." + domain) for domain in cls._PLATFORM_DOMAINS)

    @classmethod
    def is_valid_website(cls, url: str | None) -> bool:
        """
        Check if a website URL is valid (not a social media platform).

        This method filters out social media URLs and determines
        if a URL points to a real business website.

        Args:
            url: Website URL to validate

        Returns:
            True if URL points to a valid business website, False otherwise

        Examples:
            >>> ValidationService.is_valid_website("https://www.example.com")
            True

            >>> ValidationService.is_valid_website("https://www.facebook.com/mybusiness")
            False

            >>> ValidationService.is_valid_website("http://example.fr")
            True
        """
        if not url:
            return False

        if cls.is_social_url(url):
            return False

        # A third-party booking/directory page (Planity, Treatwell, PagesJaunes…) is not the business's
        # own website — demoting it keeps the « no website » angle valid.
        if cls.is_platform_url(url):
            return False

        # A media asset (image/video/pdf) scraped from a post is not a website.
        if cls.is_asset_url(url):
            return False

        url_clean = url.replace("http://", "").replace("https://", "").replace("www.", "").strip()
        if "." in url_clean:
            domain = url_clean.split("/")[0]
            domain_parts = domain.split(".")
            if len(domain_parts) >= 2 and len(domain_parts[0]) > 0:
                return True

        return False

    @staticmethod
    def _significant_tokens(text: str) -> set[str]:
        """
        Split a text into lowercase, accent-free tokens usable for matching.

        Args:
            text: Any human text (business name, city, description).

        Returns:
            Tokens of 3+ characters, minus the too-common ones.
        """
        decomposed = unicodedata.normalize("NFD", text.lower())
        without_accents = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
        tokens = set(re.findall(r"[a-z0-9]{3,}", without_accents))
        return tokens - ValidationService._WEAK_MENTION_TOKENS

    @classmethod
    def is_generic_platform_description(cls, description: str | None) -> bool:
        """
        Check whether a description is a platform's own boilerplate, not the business's.

        Real-world case: the Google Maps search page meta ("Find local businesses,
        view maps and get driving directions in Google Maps.") scraped as the
        prospect's description and displayed verbatim on his demo site.

        Args:
            description: Scraped description text.

        Returns:
            True when the text is platform boilerplate and must be dropped.
        """
        if not description:
            return False
        lowered = description.lower()
        return any(marker in lowered for marker in cls.GENERIC_PLATFORM_DESCRIPTION_MARKERS)

    @classmethod
    def is_fragmentary_description(cls, description: str | None) -> bool:
        """
        Whether a description is scraped attribute fragments glued together, not real prose.

        Real-world case: "Food Truck à Poitiers Spécialité: poulet frit coréen" — a name, a city and
        a "Spécialité:" label stitched into one line, which reads badly on a client site. Detected by
        an inline attribute label ("Spécialité:", "Catégorie:"…) inside a SHORT text; long prose that
        merely contains such a word is left alone.

        Args:
            description: Scraped description text.

        Returns:
            True when the text looks fragmentary and should be dropped for a clean fallback.
        """
        if not description:
            return False
        text = description.strip()
        # A CAPITALISED attribute label + colon ("Spécialité:", "Catégorie:") is how scraped
        # attributes glue in; prose keeps such words lowercase ("notre spécialité, ..."). Restricting
        # to short texts avoids flagging long prose that happens to use a heading.
        label = r"\b(Sp[ée]cialit[ée]s?|Cat[ée]gorie|Type|Cuisine|Adresse|Horaires?|T[ée]l[ée]phone)\s*:"
        return len(text) < 100 and bool(re.search(label, text))

    @classmethod
    def description_mentions_business(
        cls,
        description: str,
        business_name: str | None,
        city: str | None,
    ) -> bool:
        """
        Check whether a description talks about the given business at all.

        Used on untrusted description sources (a page meta description): a text
        that names neither the business nor its city is about something else.
        With no name and no city to compare against, the check passes.

        Args:
            description: Scraped description text.
            business_name: Prospect business name.
            city: Prospect city.

        Returns:
            True when the description shares a significant token with the
            business name or the city.
        """
        expected_tokens = cls._significant_tokens(f"{business_name or ''} {city or ''}")
        if not expected_tokens:
            return True
        return bool(cls._significant_tokens(description) & expected_tokens)

    @classmethod
    def place_identity_mismatch(
        cls,
        prospect_name: str,
        prospect_city: str | None,
        prospect_postal_code: str | None,
        place_title: str | None,
        place_city: str | None,
        place_postal_code: str | None,
    ) -> str | None:
        """Check that a scraped Maps place is really the prospect's business.

        Without a stored Maps URL the scraper searches « nom + ville » and opens
        the FIRST result — a homonym elsewhere in France silently fills the demo
        site with someone else's photos/reviews. Name similarity catches a wrong
        business; the geo comparison catches the same-name-other-town homonym.
        Missing data on either side skips that check (old sidecars send none).

        Args:
            prospect_name: Business name stored on the prospect.
            prospect_city: Prospect city, when known.
            prospect_postal_code: Prospect postal code parsed from its address.
            place_title: Title (h1) of the scraped Maps place.
            place_city: City of the scraped place (JSON-LD address).
            place_postal_code: Postal code of the scraped place (JSON-LD address).

        Returns:
            A human-readable French mismatch reason, or None when coherent.
        """
        from services.decision_maker.normalize import company_similarity, town_key

        if place_title:
            similarity = company_similarity(prospect_name, place_title)
            if similarity < 0.2:
                return f"La fiche Google Maps trouvée (« {place_title} ») ne correspond pas au nom du prospect"

        if prospect_postal_code and place_postal_code and len(place_postal_code) == 5:
            if place_postal_code[:2] != prospect_postal_code[:2]:
                return (
                    f"La fiche Google Maps trouvée est dans un autre département "
                    f"({place_postal_code} au lieu de {prospect_postal_code}) — homonyme probable"
                )
        elif prospect_city and place_city and town_key(place_city) != town_key(prospect_city):
            return f"La fiche Google Maps trouvée est à {place_city}, pas à {prospect_city} — homonyme probable"

        return None

    @staticmethod
    def is_valid_email(email: str | None) -> bool:
        """
        Check if an email address is valid.

        Args:
            email: Email address to validate

        Returns:
            True if email is valid, False otherwise
        """
        if not email:
            return False

        # Basic email pattern validation
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def ascii_email(email: str) -> str:
        """
        The address with its domain written the way mail servers read it.

        An accented domain (« info@rochat-contrôles.ch ») becomes its ASCII form
        (« info@xn--rochat-contrles-nsb.ch »); any other address comes back as it is.

        Args:
            email: An email address.

        Returns:
            The address with an ASCII domain.
        """
        local_part, separator, domain = email.rpartition("@")
        if not separator or domain.isascii():
            return email
        try:
            return f"{local_part}@{domain.encode('idna').decode('ascii')}"
        except UnicodeError:
            return email

    @staticmethod
    def normalize_phone(phone: str | None) -> str | None:
        """
        Normalize phone number format.

        Removes spaces, dashes, and other formatting characters
        to standardize phone number format.

        Args:
            phone: Phone number to normalize

        Returns:
            Normalized phone number or None if invalid
        """
        if not phone:
            return None

        # Remove common formatting characters
        normalized = phone.replace(" ", "").replace("-", "").replace(".", "").replace("(", "").replace(")", "")

        # Remove leading + if present
        if normalized.startswith("+"):
            normalized = normalized[1:]

        # Check if it's a valid phone number (at least 9 digits)
        if normalized and normalized.isdigit() and len(normalized) >= 9:
            return normalized

        return phone  # Return original if normalization failed

    @staticmethod
    def calculate_confidence_score(
        phone: str | None = None, address: str | None = None, email: str | None = None, website: str | None = None
    ) -> int:
        """
        Calculate confidence score based on data completeness.

        Score rules:
        - Base score: 1 (for name, category, source)
        - +1 if phone is present
        - +1 if address is present with street number
        - -1 if website is present and valid
        - +1 if email is present and valid
        - Maximum score: 4

        Args:
            phone: Phone number
            address: Full address
            email: Email address
            website: Website URL

        Returns:
            Confidence score from 1 to 4
        """
        score = 1  # Base score

        if phone and phone.strip():
            score += 1

        if address and address.strip() and any(c.isdigit() for c in address):
            score += 1

        if website and ValidationService.is_valid_website(website):
            score -= 1

        if email and ValidationService.is_valid_email(email):
            score += 1

        return min(max(score, 1), 4)


# Global service instance
validation_service = ValidationService()
