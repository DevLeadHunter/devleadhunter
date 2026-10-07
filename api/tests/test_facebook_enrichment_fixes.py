"""Unit tests for the 2026-08 Facebook enrichment fixes (website / city-postal / social)."""

from types import SimpleNamespace

from scrappers.enrichment_scraper import EnrichmentData
from scrappers.facebook_enrichment_scraper import (
    FacebookEnrichmentScraper,
    _clean_social_url,
    _parse_best_description,
    _parse_city_postal,
    _parse_og_description,
    _parse_phone,
    _pick_description,
    _website_belongs_to_business,
)
from services.sms.phone_normalizer import to_e164

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

_SWISS_ABOUT_TEXT = """Sanitaire Rochat
À propos
Coordonnées
Lausanne, Suisse, 1004
Adresse
+41 79 123 45 67
Mobile
Recommandé par 98 % (41 avis)"""


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

    def test_belgian_and_luxembourg_pages_read_four_digits(self) -> None:
        assert _parse_city_postal("Liège, Belgique, 4000", country="BE") == ("Liège", "4000")
        assert _parse_city_postal("Chaussée de Waterloo 1234, 1180 Uccle", country="BE") == ("Uccle", "1180")
        assert _parse_city_postal("Rue de la Gare 12, L-1611 Luxembourg", country="LU") == ("Luxembourg", "1611")
        assert _parse_city_postal("Esch-sur-Alzette, Luxembourg, 4011", country="LU") == ("Esch-sur-Alzette", "4011")


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

    def test_swiss_page_reads_its_international_and_national_numbers(self) -> None:
        assert _parse_phone("Coordonnées\n+41 79 123 45 67\nMobile", country="CH") == "079 123 45 67"
        assert _parse_phone("Tél. 079/123 45 67", country="CH") == "079 123 45 67"
        assert _parse_phone("Atelier : +41 (0)21 123 45 67", country="CH") == "021 123 45 67"
        assert _parse_phone("+41 79 123 45 67", country="FR") is None

    def test_a_swiss_079_is_a_swiss_mobile_never_a_false_french_one(self) -> None:
        phone = _parse_phone("Contact : 0791234567", country="CH")
        assert phone == "079 123 45 67"
        assert to_e164(phone, country="CH") == "+41791234567"
        assert _parse_phone("Tél : 06 29 34 58 99", country="CH") is None

    def test_belgian_mobile_keeps_its_four_digit_prefix(self) -> None:
        assert _parse_phone("Appelez-nous au 0470 12 34 56", country="BE") == "0470 12 34 56"
        assert _parse_phone("GSM : 0470/12.34.56", country="BE") == "0470 12 34 56"
        assert _parse_phone("+32 470 12 34 56", country="BE") == "0470 12 34 56"
        assert _parse_phone("Bureau : 02 511 11 11", country="BE") == "02 511 11 11"

    def test_luxembourg_page_reads_numbers_without_a_trunk_zero(self) -> None:
        assert _parse_phone("Tél. +352 26 12 34 56", country="LU") == "26 12 34 56"
        assert _parse_phone("Mobile 621 123 456", country="LU") == "621 123 456"
        assert _parse_phone("1 234 567 J’aime", country="LU") is None


class TestSwissFacebookPage:
    """A Swiss page read end to end: city, postal code and phone in the prospect's country."""

    def test_read_as_swiss_the_page_gives_its_city_postal_code_and_mobile(self) -> None:
        data = FacebookEnrichmentScraper._build_from_raw({"about_text": _SWISS_ABOUT_TEXT}, "", country="CH")
        assert (data.place_city, data.place_postal_code, data.phone) == ("Lausanne", "1004", "079 123 45 67")

    def test_read_as_french_the_same_page_gives_nothing(self) -> None:
        data = FacebookEnrichmentScraper._build_from_raw({"about_text": _SWISS_ABOUT_TEXT}, "")
        assert (data.place_city, data.place_postal_code, data.phone) == (None, None, None)


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


