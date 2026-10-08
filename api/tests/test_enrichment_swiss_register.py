"""
The federal register read at enrichment for a Swiss prospect (first enrichment round, 7 Oct 2026): a
landscaper struck off for ceasing trade two months earlier was a campaign lead, and no Swiss lead had
the name of the person running it.
"""

import asyncio
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace

import pytest

from services.enrichment_service import EnrichmentService
from services.prospect_search.swiss_registry import SwissRegisterFirm, swiss_registry

_PUBLICATION = (
    "Personne(s) inscrite(s): Exemple, Paul, de Haute-Ajoie, à Porrentruy, associé et gérant, avec signature "
    "individuelle, pour 20 parts sociales de CHF 1'000."
)


class _Session:
    """The database session the read commits on."""

    def commit(self) -> None:
        """Nothing to write: the record is a plain object."""


def _record() -> SimpleNamespace:
    """An enrichment whose contact nobody set yet."""
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
    return SimpleNamespace(contact_name_manual=False, place_postal_code=None, **dict.fromkeys(fields))


def _prospect() -> SimpleNamespace:
    """A Swiss landscaper of the campaign."""
    return SimpleNamespace(
        id=1,
        name="Exemple Paysages Sàrl",
        city="Porrentruy",
        address=None,
        country="CH",
        is_dismissed=False,
        user_id=7,
    )


def _firm(
    *, seat: str = "Porrentruy", status: str = "EXISTIEREND", struck_off_on: date | None = None
) -> SwissRegisterFirm:
    """The register's firm of the landscaper."""
    return SwissRegisterFirm(
        name="Exemple Paysages Sàrl",
        seat=seat,
        status=status,
        uid="CHE-111.222.333",
        struck_off_on=struck_off_on,
        register_id=1,
    )


@pytest.fixture
def register_firms(monkeypatch: pytest.MonkeyPatch) -> list[SwissRegisterFirm]:
    """The firms the register lists, scripted by each test, with one publication each."""
    firms: list[SwissRegisterFirm] = []

    async def firms_named(name: str, *, max_entries: int = 10) -> list[SwissRegisterFirm]:
        return list(firms)

    async def publications(firm: SwissRegisterFirm) -> list[tuple[date, str]]:
        return [(date(2024, 7, 30), _PUBLICATION)]

    monkeypatch.setattr(swiss_registry, "firms_named", firms_named)
    monkeypatch.setattr(swiss_registry, "publications", publications)
    return firms


def test_the_manager_of_an_active_firm_becomes_the_contact(register_firms: list[SwissRegisterFirm]) -> None:
    """The firm at the prospect's seat names its manager: a trusted contact."""
    register_firms.append(_firm())
    record = _record()

    asyncio.run(EnrichmentService()._read_swiss_register(_Session(), _prospect(), record, uid=None))

    assert (record.contact_first_name, record.contact_last_name, record.contact_name_source) == (
        "Paul",
        "Exemple",
        "registre_ch",
    )


def test_a_firm_found_away_from_its_seat_is_only_proposed(register_firms: list[SwissRegisterFirm]) -> None:
    """The only firm of that name sits in the commune, not the village: the name waits for a confirmation."""
    register_firms.append(_firm(seat="Haute-Ajoie"))
    record = _record()

    asyncio.run(EnrichmentService()._read_swiss_register(_Session(), _prospect(), record, uid=None))

    assert record.contact_first_name is None
    assert (record.proposed_first_name, record.proposed_last_name) == ("Paul", "Exemple")


