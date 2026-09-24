"""Unit tests for the « demande entrante » score of the Réceptionniste IA sourcing.

The score ranks prospects by how likely they receive more requests than they
answer. These tests pin each signal (trade, review volume, hours, chat) and the
batch scoring that reads enrichment rows, so a prospect list sorts the way the
operator expects.
"""

import importlib
import pkgutil

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import models
from core.database import Base
from models.prospect_db import ProspectDB
from models.prospect_enrichment import ProspectEnrichment
from scrappers.google_scraper import GoogleScraper
from services.inbound_demand_service import InboundDemandInputs, InboundDemandScorer, InboundDemandService

# Load every model so SQLAlchemy can configure the mappers (relationships resolve across models).
for _module in pkgutil.iter_modules(models.__path__):
    importlib.import_module("models." + _module.name)


def _inputs(**overrides: object) -> InboundDemandInputs:
    values: dict[str, object] = {
        "category": None,
        "reviews_count": None,
        "opening_hours": None,
        "has_working_website": True,
        "chat_providers": [],
    }
    values.update(overrides)
    return InboundDemandInputs(**values)  # type: ignore[arg-type]


def _points(inputs: InboundDemandInputs) -> dict[str, int]:
    return {signal.label: signal.points for signal in InboundDemandScorer.score(inputs).signals}


def test_a_busy_roofer_without_chat_scores_the_maximum() -> None:
    demand = InboundDemandScorer.score(
        _inputs(
            category="Couvreur",
            reviews_count=150,
            opening_hours=[
                {"day": "lundi", "hours": "07:00–19:30"},
                {"day": "samedi", "hours": "08:00–12:00"},
                {"day": "dimanche", "hours": "Ouvert 24h/24"},
            ],
        )
    )

    assert demand.score == 100
    assert [signal.label for signal in demand.signals] == [
        "Métier cible, vague 1 : couvreurs",
        "150 avis Google",
        "Ouvert le samedi",
        "Ouvert le dimanche",
        "Horaires tôt ou tard",
        "Aucun chat sur son site",
    ]


def test_target_vertical_outranks_another_quote_trade_which_outranks_the_rest() -> None:
    assert _points(_inputs(category="Atelier de carrosserie"))["Métier cible, vague 1 : carrosseries"] == 35
    assert _points(_inputs(category="Plombier chauffagiste"))["Métier à devis"] == 20
    assert "Métier à devis" not in _points(_inputs(category="Coiffeur"))


@pytest.mark.parametrize(("reviews", "points"), [(0, 0), (1, 5), (5, 14), (20, 23), (50, 30), (100, 35), (5000, 35)])
def test_review_volume_uses_a_capped_log_scale(reviews: int, points: int) -> None:
    label = "1 avis Google" if reviews == 1 else f"{reviews} avis Google"

    assert _points(_inputs(reviews_count=reviews))[label] == points


def test_unknown_review_count_is_shown_without_points() -> None:
    assert _points(_inputs(reviews_count=None))["Nombre d'avis Google inconnu"] == 0


def test_office_hours_and_closed_weekends_add_nothing() -> None:
    hours = [
        {"day": "lundi", "hours": "08:00–12:00, 14:00–18:00"},
        {"day": "samedi(Assomption)", "hours": "Fermé Les horaires peuvent être différents"},
        {"day": "dimanche", "hours": "Fermé"},
    ]

    labels = _points(_inputs(opening_hours=hours))

    assert "Ouvert le samedi" not in labels
    assert "Ouvert le dimanche" not in labels
    assert "Horaires tôt ou tard" not in labels


@pytest.mark.parametrize("hours", ["07:30–17:00", "09:00–19:00", "11:00–00:00", "9 h 00 – 20 h 30"])
def test_early_late_or_past_midnight_hours_count_as_extended(hours: str) -> None:
    assert _points(_inputs(opening_hours=[{"day": "mardi", "hours": hours}]))["Horaires tôt ou tard"] == 5


def test_malformed_hour_rows_are_ignored() -> None:
    demand = InboundDemandScorer.score(_inputs(opening_hours=["lundi 8-18", {"day": None, "hours": None}]))

    assert demand.score == 15


@pytest.mark.parametrize(
    ("has_working_website", "chat_providers", "label", "points"),
    [
        (False, None, "Pas de site : aucun chat en place", 15),
        (True, None, "Site pas encore analysé", 0),
        (True, ["tidio"], "Déjà équipé d'un chat", 0),
        (True, [], "Aucun chat sur son site", 15),
    ],
)
def test_chat_signal_depends_on_the_site_and_its_scan(
    has_working_website: bool, chat_providers: list[str] | None, label: str, points: int
) -> None:
    signals = _points(_inputs(has_working_website=has_working_website, chat_providers=chat_providers))

    assert signals[label] == points


@pytest.mark.parametrize(
    ("raw_rating", "raw_count", "expected"),
    [
        ("4.9", "132", (4.9, 132)),
        ("4,5", "1234", (4.5, 1234)),
        (None, None, (None, None)),
        ("", "", (None, None)),
        ("7.5", "abc", (None, None)),
    ],
)
def test_google_review_stats_are_parsed_defensively(
    raw_rating: str | None, raw_count: str | None, expected: tuple[float | None, int | None]
) -> None:
    assert GoogleScraper.parse_review_stats(raw_rating, raw_count) == expected


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _add_prospect(db: Session, **fields: object) -> ProspectDB:
    values: dict[str, object] = {"name": "Toitures Morel", "category": "Couvreur", "source": "google", "confidence": 2}
    values.update(fields)
    row = ProspectDB(user_id=1, **values)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_batch_scoring_prefers_enrichment_figures_over_discovery_ones(db: Session) -> None:
    enriched = _add_prospect(db, google_reviews_count=3, website=None)
    db.add(
        ProspectEnrichment(
            prospect_id=enriched.id,
            user_id=1,
            reviews_count=120,
            opening_hours=[{"day": "samedi", "hours": "08:00–12:00"}],
        )
    )
    discovered = _add_prospect(db, name="Charpente Martin", category="Charpentier", google_reviews_count=20)
    equipped = _add_prospect(
        db,
        name="Carrosserie Leroy",
        category="Carrosserie",
        website="https://leroy.fr",
        website_status="live",
        website_equipment_json={"chat_providers": ["tidio"], "has_contact_form": True},
    )
    db.commit()

    scores = InboundDemandService.score_prospects(db, [enriched, discovered, equipped])

    assert scores[enriched.id].score == 35 + 35 + 5 + 15
    assert scores[discovered.id].score == 35 + 23 + 15
    assert scores[equipped.id].score == 35
    assert InboundDemandService.score_prospects(db, []) == {}