class TestPageDescription:
    """The description is the page's own presentation (first enrichment round, 7 Oct 2026)."""

    _INTRO = "Intro\nL'accueil et la qualité de notre service sont irréprochables. Contactez-nous!\nPage · Garage"
    _OLD_POST = (
        "Veuillez noter que nous serons fermés ce vendredi afin de procéder à notre déménagement. Nos "
        "opérations reprendront lundi dès 7h30 à nos nouveaux locaux, rue de l'Exemple."
    )

    def test_the_intro_wins_over_a_longer_old_post(self) -> None:
        """A garage's 2017 « we are moving » post had become its description."""
        description = _pick_description(
            intro_text=self._INTRO, about_text="", og_description=None, embedded_texts=[self._OLD_POST]
        )

        assert description == "L'accueil et la qualité de notre service sont irréprochables. Contactez-nous!"

    def test_a_cut_intro_ends_on_its_last_whole_sentence(self) -> None:
        """« … paysagiste. J'interviens à tous » stops mid-sentence: the half sentence goes."""
        intro = "Intro\nDécouvrez mes créations de jardinier paysagiste.\nJ’interviens à tous\nPage · Jardinier"

        description = _pick_description(intro_text=intro, about_text="", og_description=None, embedded_texts=[])

        assert description == "Découvrez mes créations de jardinier paysagiste."

    def test_a_fuller_text_completes_a_cut_intro(self) -> None:
        """A text opening like the intro and going further is the uncut presentation."""
        intro = "Intro\nDécouvrez mes créations de jardinier paysagiste.\nJ’interviens à tous\nPage · Jardinier"
        full = "Découvrez mes créations de jardinier paysagiste. J’interviens à tous les étages du jardin."

        description = _pick_description(intro_text=intro, about_text="", og_description=None, embedded_texts=[full])

        assert description == full

    def test_og_description_loses_its_name_town_and_audience(self) -> None:
        """« Exemple Paysagiste, Morges. 91 followers. Découvrez… » keeps only the presentation."""
        og = "Exemple Paysagiste, Morges. 91 followers. Découvrez mes créations de jardinier paysagiste."

        assert _parse_og_description(og) == "Découvrez mes créations de jardinier paysagiste."

    def test_og_description_loses_its_visits_count_too(self) -> None:
        """« Garage Exemple, Terrebonne. 53 followers · 5 personnes étaient ici. L'accueil… »"""
        og = "Garage Exemple, Terrebonne. 53 followers · 5 personnes étaient ici. L'accueil et la qualité sont irréprochables."

        assert _parse_og_description(og) == "L'accueil et la qualité sont irréprochables."


class TestFullPageDescription:
    """The page's full description wins, whole (second enrichment round, 7 Oct 2026)."""

    def test_the_full_description_wins_over_the_cut_intro(self) -> None:
        """The Intro card and og:description cut the text; the page data holds it whole."""
        full = "Paysagiste de formation.\nPlus de 25 ans d'expérience.\nDallage, pavage, taille des arbres, clôture."
        intro = "Intro\nPaysagiste de formation.\nPage · Jardinier"

        description = _pick_description(
            intro_text=intro, about_text="", og_description=None, embedded_texts=[], best_description=full
        )

        assert (
            description
            == "Paysagiste de formation. Plus de 25 ans d'expérience. Dallage, pavage, taille des arbres, clôture."
        )

    def test_a_list_without_final_dot_is_kept_whole(self) -> None:
        """« GARAGE DE MÉCANIQUE . AIR CLIMATISÉ, FREIN » was cut to its first words: a full text is never cut."""
        full = "GARAGE DE MÉCANIQUE AUTOMOBILE . AIR CLIMATISÉ, FREIN, SILENCIEUX"

        assert _parse_best_description(full) == full

    def test_a_text_the_owner_left_cut_ends_on_its_last_whole_sentence(self) -> None:
        """« … J'interviens à tous... » loses its half sentence."""
        assert (
            _parse_best_description("Paysagiste depuis 20 ans. J'interviens à tous...") == "Paysagiste depuis 20 ans."
        )

    def test_dots_after_a_space_are_an_etc_not_a_cut(self) -> None:
        """« … auto-location, électricité ... » is whole: the owner's dots stand for « etc. »."""
        full = "Garage Exemple, Réparations toutes marques, auto-location, électricité ..."

        assert _parse_best_description(full) == full

    def test_a_text_cut_before_its_first_sentence_ends_gives_nothing(self) -> None:
        """« … d'exploitation de forê... » would show a broken word on the site: nothing is better."""
        assert (
            _parse_best_description("L'entreprise Exemple vous propose des services d'exploitation de forê...") is None
        )

    def test_og_description_of_a_dotted_name_loses_its_prefix(self) -> None:
        """« I.H Exemple. 112 followers. … » kept its name and audience: the dots of the name stopped the cleaning."""
        og = "I.H Exemple. 112 followers. Paysagiste de formation, plus de 25 ans d'expérience à Sion."

        assert _parse_og_description(og) == "Paysagiste de formation, plus de 25 ans d'expérience à Sion."

    def test_the_services_of_an_intro_list_are_read(self) -> None:
        """An emoji list in the Intro card gives the services, the quote and network lines left out."""
        dom = {
            "place_title": "Exemple Paysages",
            "intro_text": "Intro\n🌳 Abattage • Elagage • Dessouchage\n🌿 Aménagement paysager\n📩 Soumission rapide\nPage · Paysagiste",
        }

        data = FacebookEnrichmentScraper._build_from_raw(dom, "")

        assert data.services == ["Abattage", "Elagage", "Dessouchage", "Aménagement paysager"]
