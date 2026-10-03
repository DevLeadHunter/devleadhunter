"""The SIRET of a user's profile: kept as its 14 digits, cleared when emptied, refused when malformed."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from api.v1.routes.auth import update_current_user_info
from models.user import User
from schemas.user import UserUpdate


def _user(db: Session, *, siret: str | None = None) -> User:
    user = User(name="Alexis Durand", email="alexis@atelier-web.example", hashed_password="x", siret=siret)
    db.add(user)
    db.commit()
    return user


def test_a_siret_typed_with_spaces_is_stored_as_its_fourteen_digits(db: Session) -> None:
    user = _user(db)

    response = asyncio.run(update_current_user_info(UserUpdate(siret="988 307 906 00020"), user, db))

    assert user.siret == "98830790600020"
    assert response.siret == "98830790600020"


def test_an_emptied_siret_clears_the_profile_field(db: Session) -> None:
    user = _user(db, siret="98830790600020")

    asyncio.run(update_current_user_info(UserUpdate(siret=" "), user, db))

    assert user.siret is None


def test_a_profile_update_without_siret_keeps_it(db: Session) -> None:
    user = _user(db, siret="98830790600020")

    asyncio.run(update_current_user_info(UserUpdate(company_name="Atelier Web Durand"), user, db))

    assert user.siret == "98830790600020"


@pytest.mark.parametrize("typed", ["988 307 906", "98830790600020A", "9883079060002012"])
def test_a_siret_that_is_not_fourteen_digits_is_refused(typed: str) -> None:
    with pytest.raises(ValidationError):
        UserUpdate(siret=typed)
