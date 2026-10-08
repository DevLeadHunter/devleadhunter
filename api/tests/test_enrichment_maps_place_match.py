"""
A « nom + ville » Maps search that lands on a results list (third enrichment round, 8 Oct 2026): the app read
the list's heading « Résultats » as the place's name, so its identity guard threw away all seven leads, two of
which had their place in the list; opening the first result instead would have read a podiatrist's place for an
electrician. A lead with nothing to read was not even posted, so no register was read for it, and nobody looked
for its Facebook page, which a plain web search finds.
"""

import asyncio
from typing import Any

import pytest
from sqlalchemy.orm import Session

from enrich_cli import _is_worth_persisting
from enums.enrichment_status import EnrichmentStatus
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from scrappers.enrichment_scraper import EnrichmentData
from scrappers.maps_place_match import ListedPlace, MapsPlaceMatch
from services.enrichment_service import EnrichmentService, enrichment_service
from services.professional_license_service import professional_license_service
from services.prospect_search.candidate_facts import CandidateFacts
from services.prospect_search.contact_finder import ContactFinder
from services.prospect_search.search_judge import search_judge
from services.prospect_search.trade_catalog import TradeCatalog
from services.scraper_diagnostics_service import scraper_diagnostics_service
from services.validation_service import ValidationService

_USER_ID = 1


class _SearchResultsClient:
    """Stands in for Bright Data: every web search answers the same results."""

    def __init__(self, results: list[dict[str, str]]) -> None:
        self._results = results

    async def google_parsed(self, query: str, *, country: str = "FR", start: int = 0, local: bool = False) -> Any:
        """The prepared results, whatever the query."""
        return {"organic": self._results}


def _listed(*names: str) -> list[ListedPlace]:
    """A results list showing these places, in this order."""
    return [
        ListedPlace(name=name, link=f"https://www.google.com/maps/place/{index}") for index, name in enumerate(names)
    ]


def _opened(places: list[ListedPlace], business_name: str, town: str = "Pau") -> list[str]:
    """The names of the listed places the enrichment opens for this business, in order."""
    return [place.name for place in MapsPlaceMatch.places_named_like(places, business_name, town=town)]


def test_a_one_word_name_is_not_read_in_a_namesake_listed_first() -> None:
    """« Exemple » is the electrician « Exemple Sarl », never « Exemple Jules », a podiatrist listed first."""
    assert _opened(_listed("Exemple Jules", "Exemple Sarl"), "Exemple") == ["Exemple Sarl"]


def test_a_one_word_name_still_matches_a_place_adding_its_trade() -> None:
    """A place adding only a trade word to the name is the business."""
    assert _opened(_listed("Exemple Électricité", "Électricité Exemple"), "Exemple") == [
        "Exemple Électricité",
        "Électricité Exemple",
    ]


def test_the_owner_s_old_place_is_passed_over_for_the_places_named_like_the_business() -> None:
    """Of three places under the family name, only the two named like the business are opened, in the list's order."""
    places = _listed("Exemple Jules", "Exemple électricité", "exemple électricité")
    assert _opened(places, "Exemple Electricite") == ["Exemple électricité", "exemple électricité"]


def test_dotted_initials_read_as_the_business_initials() -> None:
    """« A.B. Électrique » is « AB électrique »; « AB Elec » and an AB sign maker are not."""
    places = _listed("A.B. Électrique", "AB Elec", "Électricité AB Enseignes")
    assert _opened(places, "AB électrique") == ["A.B. Électrique"]


def test_a_neighbour_of_the_same_trade_is_never_opened() -> None:
    """Sharing the trade word, the legal form or a two-letter acronym is no shared name."""
    places = _listed("Groupe QR Électrique inc", "QRS Électrique Inc.")
    assert _opened(places, "XYZ électrique inc.") == []
    assert _opened(places, "ÉnerExemple QR inc.") == []


def test_a_place_name_is_read_without_its_tagline() -> None:
    """The words a place adds after a dash to be found are not part of its name."""
    assert _opened(_listed("Exemple Électrique Inc - Maître Électricien Laval"), "Exemple Électrique") == [
        "Exemple Électrique Inc - Maître Électricien Laval"
    ]


def test_at_most_three_places_are_opened() -> None:
    """A long list of places named alike costs three openings, not one per place."""
    assert len(_opened(_listed(*["Exemple Paysage"] * 5), "Exemple Paysage")) == 3


