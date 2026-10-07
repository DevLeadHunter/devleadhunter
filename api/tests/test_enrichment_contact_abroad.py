"""
The person behind a business outside France, read from the business's own public words: no French registry is
asked (it would only find a French homonym), so the name is a proposal waiting for a human, never trusted alone.
"""

import asyncio

import pytest
from sqlalchemy.orm import Session

from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from services.decision_maker.strategies import LlmAggregateStrategy, RegistreGouvStrategy
from services.enrichment_service import EnrichmentService


@pytest.fixture(autouse=True)
def no_network_strategies(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The LLM stays silent and any French registry call is recorded, never sent."""
    registry_calls: list[str] = []

    async def silent_llm(self: LlmAggregateStrategy, context: object) -> list[object]:
        return []

    async def recorded_registry(self: RegistreGouvStrategy, context: object) -> list[object]:
        registry_calls.append("registre_gouv")
        return []

    monkeypatch.setattr(LlmAggregateStrategy, "resolve", silent_llm)
    monkeypatch.setattr(RegistreGouvStrategy, "resolve", recorded_registry)
    return registry_calls


def _quebec_garage(db: Session) -> tuple[ProspectDB, ProspectEnrichment]:
    """A Quebec garage named after its owner, whose customers call him by his first name."""
    prospect = ProspectDB(
        name="Garage Jules Exemple",
        city="Victoriaville",
        country="CA",
        category="garage automobile",
        source="search",
        confidence=3,
        user_id=1,
    )
    db.add(prospect)
    db.commit()
    record = ProspectEnrichment(
        prospect_id=prospect.id,
        user_id=1,
        reviews=[{"author": "Une cliente", "text": "Depuis 10 ans je vais voir Jules pour ma voiture.", "rating": 5}],
    )
    db.add(record)
    db.commit()
    return prospect, record


def test_a_quebec_garage_gets_its_owner_proposed_from_its_reviews(
    db: Session, no_network_strategies: list[str]
) -> None:
    """« Garage Jules Exemple » and « je vais voir Jules »: Jules Exemple waits for a confirmation."""
    prospect, record = _quebec_garage(db)

    asyncio.run(EnrichmentService()._resolve_contact(db, prospect, record))

    assert (record.proposed_first_name, record.proposed_last_name, record.proposed_state) == (
        "Jules",
        "Exemple",
        "pending",
    )
    assert record.contact_first_name is None
    assert no_network_strategies == []
