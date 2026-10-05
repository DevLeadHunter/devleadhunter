"""
Tests for the access token renewal — an app left open stays signed in while it is used.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from api.v1.routes.auth import router as auth_router
from core.config import settings
from core.database import get_db
from models.user import User
from services.auth_service import AuthService

EMAIL = "operateur@dibodev.fr"


def _client(db: Session) -> TestClient:
    """The auth routes on the test database, with the token checks left as they are."""
    application = FastAPI()
    application.include_router(auth_router)
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def _expiry_of(token: str) -> datetime:
    """When a token stops being accepted."""
    claims = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    return datetime.fromtimestamp(claims["exp"], UTC)


def _add_user(db: Session, *, is_active: bool = True) -> None:
    """The signed-in user, as the token's subject finds them in the database."""
    db.add(User(id=7, name="Dibodev", email=EMAIL, hashed_password="x", is_active=is_active))
    db.commit()


def test_a_token_close_to_its_end_is_traded_for_one_with_the_full_lifetime(db: Session) -> None:
    _add_user(db)
    aging_token = AuthService.create_access_token(data={"sub": EMAIL}, expires_delta=timedelta(hours=1))

    response = _client(db).post("/auth/refresh", headers={"Authorization": f"Bearer {aging_token}"})

    assert response.status_code == 200
    renewed_token = response.json()["access_token"]
    assert jwt.decode(renewed_token, settings.secret_key, algorithms=[settings.algorithm])["sub"] == EMAIL
    full_lifetime_end = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    assert abs(_expiry_of(renewed_token) - full_lifetime_end) < timedelta(minutes=1)


def test_an_expired_token_is_not_renewed(db: Session) -> None:
    _add_user(db)
    expired_token = AuthService.create_access_token(data={"sub": EMAIL}, expires_delta=timedelta(seconds=-1))

    response = _client(db).post("/auth/refresh", headers={"Authorization": f"Bearer {expired_token}"})

    assert response.status_code == 401


def test_a_deactivated_account_cannot_renew_its_token(db: Session) -> None:
    _add_user(db, is_active=False)
    token = AuthService.create_access_token(data={"sub": EMAIL})

    response = _client(db).post("/auth/refresh", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 400
