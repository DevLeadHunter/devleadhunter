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
    return SimpleNamespace(contact_name_manual=False, **dict.fromkeys(fields))


def _prospect() -> SimpleNamespace:
    """A Swiss landscaper of the campaign."""
    return SimpleNamespace(
        id=1, name="Exemple Paysages Sàrl", city="Porrentruy", country="CH", is_dismissed=False, user_id=7
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

    async def firms_named(name: str) -> list[SwissRegisterFirm]:
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
