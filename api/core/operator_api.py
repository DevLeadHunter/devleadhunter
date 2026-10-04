"""
Operator API access — how the command-line tools talk to the DevLeadHunter API.

The tools run on the operator's own machine (a residential connection, a real Chrome)
and leave every read and write of the data to the API. This class owns the base URL and
the Bearer token, so no tool pastes a token by hand or rebuilds the login.

Environment:
    DLH_API_BASE   API base URL (default: https://api.devleadhunter.dibodev.fr).
    DLH_API_TOKEN  Bearer JWT of the operator's account. Optional: when unset, the tool logs
                   in with ADMIN_EMAIL / ADMIN_PASSWORD from the .env and mints a fresh token.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

from core.config import settings

_DEFAULT_API_BASE: str = "https://api.devleadhunter.dibodev.fr"
_API_PREFIX: str = "/api/v1"


class OperatorApi:
    """Authenticated calls to the API on behalf of the operator."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """
        Args:
            client: The HTTP client of the run (owns the timeout and the connection pool).
        """
        self._client = client
        self._access_token: str | None = None

    @property
    def base_url(self) -> str:
        """The API base URL, from ``DLH_API_BASE`` or the production default."""
        return (os.environ.get("DLH_API_BASE") or _DEFAULT_API_BASE).rstrip("/")

    async def authenticate(self) -> None:
        """
        Resolve the operator's Bearer token once, before any other call.

        Prefers ``DLH_API_TOKEN`` when set (handy to force another account while debugging);
        otherwise logs in with the operator credentials already present in the ``.env``.

        Raises:
            SystemExit: No credentials, a rejected login, or a login answer without a token.
        """
        env_token = (os.environ.get("DLH_API_TOKEN") or "").strip()
        if env_token:
            self._access_token = env_token
            return

        email = (settings.admin_email or "").strip()
        password = settings.admin_password or ""
        if not email or not password:
            raise SystemExit("No DLH_API_TOKEN and no ADMIN_EMAIL / ADMIN_PASSWORD in the .env — cannot authenticate.")

        response = await self._client.post(
            f"{self.base_url}{_API_PREFIX}/auth/login",
            json={"email": email, "password": password},
        )
        if response.status_code == 401:
            raise SystemExit(f"Login rejected for {email} — check ADMIN_PASSWORD in the .env.")
        response.raise_for_status()

        token = str(response.json().get("access_token") or "").strip()
        if not token:
            raise SystemExit("Login succeeded but the API returned no access_token.")
        self._access_token = token

    async def get(self, path: str) -> httpx.Response:
        """
        Send an authenticated GET.

        Args:
            path: Route path under the API prefix (« /prospects »).

        Returns:
            The response, whatever its status (the caller decides what a 404 means).
        """
        return await self._client.get(f"{self.base_url}{_API_PREFIX}{path}", headers=self._auth_headers())

    async def post(self, path: str, *, json: Any = None) -> httpx.Response:
        """
        Send an authenticated POST.

        Args:
            path: Route path under the API prefix.
            json: Body, serialised as JSON.

        Returns:
            The response, whatever its status.
        """
        return await self._client.post(f"{self.base_url}{_API_PREFIX}{path}", headers=self._auth_headers(), json=json)

    def _auth_headers(self) -> dict[str, str]:
        """The Bearer header resolved by :meth:`authenticate`."""
        if not self._access_token:
            raise SystemExit("Not authenticated — authenticate() must run before any API call.")
        return {"Authorization": f"Bearer {self._access_token}"}
