"""
A « nom + ville » Maps search that lands on a results list (third enrichment round, 8 Oct 2026): the app read
the list's heading « Résultats » as the place's name, so its identity guard threw away all seven leads, two of
which had their place in the list; opening the first result instead would have read a podiatrist's place for an
electrician. A lead with nothing to read was not even posted, so no register was read for it.
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
from scrappers.maps_search_results import ListedPlace, MapsSearchResults
from services.enrichment_service import EnrichmentService, enrichment_service
from services.professional_license_service import professional_license_service
from services.scraper_diagnostics_service import scraper_diagnostics_service

_USER_ID = 1


def _listed(*names: str) -> list[ListedPlace]:
    """A results list showing these places, in this order."""
    return [
        ListedPlace(name=name, link=f"https://www.google.com/maps/place/{index}") for index, name in enumerate(names)
    ]


def _opened(places: list[ListedPlace], business_name: str) -> list[str]:
    """The names of the listed places the enrichment opens for this business, in order."""
    return [place.name for place in MapsSearchResults.places_named_like(places, business_name)]


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
    assert MapsSearchResults.is_in_other_town(address, city=city, country=country) is is_elsewhere


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
    """The registers and the monitoring stay offline; the prospects whose decision maker was looked for."""
    resolved: list[int] = []

    async def resolve_contact(self: EnrichmentService, db: Session, prospect: ProspectDB, record: Any) -> None:
        resolved.append(prospect.id)

    async def no_license(db: Session, prospect: ProspectDB, record: Any) -> None:
        return None

    monkeypatch.setattr(EnrichmentService, "_resolve_contact", resolve_contact)
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


def test_an_empty_read_never_undoes_a_finished_enrichment(db: Session, resolved_prospect_ids: list[int]) -> None:
    """A place that a later search cannot find keeps the enrichment read from it earlier."""
    prospect = _prospect(db)
    _enrich(db, prospect, EnrichmentData(rating=4.8, maps_listing_found=True))

    record = _enrich(db, prospect, EnrichmentData(maps_listing_found=False))

    assert (record.status, record.rating, record.error_message) == (EnrichmentStatus.COMPLETED.value, 4.8, None)


@pytest.mark.parametrize(
    ("maps_listing_found", "reason_start"),
    [(False, "Rien à lire"), (True, "La fiche Google de l'entreprise est vide"), (None, "Rien n'a pu être lu")],
)
def test_an_empty_enrichment_says_why(maps_listing_found: bool | None, reason_start: str) -> None:
    """No place of that name, an empty place, or an unread page: three reasons the drawer tells apart."""
    reason = EnrichmentService._nothing_found_reason(EnrichmentData(maps_listing_found=maps_listing_found))
    assert reason.startswith(reason_start)