def test_the_place_maps_opens_itself_must_carry_the_owner_s_full_name() -> None:
    """Maps opened a namesake sharing the owner's first name for a sole trader: it is not the business."""
    assert not MapsPlaceMatch.is_named_like("Exemple Jules", "Entreprise Individuelle Modèle Jules", town="Pau")
    assert MapsPlaceMatch.is_named_like("Modèle Jules", "Entreprise Individuelle Modèle Jules", town="Pau")


def test_trade_words_and_linking_words_do_not_count_against_a_name() -> None:
    """« Exemple & Fils Électricité Générale » is « Exemple Et Fils », « Modèle Électricité » is « Eurl Modèle Elec »."""
    assert MapsPlaceMatch.is_named_like("Exemple & Fils Electricite Generale", "Exemple Et Fils", town="Pau")
    assert MapsPlaceMatch.is_named_like("Modèle Electricité", "Eurl Modèle Elec", town="Pau")


def test_a_name_made_of_a_trade_and_a_town_must_match_word_for_word() -> None:
    """« Garage de Morges » is not the body shop of the same town."""
    places = _listed("Carrosserie de Morges", "Garage de Morges Sàrl")
    assert _opened(places, "Garage de Morges", town="Morges") == ["Garage de Morges Sàrl"]


def test_the_server_refuses_a_namesake_the_way_the_scraper_does() -> None:
    """An older desktop app may still send a namesake's place: the identity guard refuses it too."""
    reason = ValidationService.place_identity_mismatch(
        prospect_name="Entreprise Individuelle Modèle Jules",
        prospect_city="Pau",
        prospect_postal_code=None,
        place_title="Exemple Jules",
        place_city=None,
        place_postal_code=None,
    )
    assert reason is not None and "ne correspond pas" in reason


@pytest.mark.parametrize(
    ("address", "city", "country", "is_elsewhere"),
    [
        ("23 Rue Exemple, 64100 Bayonne", "Bidart", "FR", True),
        ("Le Tel, 81100 Castres", "Castres", "FR", False),
        ("144 Rue Exemple, Québec, QC G1C 1A1", "Trois-Rivières", "CA", True),
        ("1335 Côte Exemple, Terrebonne, QC J6Y 1G6", "Terrebonne", "CA", False),
        (None, "Bidart", "FR", False),
    ],
)
def test_a_place_in_another_town_is_passed_over(
    address: str | None, city: str, country: str, is_elsewhere: bool
) -> None:
    """The town the address names decides; a place listed without an address is kept."""
    assert MapsPlaceMatch.is_in_other_town(address, city=city, country=country) is is_elsewhere


@pytest.mark.parametrize(
    ("data", "is_posted"),
    [
        (EnrichmentData(), False),
        (EnrichmentData(maps_listing_found=False), True),
        (EnrichmentData(maps_listing_found=True), True),
        (EnrichmentData(rating=4.8), True),
    ],
)
def test_the_cli_posts_a_sure_answer_even_empty_but_never_an_unread_page(data: EnrichmentData, is_posted: bool) -> None:
    """A blocked read never overwrites good data; « no place of that name » is still worth recording."""
    assert _is_worth_persisting(data) is is_posted


