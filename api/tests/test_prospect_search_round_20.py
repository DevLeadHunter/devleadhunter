"""
Round 20 of the search training (search n° 20, garages around Le Locle): the Swiss network of independent garages
read on a photo's sign, a Swiss locality Google writes as a bare article, and the partners and directors a firm's
gazette entries name. Each case is a real one, its names, numbers and people replaced.
"""

import asyncio
from datetime import date
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from scrappers.google_local_results import LocalListing
from services.decision_maker.swiss_register_people import RegisteredPerson, SwissRegisterPeople
from services.enrichment_service import EnrichmentService
from services.prospect_search.network_outlets import NetworkOutlets
from services.prospect_search.runner import ProspectSearchRunner
from services.prospect_search.swiss_registry import SwissRegisterFirm, swiss_registry
from services.swiss_localities import SwissLocalities, swiss_localities

_REAL_ASYNC_CLIENT = httpx.AsyncClient


@pytest.mark.parametrize(
    ("caption", "is_network_sign"),
    [
        (
            "Véhicule SUV noir stationné devant un garage nommé 'le GARAGE' avec d'autres voitures en arrière-plan.",
            True,
        ),
        ("Façade avec l'enseigne « le Garage » au-dessus de « Garage et Carrosserie multimarque ».", True),
        ("Voiture rouge stationnée devant le garage avec enseigne 'Carrosserie'.", False),
        ("Vue de l'atelier, le garage et l'enseigne 'Garage Exemple'.", False),
        ("Bâtiment d'un garage avec enseignes 'Garage', 'Carrosserie' et 'Peinture'.", False),
    ],
)
def test_the_swiss_network_le_garage_counts_only_quoted_as_a_name(caption: str, is_network_sign: bool) -> None:
    """The network of independent garages writes its sign « le GARAGE »: two everyday words anywhere else."""
    assert NetworkOutlets.shows_network_sign(caption) is is_network_sign


def _localities(monkeypatch: pytest.MonkeyPatch, by_postal_code: dict[str, list[str]]) -> None:
    async def localities_of(postal_code: str) -> list[str]:
        return by_postal_code.get(postal_code, [])

    monkeypatch.setattr(swiss_localities, "localities_of", localities_of)


@pytest.mark.parametrize(
    ("address", "mended"),
    [
        ("Le, Exemple-du-Lac 6, 2999 Le", ("Le Exemple-du-Lac", "Le Exemple-du-Lac 6, 2999 Le Exemple-du-Lac")),
        ("Le, Modèle 12, 2998 Le", ("Le Modèle", "Le Modèle 12, 2998 Le Modèle")),
        ("Rue de l'Exemple 88, 2998 Le", (None, "Rue de l'Exemple 88, 2998 Le")),
    ],
)
def test_a_town_read_as_a_bare_article_takes_the_locality_of_its_postal_code(
    monkeypatch: pytest.MonkeyPatch, address: str, mended: tuple[str | None, str]
) -> None:
    """2998 serves two localities: the address must name one, else the town stays unknown, never « Le »."""
    _localities(monkeypatch, {"2999": ["Le Exemple-du-Lac"], "2998": ["Le Exempleville", "Le Modèle"]})

    assert asyncio.run(swiss_localities.mended_town_and_address(address)) == mended


def test_the_federal_service_s_answer_gives_the_localities_of_a_postal_code(monkeypatch: pytest.MonkeyPatch) -> None:
    answer = {
        "results": [{"attrs": {"label": "<b>2999 - Le Exemple-du-Lac</b>"}}, {"attrs": {"label": "<b>2990 - X</b>"}}]
    }

    def build(**kwargs: Any) -> httpx.AsyncClient:
        return _REAL_ASYNC_CLIENT(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=answer)), **kwargs
        )

    monkeypatch.setattr(httpx, "AsyncClient", build)

    assert asyncio.run(SwissLocalities().localities_of("2999")) == ["Le Exemple-du-Lac"]


def test_a_swiss_listing_read_as_le_is_mended_before_it_becomes_a_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    _localities(monkeypatch, {"2999": ["Le Exemple-du-Lac"]})
    bare = LocalListing(name="Carrosserie Exemple", locality="Le", address="Le, Exemple-du-Lac 6, 2999 Le")
    placed = LocalListing(
        name="Garage Exemple", locality="Exempleville", address="Rue de l'Exemple 1, 2997 Exempleville"
    )

    asyncio.run(ProspectSearchRunner._mend_bare_article_towns([bare, placed]))

    assert (bare.locality, bare.address) == ("Le Exemple-du-Lac", "Le Exemple-du-Lac 6, 2999 Le Exemple-du-Lac")
    assert (placed.locality, placed.address) == ("Exempleville", "Rue de l'Exemple 1, 2997 Exempleville")


