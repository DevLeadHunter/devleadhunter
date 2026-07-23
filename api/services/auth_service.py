"""Authentication: password hashing, JWT tokens, and the FastAPI auth dependencies."""
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from core.config import settings
from core.database import get_db
from models.user import User
from schemas.user import TokenData
from enums.user_role import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


class AuthService:
    """Password hashing, JWT issuing and user lookup — everything the auth flow needs, HTTP aside."""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Check a plain password against its bcrypt hash.

        Args:
            plain_password: Password as typed by the user.
            hashed_password: Hash stored on the user row.

        Returns:
            Whether the password matches.
        """
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password with bcrypt, salt included.

        Args:
            password: Password as typed by the user.

        Returns:
            The hash to store on the user row.
        """
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Issue a signed JWT access token.

        Args:
            data: Claims to encode, `sub` carrying the user email.
            expires_delta: Lifetime override, defaulting to the configured one.

        Returns:
            The encoded token.
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """
        Look a user up by email.

        Args:
            db: Active database session.
            email: Email to match.

        Returns:
            The user, or None when no row matches.
        """
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """
        Look a user up by primary key.

        Args:
            db: Active database session.
            user_id: User identifier.

        Returns:
            The user, or None when no row matches.
        """
        return db.query(User).filter(User.id == user_id).first()

    @classmethod
    def authenticate_user(cls, db: Session, email: str, password: str) -> Optional[User]:
        """
        Authenticate a login attempt.

        Args:
            db: Active database session.
            email: Submitted email.
            password: Submitted password.

        Returns:
            The user when the credentials match an active account, None otherwise — the three
            failure causes are deliberately indistinguishable to the caller.
        """
        user = cls.get_user_by_email(db, email)
        if not user:
            return None
        if not cls.verify_password(password, user.hashed_password):
            return None
        if not user.is_active:
            return None
        return user

    @classmethod
    def resolve_user_from_token(cls, token: str, db: Session) -> User:
        """
        Resolve the user a raw JWT belongs to.

        Used by the HTTP dependency and by the WebSocket routes, which receive the token as a
        query parameter rather than through the `Authorization` header.

        Args:
            token: Raw JWT.
            db: Active database session.

        Returns:
            The authenticated user.

        Raises:
            HTTPException: 401 when the token is invalid, expired, or points at no user.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception
            token_data = TokenData(email=email)
        except JWTError:
            raise credentials_exception

        user = cls.get_user_by_email(db, email=token_data.email)
        if user is None:
            raise credentials_exception
        return user


# FastAPI resolves dependencies by inspecting plain callables, so these stay module-level and
# only delegate to AuthService. They are the auth contract the routes declare with Depends().


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Resolve the caller from the bearer token.

    Args:
        token: Bearer token extracted by the OAuth2 scheme.
        db: Active database session.

    Returns:
        The authenticated user.

    Raises:
        HTTPException: 401 when the token is invalid or points at no user.
    """
    return AuthService.resolve_user_from_token(token, db)


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Reject a caller whose account has been deactivated.

    Args:
        current_user: Caller resolved from the token.

    Returns:
        The caller.

    Raises:
        HTTPException: 400 when the account is inactive.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


def require_auth(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Guard a route behind authentication.

    Args:
        current_user: Caller resolved from the token.

    Returns:
        The caller.
    """
    return current_user


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Guard a route behind the admin role.

    Args:
        current_user: Caller resolved from the token.

    Returns:
        The caller.

    Raises:
        HTTPException: 403 when the caller is not an admin.
    """
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    return current_user
