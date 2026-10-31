"""
What an enrichment reads changes what the app knows of a prospect: the website it finds is checked, a listing
titled after a network sets the prospect aside, the known Facebook page reaches the generated site, and a name
the registry contradicts is flagged instead of proposed alone.
"""

import asyncio
from typing import Any

import pytest
from sqlalchemy.orm import Session

from enums.identity_check_status import IdentityCheckStatus
from enums.website_status import WebsiteStatus
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from scrappers.enrichment_scraper import EnrichmentData
from services.decision_maker.resolver import decision_maker_resolver
from services.decision_maker.types import NameCandidate, NameResolution, ResolutionContext
from services.enrichment_service import EnrichmentService, enrichment_service
from services.photo_labeling_service import photo_labeling_service
from services.professional_license_service import professional_license_service
from services.prospect_service import prospect_service
from services.scraper_diagnostics_service import scraper_diagnostics_service
from services.website_liveness_service import website_liveness_service

_USER_ID = 1


@pytest.fixture
def offline_enrichment(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, str]]:
    """The registers, the licences, the photo labels and the monitoring stay offline; every website answers."""
    set_aside: list[tuple[int, str]] = []

    async def no_contact(self: EnrichmentService, db: Session, prospect: ProspectDB, record: Any) -> None:
        return None

    async def no_license(db: Session, prospect: ProspectDB, record: Any) -> None:
        return None

    async def live(website: str | None) -> WebsiteStatus | None:
        return WebsiteStatus.LIVE if website else None

    def dismiss(db: Session, prospect_id: int, *, reason: str, dismissed_by_user_id: int | None) -> None:
        set_aside.append((prospect_id, reason))

    monkeypatch.setattr(EnrichmentService, "_resolve_contact", no_contact)
    monkeypatch.setattr(professional_license_service, "resolve_for_enrichment", no_license)
    monkeypatch.setattr(photo_labeling_service, "schedule", lambda prospect_id: None)
    monkeypatch.setattr(scraper_diagnostics_service, "record", lambda **_fields: None)
    monkeypatch.setattr(website_liveness_service, "check_website_status", live)
    monkeypatch.setattr(prospect_service, "dismiss", dismiss)
    return set_aside


def _garage(db: Session, name: str, *, facebook_url: str | None = None) -> ProspectDB:
    """A garage the search validated, its Maps listing stored."""
    prospect = ProspectDB(
        name=name,
        city="Montluçon",
        country="FR",
        category="garage automobile",
        source="search",
        confidence=3,
        user_id=_USER_ID,
        google_maps_url="https://www.google.com/maps?cid=123456789",
        facebook_url=facebook_url,
    )
    db.add(prospect)
    db.commit()
    return prospect


def _enrich(db: Session, prospect: ProspectDB, data: EnrichmentData) -> ProspectEnrichment:
    """Persist a payload the desktop scraped for the prospect."""
    return asyncio.run(enrichment_service.enrich(db, _USER_ID, prospect, scraped_data=data))


def test_a_website_the_enrichment_finds_is_checked_and_a_live_one_says_the_garage_has_a_site(
    db: Session, offline_enrichment: list[tuple[int, str]]
) -> None:
    prospect = _garage(db, "DAC Automobiles")

    _enrich(db, prospect, EnrichmentData(website="http://www.dacautomobiles-narrosse.fr/", rating=4.6))

    assert (prospect.website, prospect.website_status) == (
        "http://www.dacautomobiles-narrosse.fr/",
        WebsiteStatus.LIVE.value,
    )


def test_a_listing_titled_after_a_network_sets_the_garage_aside(
    db: Session, offline_enrichment: list[tuple[int, str]]
) -> None:
    prospect = _garage(db, "Garage des Marais")

    _enrich(db, prospect, EnrichmentData(place_title="Garage des Marais - Motrio", rating=4.8))

    assert offline_enrichment == [
        (
            prospect.id,
            "Sa fiche Google « Garage des Marais - Motrio » est celle d'un réseau ou d'une marque : le patron ne "
            "décide pas seul.",
        )
    ]


def test_an_independent_garage_s_listing_sets_nothing_aside(
    db: Session, offline_enrichment: list[tuple[int, str]]
) -> None:
    prospect = _garage(db, "Garage Exemple")

    _enrich(db, prospect, EnrichmentData(place_title="Garage Exemple - Mécanique toutes marques", rating=4.8))

    assert offline_enrichment == []


def test_the_known_facebook_page_of_the_garage_reaches_its_social_links(
    db: Session, offline_enrichment: list[tuple[int, str]]
) -> None:
    page = "https://www.facebook.com/aquitainenegoceauto"
    prospect = _garage(db, "Aquitaine Négoce Auto", facebook_url=page)

    record = _enrich(db, prospect, EnrichmentData(rating=4.9, social_links={"instagram": "https://instagram.com/x"}))

    assert record.social_links == {"instagram": "https://instagram.com/x", "facebook": page}


def test_a_name_the_registry_contradicts_is_flagged_as_a_conflict(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    """The company of the garage's name writes another person than the one-person company of the proposed name."""
    prospect = _garage(db, "Garage Exemple et Fils")
    record = ProspectEnrichment(prospect_id=prospect.id, user_id=_USER_ID)
    db.add(record)
    db.commit()
    head_of_the_garage = NameCandidate(
        first="Marc",
        last="Exemple",
        source="registre_gouv",
        confidence=0.75,
        primary=True,
        geo_confirmed=True,
        provenance="Registre officiel (SIRENE) : GARAGE EXEMPLE ET FILS, SIREN 123456789",
    )
    head_of_another_company = NameCandidate(
        first="Patrick",
        last="Exemple",
        source="web_registry",
        confidence=0.95,
        primary=True,
        geo_confirmed=True,
        provenance="Recherche web → Registre officiel (SIRENE) : PATRICK EXEMPLE, SIREN 987654321",
    )

    async def resolve(context: ResolutionContext) -> NameResolution:
        return NameResolution(
            status=NameResolution.PROPOSED,
            candidate=head_of_another_company,
            candidates=[head_of_the_garage, head_of_another_company],
        )

    monkeypatch.setattr(decision_maker_resolver, "resolve", resolve)
    monkeypatch.setattr(scraper_diagnostics_service, "record", lambda **_fields: None)

    asyncio.run(EnrichmentService()._resolve_contact(db, prospect, record))

    assert record.identity_check_status == IdentityCheckStatus.CONFLICT.value
    assert record.identity_check_detail is not None
    assert record.identity_check_detail.startswith("Patrick Exemple est proposé, mais le registre inscrit Marc Exemple")
    assert (record.proposed_first_name, record.proposed_state, record.contact_first_name) == (
        "Patrick",
        "pending",
        None,
    )
