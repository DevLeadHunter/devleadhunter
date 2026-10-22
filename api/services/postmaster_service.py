"""Gmail Postmaster Tools — per-user Gmail-side reputation via OAuth.

Each user connects the Google account that owns their sending domain(s) in
Postmaster Tools (https://postmaster.google.com). Domain verification (TXT DNS)
remains a one-time manual step on Google's side; OAuth only grants API read
access to domains already registered under that account.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from core.config import settings
from models.user import User
from services.encryption_service import encryption_service
from services.postmaster_oauth_service import POSTMASTER_SCOPE, PostmasterOAuthService

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS: float = 21_600.0  # Postmaster data is daily — 6 h cache limits quota use.
_DOMAINS_CACHE_TTL_SECONDS: float = 86_400.0  # Domain list changes rarely.
_RETRY_DELAYS_SECONDS: tuple[float, ...] = (2.0, 5.0, 10.0)
_RETIRED_API_MARKER: str = "no longer supported"


class PostmasterService:
    """Read-only Postmaster client scoped to one user's OAuth credentials."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._domains_cache: dict[int, tuple[float, set[str]]] = {}
        self._oauth = PostmasterOAuthService()

    def connection_status(self, user: User) -> dict[str, Any]:
        """Return whether the user has connected Postmaster OAuth.

        Args:
            user: Authenticated user.

        Returns:
            ``connected``, ``google_email`` and ``oauth_available`` flags.
        """
        has_token = bool(user.postmaster_oauth_refresh_token)
        return {
            "connected": has_token,
            "google_email": user.postmaster_google_email,
            "oauth_available": self._oauth.is_platform_configured,
        }

    def domain_stats(self, db: Session, user: User, domain: str, days: int = 30) -> dict[str, Any]:
        """Fetch Gmail reputation + spam-rate history for a domain.

        Args:
            db: Database session (token refresh may persist here).
            user: Token owner.
            domain: Sending domain (must exist in the user's Postmaster account).
            days: History depth (Postmaster keeps ~120 days).

        Returns:
            Parsed stats, or an ``error`` key when the fetch fails.
        """
        if not user.postmaster_oauth_refresh_token:
            return {"domain": domain, "error": None, "needs_connection": True}

        cache_key = f"{user.id}:{domain}:{days}"
        cached = self._cache.get(cache_key)
        if cached and (time.monotonic() - cached[0]) < _CACHE_TTL_SECONDS:
            return cached[1]

        try:
            result = self._fetch(db, user, domain, days)
        except Exception as exc:
            logger.warning("Postmaster fetch failed for user %s domain %s: %s", user.id, domain, exc)
            return {
                "domain": domain,
                "error": self._friendly_error(exc),
            }

        self._cache[cache_key] = (time.monotonic(), result)
        return result

    def clear_user_cache(self, user_id: int) -> None:
        """Drop cached Postmaster responses for one user.

        Args:
            user_id: Owner whose cache entries should be removed.
        """
        prefix = f"{user_id}:"
        for key in list(self._cache):
            if key.startswith(prefix):
                del self._cache[key]
        self._domains_cache.pop(user_id, None)

    def disconnect(self, db: Session, user: User) -> None:
        """Remove stored Postmaster OAuth tokens for a user.

        Args:
            db: Database session.
            user: Owner to disconnect.
        """
        user.postmaster_google_email = None
        user.postmaster_oauth_refresh_token = None
        user.postmaster_oauth_access_token = None
        user.postmaster_oauth_token_expires_at = None
        db.commit()
        self.clear_user_cache(user.id)

    def _fetch(self, db: Session, user: User, domain: str, days: int) -> dict[str, Any]:
        """Call the Postmaster API v1 traffic stats endpoint.

        Args:
            db: Database session.
            user: Token owner.
            domain: Verified domain name.
            days: History depth.

        Returns:
            Parsed daily stats.

        Raises:
            Exception: When credentials are missing or the API call fails.
        """
        credentials = self._ensure_credentials(db, user)
        client = build("gmailpostmastertools", "v1", credentials=credentials, cache_discovery=False)
        registered_domains = self._registered_domains(client, user.id)

        end = datetime.utcnow().date()
        start = end - timedelta(days=days)
        parent = f"domains/{domain}"
        try:
            response = self._execute(
                client.domains()
                .trafficStats()
                .list(
                    parent=parent,
                    startDate_year=start.year,
                    startDate_month=start.month,
                    startDate_day=start.day,
                    endDate_year=end.year,
                    endDate_month=end.month,
                    endDate_day=end.day,
                    pageSize=days,
                )
            )
        except HttpError as exc:
            if exc.resp is not None and exc.resp.status == 404:
                # 404 on trafficStats often means "no published metrics yet", not a missing domain.
                if domain.lower() in registered_domains:
                    return {
                        "domain": domain,
                        "latest": None,
                        "days": [],
                        "no_data": True,
                    }
                return {
                    "domain": domain,
                    "latest": None,
                    "days": [],
                    "no_data": True,
                    "domain_not_found": True,
                }
            raise

        days_out: list[dict[str, Any]] = []
        for stat in response.get("trafficStats", []):
            raw_date = stat.get("name", "").rsplit("/", 1)[-1]
            iso = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}" if len(raw_date) == 8 else raw_date
            days_out.append(
                {
                    "date": iso,
                    "domain_reputation": stat.get("domainReputation"),
                    "user_reported_spam_ratio": stat.get("userReportedSpamRatio"),
                    "spf_success_ratio": stat.get("spfSuccessRatio"),
                    "dkim_success_ratio": stat.get("dkimSuccessRatio"),
                    "dmarc_success_ratio": stat.get("dmarcSuccessRatio"),
                    "inbound_encryption_ratio": stat.get("inboundEncryptionRatio"),
                }
            )
        days_out.sort(key=lambda item: item["date"])

        latest = days_out[-1] if days_out else None
        return {
            "domain": domain,
            "latest": latest,
            "days": days_out,
            "no_data": not days_out,
        }

    def _registered_domains(self, client: Any, user_id: int) -> set[str]:
        """Return domain names registered in the user's Postmaster account.

        Args:
            client: Gmail Postmaster Tools API client.
            user_id: Owner (for cache key).

        Returns:
            Lower-cased FQDNs from ``domains.list``.
        """
        cached = self._domains_cache.get(user_id)
        if cached and (time.monotonic() - cached[0]) < _DOMAINS_CACHE_TTL_SECONDS:
            return cached[1]

        response = self._execute(client.domains().list(pageSize=100))
        names: set[str] = set()
        for item in response.get("domains", []):
            resource = item.get("name", "")
            if resource.startswith("domains/"):
                names.add(resource.removeprefix("domains/").lower())

        self._domains_cache[user_id] = (time.monotonic(), names)
        return names

    @staticmethod
    def _execute(request: Any) -> dict[str, Any]:
        """Execute a Postmaster API request with short retries on rate limits.

        Args:
            request: Google API request object.

        Returns:
            Parsed JSON response.

        Raises:
            HttpError: When the request fails after retries.
        """
        last_error: HttpError | None = None
        for attempt, delay in enumerate((0.0, *_RETRY_DELAYS_SECONDS)):
            if delay:
                time.sleep(delay)
            try:
                return request.execute()
            except HttpError as exc:
                last_error = exc
                if (
                    exc.resp is not None
                    and exc.resp.status == 429
                    and attempt < len(_RETRY_DELAYS_SECONDS)
                    and not PostmasterService._is_retired_api(exc)
                ):
                    logger.warning(
                        "Postmaster API rate-limited (429), retry %s/%s", attempt + 1, len(_RETRY_DELAYS_SECONDS)
                    )
                    continue
                raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("Postmaster API request failed without response")

    def _ensure_credentials(self, db: Session, user: User) -> Credentials:
        """Return valid Google credentials, refreshing and persisting when needed.

        Args:
            db: Database session.
            user: Token owner.

        Returns:
            OAuth credentials ready for API calls.

        Raises:
            ValueError: When no refresh token is stored.
        """
        refresh_token = user.postmaster_oauth_refresh_token
        if not refresh_token:
            raise ValueError("Postmaster not connected")

        decrypted_refresh = encryption_service.decrypt(refresh_token)
        access_token = (
            encryption_service.decrypt(user.postmaster_oauth_access_token)
            if user.postmaster_oauth_access_token
            else None
        )

        credentials = Credentials(
            token=access_token,
            refresh_token=decrypted_refresh,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=[POSTMASTER_SCOPE],
        )
        if user.postmaster_oauth_token_expires_at:
            credentials.expiry = user.postmaster_oauth_token_expires_at

        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            user.postmaster_oauth_access_token = encryption_service.encrypt(credentials.token or "")
            user.postmaster_oauth_token_expires_at = credentials.expiry
            db.commit()

        return credentials

    def store_tokens(
        self,
        db: Session,
        user: User,
        *,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime,
        google_email: str,
    ) -> None:
        """Persist OAuth tokens after a successful connect or reconnect.

        Args:
            db: Database session.
            user: Owner.
            access_token: Short-lived access token.
            refresh_token: Long-lived refresh token (may be omitted on re-consent).
            expires_at: Access token expiry.
            google_email: Connected Google account email.
        """
        user.postmaster_google_email = google_email
        user.postmaster_oauth_access_token = encryption_service.encrypt(access_token)
        if refresh_token:
            user.postmaster_oauth_refresh_token = encryption_service.encrypt(refresh_token)
        user.postmaster_oauth_token_expires_at = expires_at
        db.commit()
        self.clear_user_cache(user.id)

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        """Translate common API failures into actionable French messages.

        Args:
            exc: Raised exception.

        Returns:
            A short explanation for the UI.
        """
        text = str(exc)
        lowered = text.lower()
        if PostmasterService._is_retired_api(exc):
            return (
                "Google a retiré la version de l'API Postmaster que l'application utilise : "
                "la page doit passer à la nouvelle API de Google pour afficher la réputation du domaine."
            )
        if "invalid_grant" in lowered or ("token" in lowered and "revoked" in lowered):
            return "Session Google expirée — reconnectez Postmaster avec le bouton ci-dessous."
        if "403" in text or "permission" in lowered:
            return (
                "Accès refusé : connectez le compte Google qui possède ce domaine dans Postmaster Tools, "
                "ou vérifiez que le domaine y est bien enregistré."
            )
        if "404" in text:
            return (
                "Domaine introuvable dans Postmaster Tools — ajoutez-le et vérifiez-le sur postmaster.google.com "
                "avec le même compte Google que celui connecté ici."
            )
        if "429" in text or "resource_exhausted" in lowered or "quota" in lowered or "rate limit" in lowered:
            return "Quota Google Postmaster dépassé — réessayez dans quelques minutes."
        return "Erreur Postmaster temporaire — réessayez dans quelques minutes."

    @staticmethod
    def _is_retired_api(exc: Exception) -> bool:
        """Whether Google answered that this version of the Postmaster API is retired (a 429 that never clears).

        Args:
            exc: Raised exception.

        Returns:
            True when retrying cannot help.
        """
        return _RETIRED_API_MARKER in str(exc).lower()


postmaster_service = PostmasterService()
