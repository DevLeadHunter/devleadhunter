"""``GET /dashboard/coverage/prospects``: a map zone lists its own country's prospects, never a foreign homonym's."""

from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from api.v1.routes.dashboard import coverage_zone_prospects
from models.prospect_db import ProspectDB
from models.user import User


def _owner(db: Session) -> User:
    owner = User(name="Camille Durand", email="camille@example.com", hashed_password="x")
    db.add(owner)
    db.commit()
    return owner


def _prospect(db: Session, owner: User, name: str, city: str, country: str) -> None:
    db.add(
        ProspectDB(
            name=name,
            city=city,
            country=country,
            category="Paysagiste",
            source="google",
            confidence=2,
            user_id=owner.id,
        )
    )
    db.commit()


def _zone_names(db: Session, owner: User, country: str | None) -> list[str]:
    response = asyncio.run(
        coverage_zone_prospects(
            cities=["Laval"],
            country=country,
            scope="me",
            member_id=None,
            categories=None,
            limit=300,
            current_user=owner,
            db=db,
        )
    )
    return [row.name for row in response.items]


def _two_lavals(db: Session) -> User:
    owner = _owner(db)
    _prospect(db, owner, "Jardins de la Mayenne", "Laval", "FR")
    _prospect(db, owner, "Paysages d'avant la colonne pays", "Laval", "")
    _prospect(db, owner, "Paysagement Rive-Nord", "Laval", "CA")
    return owner


def test_a_quebec_zone_leaves_the_french_laval_out(db: Session) -> None:
    owner = _two_lavals(db)
    assert _zone_names(db, owner, "CA") == ["Paysagement Rive-Nord"]


def test_a_french_zone_counts_the_rows_saved_before_the_country_existed(db: Session) -> None:
    owner = _two_lavals(db)
    assert _zone_names(db, owner, "fr") == ["Jardins de la Mayenne", "Paysages d'avant la colonne pays"]


def test_a_zone_without_country_keeps_every_homonym(db: Session) -> None:
    owner = _two_lavals(db)
    assert len(_zone_names(db, owner, None)) == 3
