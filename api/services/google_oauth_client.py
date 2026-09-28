"""
The OAuth steps every Google integration shares: the consent page, the code exchange, the token refresh and the
connected account's profile.

The assistants' agendas, Gmail sending and Postmaster Tools share the server's Google OAuth client
(``GOOGLE_CLIENT_ID`` / ``GOOGLE_CLIENT_SECRET``); each keeps its own scopes, redirect address and errors.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, ClassVar
from urllib.parse import quote, urlencode

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GoogleTokens:
    """Tokens of a Google account; ``expires_at`` is naive UTC."""

    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scopes: frozenset[str]


class GoogleOAuthError(Exception):
    """A token or profile call Google refused or did not answer; ``error_code`` is Google's own (``invalid_grant``…)."""

    def __init__(self, message: str, *, status_code: int | None = None, error_code: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code

    @property
    def is_access_lost(self) -> bool:
        """Whether the account must consent again: its grant was revoked or has expired, or the client is refused."""
        return self.error_code in ("invalid_grant", "unauthorized_client")


class GoogleOAuthClient:
    """Google's OAuth endpoints, for any scope and redirect address."""

    AUTHORIZATION_URL: ClassVar[str] = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL: ClassVar[str] = "https://oauth2.googleapis.com/token"
    USERINFO_URL: ClassVar[str] = "https://www.googleapis.com/oauth2/v2/userinfo"

    @property
    def is_configured(self) -> bool:
        """Whether the Google OAuth client is configured on the server."""
        return bool(settings.google_client_id and settings.google_client_secret)

    @classmethod
    def authorization_url(
        cls, *, scopes: Iterable[str], redirect_uri: str, state: str | None, include_granted_scopes: bool = False
    ) -> str:
        """
        The Google consent page for an integration.

        Args:
            scopes: The accesses asked for.
            redirect_uri: Where Google sends the answer (declared in the Google console).
            state: What brings the answer back to its owner, when the integration uses one.
            include_granted_scopes: Keep the accesses the account already granted to this client.

        Returns:
            The URL to open in the browser (offline access, consent shown every time).
        """
        query: dict[str, str] = {
            "client_id": settings.google_client_id or "",
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
        }
        if include_granted_scopes:
            query["include_granted_scopes"] = "true"
        if state:
            query["state"] = state
        return f"{cls.AUTHORIZATION_URL}?{urlencode(query, quote_via=quote)}"

    async def exchange_code(self, code: str, *, redirect_uri: str, timeout_seconds: float) -> GoogleTokens:
        """
        Exchange a consent code for the account's tokens.

        Args:
            code: The ``code`` Google sent to the redirect address.
            redirect_uri: The redirect address the consent page named.
            timeout_seconds: HTTP timeout.

        Returns:
            The tokens and the scopes the account actually granted.

        Raises:
            GoogleOAuthError: When Google refuses the code or does not answer.
        """
        payload = await self._token_request(
            {
                "code": code,
                "client_id": settings.google_client_id or "",
                "client_secret": settings.google_client_secret or "",
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout_seconds=timeout_seconds,
        )
        return self._tokens(payload, refresh_token=payload.get("refresh_token"))

    async def refresh(self, refresh_token: str, *, timeout_seconds: float) -> GoogleTokens:
        """
        A fresh access token.

        Args:
            refresh_token: The stored refresh token.
            timeout_seconds: HTTP timeout.

        Returns:
            The new tokens (the refresh token is kept unless Google sends another one).

        Raises:
            GoogleOAuthError: When Google refuses the refresh (``is_access_lost``: consent again) or does not answer.
        """
        payload = await self._token_request(
            {
                "refresh_token": refresh_token,
                "client_id": settings.google_client_id or "",
                "client_secret": settings.google_client_secret or "",
                "grant_type": "refresh_token",
            },
            timeout_seconds=timeout_seconds,
        )
        return self._tokens(payload, refresh_token=payload.get("refresh_token") or refresh_token)

    async def user_info(self, access_token: str, *, timeout_seconds: float) -> dict[str, Any]:
        """
        The profile of the connected Google account.

        Args:
            access_token: A valid access token.
            timeout_seconds: HTTP timeout.

        Returns:
            Google's profile (``email``, ``verified_email``, ``name``…).

        Raises:
            GoogleOAuthError: When Google refuses the token or does not answer.
        """
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(self.USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("Google injoignable") from exc
        if response.status_code >= 400:
            logger.warning("Google profile refused (%s)", response.status_code)
            raise GoogleOAuthError(
                f"Google a refusé l'accès au profil ({response.status_code})", status_code=response.status_code
            )
        return self._json(response)

    async def _token_request(self, form: dict[str, str], *, timeout_seconds: float) -> dict[str, Any]:
        """POST to the token endpoint."""
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(self.TOKEN_URL, data=form)
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("Google injoignable") from exc
        if response.status_code >= 400:
            error = self._json(response).get("error")
            error_code = error if isinstance(error, str) else None
            logger.warning("Google token endpoint refused (%s): %s", response.status_code, error_code)
            raise GoogleOAuthError(
                f"Google a refusé l'accès ({error_code or response.status_code})",
                status_code=response.status_code,
                error_code=error_code,
            )
        return self._json(response)

    @staticmethod
    def _tokens(payload: dict[str, Any], *, refresh_token: str | None) -> GoogleTokens:
        """Tokens read from a token-endpoint answer."""
        access_token = payload.get("access_token")
        if not access_token:
            raise GoogleOAuthError("Réponse de Google sans jeton d'accès")
        expires_in = int(payload.get("expires_in") or 3600)
        return GoogleTokens(
            access_token=str(access_token),
            refresh_token=str(refresh_token) if refresh_token else None,
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=expires_in),
            scopes=frozenset(str(payload.get("scope") or "").split()),
        )

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any]:
        """A response's JSON object (empty when it has none)."""
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}


google_oauth_client = GoogleOAuthClient()
