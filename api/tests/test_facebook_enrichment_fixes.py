"""Unit tests for the 2026-08 Facebook enrichment fixes (website / city-postal / social)."""

from types import SimpleNamespace

from scrappers.enrichment_scraper import EnrichmentData
from scrappers.facebook_enrichment_scraper import (
    _clean_social_url,
    _parse_city_postal,
    _parse_phone,
    _website_belongs_to_business,
)

# Real "À propos" text captured from a public FB page (Coordonnées block order).
_ABOUT_TEXT = """Food truck mexicain Tacos Maru
1,7 K followers • 2,1 K suivi(e)s
À propos
Coordonnées
., Châtellerault, France, 86100
Adresse
06 29 34 58 99
Mobile
foodtruckmexicaintacosmaru@gmail.com
E-mail
Recommandé par 96 % (22 avis)"""


class TestCleanSocialUrl:
    def test_unwraps_lphp_redirect(self) -> None:
        raw = "https://l.facebook.com/l.php?u=https%3A%2F%2Fwww.instagram.com%2Fpizzaflam%2F&h=AT1"
        assert _clean_social_url(raw) == "https://www.instagram.com/pizzaflam/"

    def test_unwraps_login_next(self) -> None:
        raw = "https://www.facebook.com/login/?next=https%3A%2F%2Fwww.facebook.com%2FPizzaFlam44"
        assert _clean_social_url(raw) == "https://www.facebook.com/PizzaFlam44"

    def test_bare_login_redirect_dropped(self) -> None:
        raw = "https://www.facebook.com/login/device-based/regular/login/?login_attempt=1"
        assert _clean_social_url(raw) == ""

    def test_plain_profile_preserved(self) -> None:
        assert _clean_social_url("https://www.instagram.com/pizzaflam44/") == "https://www.instagram.com/pizzaflam44/"


class TestWebsiteBelongsToBusiness:
    def test_third_party_partner_link_rejected(self) -> None:
        assert (
            _website_belongs_to_business(
                "http://www.agriethique.fr/", "B&B le Food truck Spécialiste du Burger à Nantes"
            )
            is False
        )

    def test_matching_domain_kept(self) -> None:
        assert _website_belongs_to_business("https://pizzaflam.fr", "PIZZ'A FLAM") is True

    def test_hyphenated_domain_kept(self) -> None:
        assert _website_belongs_to_business("https://www.chez-marcel.fr", "Chez Marcel") is True

    def test_unknown_name_keeps_website(self) -> None:
        assert _website_belongs_to_business("https://anything.com", None) is True


class TestParseCityPostal:
    def test_facebook_coordonnees_block(self) -> None:
        assert _parse_city_postal(_ABOUT_TEXT) == ("Châtellerault", "86100")

    def test_street_address_order(self) -> None:
        assert _parse_city_postal("12 rue de la Paix, 44000 Nantes") == ("Nantes", "44000")

    def test_city_france_postal_inline(self) -> None:
        assert _parse_city_postal("Paris, France, 75011") == ("Paris", "75011")

    def test_no_address_returns_none(self) -> None:
        assert _parse_city_postal("Aucune adresse ici", "") == (None, None)

    def test_quebec_page_reads_its_postal_code_shape(self) -> None:
        assert _parse_city_postal("Montréal, QC H2X 1Y4", country="CA") == ("Montréal", "H2X 1Y4")
        assert _parse_city_postal("Laval, Québec, Canada h7n 1a1", country="CA") == ("Laval", "H7N 1A1")
        assert _parse_city_postal("123 Rue X, Montréal, QC H2X 1Y4", country="CA") == ("Montréal", "H2X 1Y4")
        # Five French digits mean nothing on a Québec page, and a Québec code nothing on a French one.
        assert _parse_city_postal("Paris, France, 75011", country="CA") == (None, None)
        assert _parse_city_postal("Montréal, QC H2X 1Y4", country="FR") == (None, None)

    def test_swiss_page_reads_four_digits(self) -> None:
        assert _parse_city_postal("Genève, Suisse, 1204", country="CH") == ("Genève", "1204")
        assert _parse_city_postal("Rue du Rhône 12, 1204 Genève", country="CH") == ("Genève", "1204")


class TestParsePhone:
    def test_coordonnees_block(self) -> None:
        assert _parse_phone(_ABOUT_TEXT) == "06 29 34 58 99"

    def test_compact_digits_normalised(self) -> None:
        assert _parse_phone("Contact : 0629345899") == "06 29 34 58 99"

    def test_international_prefix_converted(self) -> None:
        assert _parse_phone("Tél : +33 6 29 34 58 99") == "06 29 34 58 99"

    def test_dotted_format(self) -> None:
        assert _parse_phone("06.29.34.58.99") == "06 29 34 58 99"

    def test_number_inside_longer_digit_run_rejected(self) -> None:
        # A SIRET or order id must not be mistaken for a phone number.
        assert _parse_phone("SIRET 06293458990001") is None

    def test_no_phone_returns_none(self) -> None:
        assert _parse_phone("Aucun numéro ici", "") is None

    def test_quebec_page_reads_the_north_american_plan(self) -> None:
        assert _parse_phone("Téléphone : (514) 555-0199", country="CA") == "514 555-0199"
        assert _parse_phone("Appelez au +1 438 555 0100", country="CA") == "438 555-0100"
        # A ten-digit Québec number is never read as a French one, and vice versa.
        assert _parse_phone("Téléphone : 514 555-0199", country="FR") is None
        assert _parse_phone("Tél : 06 29 34 58 99", country="CA") is None


class TestFacebookScrapeEmptyGuard:
    """An empty Facebook-anchored scrape is a FAILURE, never a valid « no data » result."""

    @staticmethod
    def _is_empty(prospect: object, data: EnrichmentData) -> bool:
        from services.enrichment_service import EnrichmentService

        return EnrichmentService._facebook_scrape_is_empty(prospect, data)  # type: ignore[arg-type]

    def test_empty_payload_flagged(self) -> None:
        prospect = SimpleNamespace(facebook_url="https://www.facebook.com/PizzaFlam44")
        assert self._is_empty(prospect, EnrichmentData(source="facebook")) is True

    def test_payload_with_title_passes(self) -> None:
        prospect = SimpleNamespace(facebook_url="https://www.facebook.com/PizzaFlam44")
        assert self._is_empty(prospect, EnrichmentData(source="facebook", place_title="PIZZ'A FLAM")) is False

    def test_payload_with_emails_passes(self) -> None:
        prospect = SimpleNamespace(facebook_url="https://www.facebook.com/PizzaFlam44")
        assert self._is_empty(prospect, EnrichmentData(source="facebook", emails=["a@b.fr"])) is False

    def test_prospect_without_facebook_url_not_guarded(self) -> None:
        prospect = SimpleNamespace(facebook_url=None)
        assert self._is_empty(prospect, EnrichmentData(source="facebook")) is False

    def test_google_sourced_payload_not_guarded(self) -> None:
        prospect = SimpleNamespace(facebook_url="https://www.facebook.com/PizzaFlam44")
        assert self._is_empty(prospect, EnrichmentData(source="google")) is False
