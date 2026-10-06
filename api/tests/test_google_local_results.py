"""Reading a Google local results page: the fields a candidate starts from."""

from scrappers.google_local_results import GoogleLocalResultsParser


def _card(name: str, lines: list[str], *, links: str = "") -> str:
    """One business card in the shape Google serves it."""
    body = "".join(f"<div>{line}</div>" for line in lines)
    return (
        '<div class="VkpGBb"><div><div class="rllt__details">'
        f'<div role="heading"><span>{name}</span></div>{body}'
        f"</div></div>{links}</div>"
    )


_DIRECTIONS = (
    '<a href="/maps/dir//Filvert+Sarl,+Rue+de+la+Garenne+20,+1950+Sion/'
    'data=!4m6!4m5!1m1!4e2!1m2!1m1!1s0x478edc8a846f513d:0x66d92e58019e9a3e?sa=X">Itinéraire</a>'
)
_WEBSITE = '<a href="/goto?url=CAESVQHrOzAV">Site Web</a>'

_PAGE = (
    "<html><body>"
    + "".join(
        [
            _card(
                "Filvert Sarl",
                [
                    "5,0 (17) · Paysagiste",
                    "Plus de 7 ans en activité · Sion",
                    "Fermé · Ouvre à 07:30 lun. · 079 473 19 61",
                ],
                links=_WEBSITE + _DIRECTIONS,
            ),
            _card("Graine de Vie paysage", ["5,0 (5) · Paysagiste", "Fermé · Ouvre à 07:30 lun. · 076 680 31 47"]),
            _card("Ancien Jardin", ["Aucun avis · Paysagiste", "Sion", "Définitivement fermé"]),
        ]
    )
    + "</body></html>"
)


def test_a_card_gives_name_rating_category_phone_and_town() -> None:
    listing = GoogleLocalResultsParser.parse_html(_PAGE, country="CH")[0]

    assert listing.name == "Filvert Sarl"
    assert listing.rating == 5.0
    assert listing.reviews_count == 17
    assert listing.category == "Paysagiste"
    assert listing.phone == "079 473 19 61"
    assert listing.locality == "Sion"
    assert listing.address == "Rue de la Garenne 20, 1950 Sion"


def test_the_website_button_and_the_google_identifier_are_read_from_the_links() -> None:
    listing = GoogleLocalResultsParser.parse_html(_PAGE, country="CH")[0]

    assert listing.has_website_button is True
    assert listing.website_link == "/goto?url=CAESVQHrOzAV"
    assert listing.cid == str(int("66d92e58019e9a3e", 16))
    assert listing.maps_url == f"https://www.google.com/maps?cid={listing.cid}"


def test_a_card_without_links_has_no_website_and_keeps_its_phone() -> None:
    listing = GoogleLocalResultsParser.parse_html(_PAGE, country="CH")[1]

    assert listing.has_website_button is False
    assert listing.phone == "076 680 31 47"
    assert listing.locality is None
    assert listing.cid is None


def test_a_closed_business_is_flagged_and_its_missing_rating_is_not_invented() -> None:
    listing = GoogleLocalResultsParser.parse_html(_PAGE, country="CH")[2]

    assert listing.is_permanently_closed is True
    assert listing.rating is None
    assert listing.category == "Paysagiste"


def test_a_quebec_card_reads_the_north_american_phone_and_drops_the_province() -> None:
    page = _card(
        "Toupet Entretien Paysager Inc",
        ["5,0 (16) · Paysagiste", "Trois-Rivières, QC", "Fermé · Ouvre à 08 h 00 dim. · (819) 609-6026"],
    )

    listing = GoogleLocalResultsParser.parse_html(page, country="CA")[0]

    assert listing.phone == "(819) 609-6026"
    assert listing.locality == "Trois-Rivières"


def test_a_card_without_category_keeps_its_phone_and_its_street_out_of_the_category() -> None:
    page = _card("Garage Lanaudière", ["4,6 (12) · (450) 755-6599", "Joliette, QC"]) + _card(
        "Mécanique Firestone", ["Aucun avis · 1475 Bd Firestone", "Joliette, QC"]
    )

    first, second = GoogleLocalResultsParser.parse_html(page, country="CA")

    assert (first.category, first.phone) == (None, "(450) 755-6599")
    assert second.category is None


def test_an_unrecognised_layout_yields_nothing_so_the_caller_falls_back() -> None:
    assert GoogleLocalResultsParser.parse_html("<html><body><div>Autre page</div></body></html>") == []


def test_the_parsed_json_fallback_keeps_what_it_carries_and_marks_the_website_unknown() -> None:
    listings = GoogleLocalResultsParser.parse_snack_pack(
        [
            {"cid": "1", "name": "Annonce", "sponsored": True},
            {
                "cid": "7770705969363714089",
                "name": "Plaschy Paysagiste Sàrl",
                "rating": 4.9,
                "reviews_cnt": 14,
                "type": "Paysagiste",
                "work_status": "Fermé",
                "address": "Plus de 5 ans en activité ⋅ Saint-Léonard",
            },
        ]
    )

    assert len(listings) == 1
    assert listings[0].locality == "Saint-Léonard"
    assert listings[0].has_website_button is None
    assert listings[0].phone is None


def test_in_the_searched_town_google_shows_the_street_which_is_an_address_not_a_town() -> None:
    page = _card("GARAGE M&D AUTOMOBILE", ["5,0 (31) · Garage automobile", "6 Av. de la Gineste · 07 60 62 30 90"])

    listing = GoogleLocalResultsParser.parse_html(page, country="FR")[0]

    assert listing.locality is None
    assert listing.address == "6 Av. de la Gineste"
    assert listing.phone == "07 60 62 30 90"


def test_a_layout_without_any_action_link_leaves_the_website_unknown() -> None:
    page = _card("Garage Delcloup", ["4,9 (65) · Atelier de réparation automobile", "Cahors · 05 65 35 37 92"])

    assert GoogleLocalResultsParser.parse_html(page, country="FR")[0].has_website_button is None
