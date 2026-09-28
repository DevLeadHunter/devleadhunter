"""Google OAuth for Gmail Postmaster Tools (per-user, read-only).

Separate from Gmail sending OAuth: different scope, callback and stored tokens. The consent, the tokens and the
profile go through the shared Google OAuth client.
"""

from __future__ import annotations

from typing import Any, ClassVar

from core.config import settings
from services.google_oauth_client import google_oauth_client

# v1 REST API (`gmailpostmastertools.googleapis.com/v1`) only accepts this scope.
# `postmaster.traffic.readonly` is for the newer v2 client — using it yields 403 on v1.
POSTMASTER_SCOPE: str = "https://www.googleapis.com/auth/postmaster.readonly"
USERINFO_EMAIL_SCOPE: str = "https://www.googleapis.com/auth/userinfo.email"


class PostmasterOAuthService:
    """OAuth2 helper for the Postmaster Tools API."""

    SCOPES: ClassVar[tuple[str, ...]] = ("openid", USERINFO_EMAIL_SCOPE, POSTMASTER_SCOPE)
    TIMEOUT_SECONDS: ClassVar[float] = 30.0

    @property
    def is_platform_configured(self) -> bool:
        """Whether the Google OAuth client is configured on the server.

        Returns:
            True when client id and secret are set.
        """
        return google_oauth_client.is_configured

    def get_authorization_url(self, state: str) -> str:
        """Build the Google consent URL for Postmaster read access.

        Args:
            state: CSRF token (``postmaster_user_<id>``).

        Returns:
            URL to redirect the browser to.
        """
        return google_oauth_client.authorization_url(
            scopes=self.SCOPES, redirect_uri=settings.google_postmaster_redirect_uri, state=state
        )

    async def exchange_code_for_tokens(self, code: str) -> dict[str, Any]:
        """Exchange an authorization code for access and refresh tokens.

        Args:
            code: Authorization code from Google.

        Returns:
            Dict with access_token, optional refresh_token and expires_at.

        Raises:
            GoogleOAuthError: When the token exchange fails.
        """
        tokens = await google_oauth_client.exchange_code(
            code, redirect_uri=settings.google_postmaster_redirect_uri, timeout_seconds=self.TIMEOUT_SECONDS
        )
        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at,
        }

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh an expired access token.

        Args:
            refresh_token: Stored refresh token.

        Returns:
            Dict with access_token and expires_at.

        Raises:
            GoogleOAuthError: When refresh fails (token revoked, app in testing mode, etc.).
        """
        tokens = await google_oauth_client.refresh(refresh_token, timeout_seconds=self.TIMEOUT_SECONDS)
        return {"access_token": tokens.access_token, "expires_at": tokens.expires_at}

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Fetch the Google account profile for the connected user.

        Args:
            access_token: Valid access token.

        Returns:
            Google userinfo payload (email, verified_email, name, …).

        Raises:
            GoogleOAuthError: When Google refuses the token.
        """
        return await google_oauth_client.user_info(access_token, timeout_seconds=self.TIMEOUT_SECONDS)