_PARTNERS = (
    "Garage Exemple SNC, Exempleville. Société en nom collectif qui a commencé le 10.05.2017. Associés: Exemple Jules "
    "et Exemple Paul, tous deux de Modèle, à Exempleville, lesquels signent individuellement. But: exploitation "
    "d'un garage automobile."
)


def test_partners_of_one_family_signing_alone_give_their_family_name() -> None:
    leads = SwissRegisterPeople.lead_people(SwissRegisterPeople.registered_people([(date(2019, 5, 21), _PARTNERS)]))

    assert [(lead.first_name, lead.last_name) for lead in leads] == [("Jules", "Exemple"), ("Paul", "Exemple")]
    assert SwissRegisterPeople.family_name_of(leads) == "Exemple"


def test_partners_of_two_families_give_no_family_name() -> None:
    publication = _PARTNERS.replace("Exemple Paul", "Temoin Paul")
    leads = SwissRegisterPeople.lead_people(SwissRegisterPeople.registered_people([(date(2019, 5, 21), publication)]))

    assert len(leads) == 2 and SwissRegisterPeople.family_name_of(leads) is None


def test_a_partner_without_signature_runs_nothing() -> None:
    """A shareholder of a limited company: « associé, pour 20 parts sociales, sans signature »."""
    publication = "Associés: Exemple Jules, de Modèle, à Exempleville, pour 20 parts sociales, sans signature."

    assert (
        SwissRegisterPeople.lead_people(SwissRegisterPeople.registered_people([(date(2020, 1, 6), publication)])) == []
    )


def test_a_director_granted_the_individual_signature_runs_the_business() -> None:
    publication = (
        "Exemple Cars Sàrl, à Exempleville, CHE-000.000.010 (FOSC du 19.12.2013). Signature individuelle a été "
        "conférée à Modèle dos Exemple Jules Paul, du Portugal, à Exempleville, directeur."
    )

    assert SwissRegisterPeople.lead_people(
        SwissRegisterPeople.registered_people([(date(2017, 2, 15), publication)])
    ) == [
        RegisteredPerson(
            first_name="Jules Paul", last_name="Modèle dos Exemple", roles=("directeur",), is_name_certain=False
        )
    ]


def test_the_family_name_of_the_partners_is_the_contact_and_the_greeting_stays_neutral(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    firm = SwissRegisterFirm(
        name="Garage Exemple SNC", seat="Exempleville", status="EXISTIEREND", uid="CHE-000.000.011", register_id=1
    )

    async def firms_named(name: str, *, max_entries: int = 10) -> list[SwissRegisterFirm]:
        return [firm]

    async def publications(_firm: SwissRegisterFirm) -> list[tuple[date, str]]:
        return [(date(2019, 5, 21), _PARTNERS)]

    monkeypatch.setattr(swiss_registry, "firms_named", firms_named)
    monkeypatch.setattr(swiss_registry, "publications", publications)
    fields = [
        "contact_first_name",
        "contact_last_name",
        "contact_gender",
        "contact_name_source",
        "contact_name_confidence",
        "contact_name_status",
        "contact_name_provenance",
        "contact_siren",
        "proposed_first_name",
        "proposed_last_name",
        "proposed_gender",
        "proposed_source",
        "proposed_confidence",
        "proposed_provenance",
        "proposed_state",
    ]
    record = SimpleNamespace(contact_name_manual=False, place_postal_code=None, reviews=[], **dict.fromkeys(fields))
    prospect = SimpleNamespace(
        id=1,
        name="Garage Exemple SNC",
        city="Exempleville",
        address=None,
        country="CH",
        is_dismissed=False,
        user_id=7,
        email=None,
        emails=[],
    )

    class _Session:
        def commit(self) -> None:
            """The record is a plain object."""

    asyncio.run(EnrichmentService()._read_swiss_register(_Session(), prospect, record, uid=None))

    assert (record.contact_first_name, record.contact_last_name, record.contact_gender) == (None, "Exemple", None)
    assert record.contact_name_source == "registre_ch"