def test_a_firm_struck_off_lately_is_set_aside_by_the_app(
    register_firms: list[SwissRegisterFirm], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recent striking-off sends the prospect to the « Écartés » tab with its reason, and names nobody."""
    register_firms.append(_firm(status="GELOESCHT", struck_off_on=datetime.now(UTC).date() - timedelta(days=90)))
    set_aside: list[tuple[int, str, int | None]] = []

    def dismiss(db: object, prospect_id: int, *, reason: str, dismissed_by_user_id: int | None) -> None:
        set_aside.append((prospect_id, reason, dismissed_by_user_id))

    from services.prospect_service import prospect_service

    monkeypatch.setattr(prospect_service, "dismiss", dismiss)
    record = _record()

    asyncio.run(EnrichmentService()._read_swiss_register(_Session(), _prospect(), record, uid=None))

    assert set_aside == [(1, "Entreprise radiée au registre du commerce (Zefix)", None)]
    assert record.contact_first_name is None and record.proposed_first_name is None


def test_a_firm_whose_address_is_in_the_business_town_is_the_business(
    register_firms: list[SwissRegisterFirm], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The firm's seat is the commune, its address the business's village: its manager is the trusted contact."""

    async def address_in_the_village(firm: SwissRegisterFirm) -> tuple[str, str]:
        return "2900", "Porrentruy"

    monkeypatch.setattr(swiss_registry, "address_of", address_in_the_village)
    register_firms.append(_firm(seat="Haute-Ajoie"))
    record = _record()

    asyncio.run(EnrichmentService()._read_swiss_register(_Session(), _prospect(), record, uid=None))

    assert (record.contact_first_name, record.proposed_first_name) == ("Paul", None)


def test_the_only_firm_of_the_name_in_another_region_names_nobody(
    register_firms: list[SwissRegisterFirm], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A garage of Gland (1196) is not the firm of the same name in Andelfingen (8452): no name, not even proposed."""

    async def address_far_away(firm: SwissRegisterFirm) -> tuple[str, str]:
        return "8452", "Adlikon b. Andelfingen"

    monkeypatch.setattr(swiss_registry, "address_of", address_far_away)
    register_firms.append(_firm(seat="Andelfingen"))
    prospect = _prospect()
    prospect.address = "Rue de l'Exemple 1, 1196 Gland"
    record = _record()

    asyncio.run(EnrichmentService()._read_swiss_register(_Session(), prospect, record, uid=None))

    assert (record.contact_first_name, record.proposed_first_name) == (None, None)


def test_a_firm_filed_under_another_name_at_the_business_address_names_its_head(
    register_firms: list[SwissRegisterFirm], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The register adds the owner's name (« Exemple Paysages Modèle »): found by its words at the address."""

    async def addresses_in_town(firm: SwissRegisterFirm) -> list[tuple[str, str]]:
        return [("2900", "Porrentruy")]

    monkeypatch.setattr(swiss_registry, "addresses_of", addresses_in_town)
    register_firms.append(
        SwissRegisterFirm(
            name="Exemple Paysages Modèle",
            seat="Haute-Ajoie",
            status="EXISTIEREND",
            uid="CHE-444.555.666",
            register_id=2,
        )
    )
    record = _record()

    asyncio.run(EnrichmentService()._read_swiss_register(_Session(), _prospect(), record, uid=None))

    assert (record.contact_first_name, record.proposed_first_name) == ("Paul", None)


def test_the_firm_of_a_number_now_trading_under_another_name_names_nobody(
    register_firms: list[SwissRegisterFirm],
) -> None:
    """The company number read by the search now belongs to a property company: its director is not the head."""
    register_firms.append(
        SwissRegisterFirm(
            name="Modèle Immobilier SA", seat="Porrentruy", status="EXISTIEREND", uid="CHE-111.222.333", register_id=1
        )
    )
    record = _record()

    asyncio.run(EnrichmentService()._read_swiss_register(_Session(), _prospect(), record, uid="CHE-111.222.333"))

    assert (record.contact_first_name, record.proposed_first_name) == (None, None)


def test_a_sole_proprietorship_without_publication_names_its_owner_in_its_name(
    register_firms: list[SwissRegisterFirm], monkeypatch: pytest.MonkeyPatch
) -> None:
    """« Exemple Paysages, Modèle Jules », registered before the gazette went online, names its owner."""

    async def no_publication(firm: SwissRegisterFirm) -> list[tuple[date, str]]:
        return []

    async def addresses_in_town(firm: SwissRegisterFirm) -> list[tuple[str, str]]:
        return [("2900", "Porrentruy")]

    monkeypatch.setattr(swiss_registry, "publications", no_publication)
    monkeypatch.setattr(swiss_registry, "addresses_of", addresses_in_town)
    register_firms.append(
        SwissRegisterFirm(
            name="Exemple Paysages, Modèle Jules",
            seat="Porrentruy",
            status="EXISTIEREND",
            uid="CHE-777.888.999",
            register_id=3,
            legal_form_id=1,
        )
    )
    record = _record()

    asyncio.run(EnrichmentService()._read_swiss_register(_Session(), _prospect(), record, uid=None))

    assert (record.contact_first_name, record.contact_last_name) == ("Jules", "Modèle")


def test_an_unsure_register_name_the_business_email_confirms_is_trusted(
    register_firms: list[SwissRegisterFirm], monkeypatch: pytest.MonkeyPatch
) -> None:
    """« de Modèle Jules Paul, titulaire » is unsure alone; the business writes from « demodele@… »: trusted."""

    async def older_publication(firm: SwissRegisterFirm) -> list[tuple[date, str]]:
        return [(date(2016, 3, 2), "Personne inscrite: de Modèle Jules Paul, de Exemple, à Porrentruy, titulaire.")]

    monkeypatch.setattr(swiss_registry, "publications", older_publication)
    register_firms.append(_firm())
    prospect = _prospect()
    prospect.email = "demodele@exemple.ch"
    prospect.emails = ["demodele@exemple.ch"]
    record = _record()
    record.reviews = []

    asyncio.run(EnrichmentService()._read_swiss_register(_Session(), prospect, record, uid=None))

    assert (record.contact_first_name, record.contact_last_name, record.proposed_first_name) == (
        "Jules",
        "De Modèle",
        None,
    )