@pytest.fixture
def resolved_prospect_ids(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """The registers, the web search and the monitoring stay offline; the prospects whose decision maker was looked for."""
    resolved: list[int] = []

    async def resolve_contact(self: EnrichmentService, db: Session, prospect: ProspectDB, record: Any) -> None:
        resolved.append(prospect.id)

    async def no_license(db: Session, prospect: ProspectDB, record: Any) -> None:
        return None

    async def no_facebook_page(prospect: ProspectDB) -> str | None:
        return None

    monkeypatch.setattr(EnrichmentService, "_resolve_contact", resolve_contact)
    monkeypatch.setattr(EnrichmentService, "_search_facebook_page", staticmethod(no_facebook_page))
    monkeypatch.setattr(professional_license_service, "resolve_for_enrichment", no_license)
    monkeypatch.setattr(scraper_diagnostics_service, "record", lambda **_fields: None)
    return resolved


def _prospect(db: Session) -> ProspectDB:
    """An electrician found by a register, with no Maps place or page stored."""
    prospect = ProspectDB(
        name="Exemple Électricité",
        city="Bidart",
        country="FR",
        category="électricien",
        source="search",
        confidence=3,
        user_id=_USER_ID,
    )
    db.add(prospect)
    db.commit()
    return prospect


def _enrich(db: Session, prospect: ProspectDB, data: EnrichmentData) -> ProspectEnrichment:
    """Persist a payload the desktop scraped for the prospect."""
    return asyncio.run(enrichment_service.enrich(db, _USER_ID, prospect, scraped_data=data))


def test_a_business_with_no_place_says_so_and_still_reads_the_registers(
    db: Session, resolved_prospect_ids: list[int]
) -> None:
    """Nothing to read is no finished enrichment, and the decision maker is still looked for."""
    prospect = _prospect(db)

    record = _enrich(db, prospect, EnrichmentData(maps_listing_found=False))

    assert record.status == EnrichmentStatus.FAILED.value
    assert (record.error_message or "").startswith("Rien à lire")
    assert resolved_prospect_ids == [prospect.id]


def test_a_business_google_has_nothing_about_gets_its_facebook_page_to_read(
    db: Session, resolved_prospect_ids: list[int], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The page a web search finds is stored on the prospect, so the next enrichment reads it."""

    async def page_found(prospect: ProspectDB) -> str | None:
        return "https://www.facebook.com/exemple.electricite"

    monkeypatch.setattr(EnrichmentService, "_search_facebook_page", staticmethod(page_found))
    prospect = _prospect(db)

    record = _enrich(db, prospect, EnrichmentData(maps_listing_found=False))

    assert prospect.facebook_url == "https://www.facebook.com/exemple.electricite"
    assert (record.error_message or "").startswith("Pas de fiche Google, mais sa page Facebook est trouvée")


def test_the_web_search_keeps_the_page_of_the_business_and_not_a_namesake_s() -> None:
    """Only a page named like the business, in its town, showing no other phone number, is its page."""
    results = [
        {
            "link": "https://www.facebook.com/exemple.homonyme/",
            "title": "Exemple Électricité | Lyon",
            "description": "Exemple Électricité, Lyon. Électricien 04 72 00 00 00.",
        },
        {
            "link": "https://www.facebook.com/exemple.electricite/",
            "title": "Exemple Électricité | Bidart",
            "description": "Exemple Électricité, Bidart. 120 followers. Électricien 06 12 34 56 78.",
        },
    ]
    facts = CandidateFacts(
        name="Exemple Électricité",
        trade_key="electricien",
        country="FR",
        origin="search",
        city="Bidart",
        phone="06 12 34 56 78",
    )
    finder = ContactFinder(_SearchResultsClient(results), search_judge)  # type: ignore[arg-type]

    page = asyncio.run(finder.find_facebook_page(facts, TradeCatalog.resolve("électricien")))

    assert page == "https://www.facebook.com/exemple.electricite"


def test_an_empty_read_never_undoes_a_finished_enrichment(db: Session, resolved_prospect_ids: list[int]) -> None:
    """A place that a later search cannot find keeps the enrichment read from it earlier."""
    prospect = _prospect(db)
    _enrich(db, prospect, EnrichmentData(rating=4.8, maps_listing_found=True))

    record = _enrich(db, prospect, EnrichmentData(maps_listing_found=False))

    assert (record.status, record.rating, record.error_message) == (EnrichmentStatus.COMPLETED.value, 4.8, None)


def test_an_enrichment_emptied_by_hand_is_no_finished_one(db: Session, resolved_prospect_ids: list[int]) -> None:
    """Once the data of a wrong place is cleared, a read finding nothing says so instead of « completed »."""
    prospect = _prospect(db)
    _enrich(db, prospect, EnrichmentData(rating=4.8, maps_listing_found=True))
    record = db.query(ProspectEnrichment).filter_by(prospect_id=prospect.id).one()
    record.rating = None
    db.commit()

    record = _enrich(db, prospect, EnrichmentData(maps_listing_found=False))

    assert record.status == EnrichmentStatus.FAILED.value


@pytest.mark.parametrize(
    ("maps_listing_found", "reason_start"),
    [(False, "Rien à lire"), (True, "La fiche Google de l'entreprise est vide"), (None, "Rien n'a pu être lu")],
)
def test_an_empty_enrichment_says_why(maps_listing_found: bool | None, reason_start: str) -> None:
    """No place of that name, an empty place, or an unread page: three reasons the drawer tells apart."""
    reason = EnrichmentService._nothing_found_reason(EnrichmentData(maps_listing_found=maps_listing_found))
    assert reason.startswith(reason_start)
