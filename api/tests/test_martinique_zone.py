"""A Martinique prospect stays French, but the map and the search show it in its own zone, as Québec has."""

from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from api.v1.routes.dashboard import coverage_zone_prospects, dashboard_coverage
from models.prospect_db import ProspectDB
from models.prospect_search_candidate import ProspectSearchCandidate
from models.user import User
from schemas.prospect_search import ProspectSearchCandidateResponse


def _owner(db: Session) -> User:
    owner = User(name="Camille Durand", email="camille@example.com", hashed_password="x")
    db.add(owner)
    db.commit()
    return owner


def _prospect(
    db: Session, owner: User, name: str, city: str, address: str | None = None, phone: str | None = None
) -> ProspectDB:
    prospect = ProspectDB(
        name=name,
        city=city,
        address=address,
        phone=phone,
        country="FR",
        category="Paysagiste",
        source="google",
        confidence=2,
        user_id=owner.id,
    )
    db.add(prospect)
    db.commit()
    return prospect


def _martinique_and_mainland(db: Session) -> User:
    owner = _owner(db)
    _prospect(db, owner, "Jardins du Diamant", "Le Diamant", address="Quartier Dizac, 97223 Le Diamant")
    _prospect(db, owner, "Paysages du Lamentin", "Le Lamentin", phone="0696 12 34 56")
    _prospect(db, owner, "Jardins du Tarn", "Albi", address="3 rue Croix-Verte, 81000 Albi")
    return owner


def test_a_prospect_is_placed_in_martinique_by_his_address_or_else_by_his_number(db: Session) -> None:
    owner = _owner(db)
    by_address = _prospect(db, owner, "Jardins du Diamant", "Le Diamant", address="Quartier Dizac, 97223 Le Diamant")
    by_number = _prospect(db, owner, "Paysages du Lamentin", "Le Lamentin", phone="0696 12 34 56")
    in_mainland = _prospect(db, owner, "Jardins du Tarn", "Albi", address="3 rue Croix-Verte, 81000 Albi")

    assert (by_address.region, by_number.region, in_mainland.region) == ("MQ", "MQ", None)


def test_a_prospect_whose_address_moves_to_the_mainland_leaves_martinique(db: Session) -> None:
    owner = _owner(db)
    prospect = _prospect(
        db,
        owner,
        "Paysages du Lamentin",
        "Le Lamentin",
        address="Place Mahault, 97232 Le Lamentin",
        phone="0696 12 34 56",
    )

    prospect.address = "12 rue de Brest, 35000 Rennes"
    db.commit()

    assert prospect.region is None


def test_the_coverage_map_counts_martinique_as_its_own_zone(db: Session) -> None:
    owner = _martinique_and_mainland(db)

    response = asyncio.run(dashboard_coverage(scope="me", member_id=None, categories=None, current_user=owner, db=db))

    assert {country.country: country.count for country in response.countries} == {"MQ": 2, "FR": 1}
    assert {city.city: city.country for city in response.cities} == {
        "Le Diamant": "MQ",
        "Le Lamentin": "MQ",
        "Albi": "FR",
    }


def test_the_martinique_zone_lists_its_prospects_and_the_mainland_zone_leaves_them_out(db: Session) -> None:
    owner = _martinique_and_mainland(db)

    def zone_names(zone: str) -> list[str]:
        response = asyncio.run(
            coverage_zone_prospects(
                cities=["Le Diamant", "Le Lamentin", "Albi"],
                country=zone,
                scope="me",
                member_id=None,
                categories=None,
                limit=300,
                current_user=owner,
                db=db,
            )
        )
        return sorted(row.name for row in response.items)

    assert zone_names("MQ") == ["Jardins du Diamant", "Paysages du Lamentin"]
    assert zone_names("FR") == ["Jardins du Tarn"]


def test_a_search_candidate_in_martinique_carries_its_zone(db: Session) -> None:
    candidate = ProspectSearchCandidate(
        search_id=1,
        user_id=1,
        trade="paysagiste",
        origin="google",
        name="Jardins du Diamant",
        address="Quartier Dizac, 97223 Le Diamant",
        country="FR",
    )
    db.add(candidate)
    db.commit()

    assert ProspectSearchCandidateResponse.model_validate(candidate).region == "MQ"
