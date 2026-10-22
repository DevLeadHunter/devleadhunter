"""Gmail Postmaster Tools v2 — per-user Gmail view of a sending domain via OAuth.

Each user connects the Google account that owns their sending domain(s) in
Postmaster Tools (https://postmaster.google.com). Domain verification (TXT DNS)
remains a one-time manual step on Google's side; OAuth only grants read access to
the traffic of domains already registered under that account. Google retired the
v1 API in October 2026: v2 no longer gives a domain reputation but a compliance
status (sender requirements and a deliverability verdict) and daily rates.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from core.config import settings
from models.user import User
from services.encryption_service import encryption_service
from services.postmaster_oauth_service import PostmasterOAuthService

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS: float = 21_600.0  # Postmaster data is daily — 6 h cache limits quota use.
_RETRY_DELAYS_SECONDS: tuple[float, ...] = (2.0, 5.0, 10.0)
_RETIRED_API_MARKER: str = "no longer supported"
_MISSING_SCOPE_MARKERS: tuple[str, ...] = (
    "insufficient authentication scopes",
    "access_token_scope_insufficient",
    "invalid_scope",
)
_NOT_REGISTERED_STATUSES: frozenset[int] = frozenset({403, 404})
_STATS_PAGE_SIZE: int = 200
_MAX_STATS_PAGES: int = 10
_DAILY_METRICS: tuple[tuple[str, str, str | None], ...] = (
    ("spam_ratio", "SPAM_RATE", None),
    ("spf_ratio", "AUTH_SUCCESS_RATE", 'auth_type = "spf"'),
    ("dkim_ratio", "AUTH_SUCCESS_RATE", 'auth_type = "dkim"'),
    ("dmarc_ratio", "AUTH_SUCCESS_RATE", 'auth_type = "dmarc"'),
    ("tls_ratio", "TLS_ENCRYPTION_RATE", 'traffic_direction = "inbound"'),
    ("delivery_error_ratio", "DELIVERY_ERROR_RATE", None),
)


class PostmasterService:
    """Read-only Postmaster v2 client scoped to one user's OAuth credentials."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
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
        """Fetch Gmail's compliance status and daily rates for a sending domain.

        Args:
            db: Database session (token refresh may persist here).
            user: Token owner.
            domain: Sending domain; the registered domain that covers it is the one read.
            days: History depth (Postmaster keeps ~120 days).

        Returns:
            Parsed status and rates, or an ``error`` key (with ``needs_reconnect``) when the fetch fails.
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
                "needs_reconnect": self._is_missing_scope(exc),
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
        """Read the compliance status and the daily rates of the registered domain that covers a sending domain.

        Args:
            db: Database session.
            user: Token owner.
            domain: Sending domain.
            days: History depth.

        Returns:
            The compliance summary, the daily rates and the domain Google answered for.

        Raises:
            Exception: When credentials are missing or the API call fails for another reason than an unknown domain.
        """
        credentials = self._ensure_credentials(db, user)
        client = build(
            "gmailpostmastertools", "v2", credentials=credentials, cache_discovery=False, static_discovery=False
        )
        candidates: list[str] = self.candidate_domains(domain)
        compliance_domain, compliance_payload = self._first_registered(
            candidates,
            lambda candidate: self._execute(
                client.domains().getComplianceStatus(name=f"domains/{candidate}/complianceStatus")
            ),
        )
        end: date = datetime.now(UTC).date()
        start: date = end - timedelta(days=days)
        stats_domain, stats_entries = self._first_registered(
            candidates, lambda candidate: self._query_daily_stats(client, candidate, start, end)
        )

        days_out: list[dict[str, Any]] = self._daily_rows(stats_entries or [])
        return {
            "domain": domain,
            "queried_domain": stats_domain or compliance_domain,
            "compliance": self._compliance_summary(compliance_payload) if compliance_payload is not None else None,
            "latest": days_out[-1] if days_out else None,
            "days": days_out,
            "no_data": not days_out,
            "domain_not_found": compliance_domain is None and stats_domain is None,
        }

    def _query_daily_stats(self, client: Any, domain: str, start: date, end: date) -> list[dict[str, Any]]:
        """Every daily statistic Google holds for a domain over a date range, page after page.

        Args:
            client: Gmail Postmaster Tools v2 client.
            domain: Registered domain to query.
            start: First day, inclusive.
            end: Last day, inclusive.

        Returns:
            The raw ``domainStats`` entries.

        Raises:
            HttpError: When Google refuses the query.
        """
        body: dict[str, Any] = {
            "metricDefinitions": [
                self._metric_definition(name, metric, metric_filter) for name, metric, metric_filter in _DAILY_METRICS
            ],
            "timeQuery": {"dateRanges": {"dateRanges": [{"start": self._api_date(start), "end": self._api_date(end)}]}},
            "aggregationGranularity": "DAILY",
            "pageSize": _STATS_PAGE_SIZE,
        }
        entries: list[dict[str, Any]] = []
        for _page in range(_MAX_STATS_PAGES):
            response = self._execute(client.domains().domainStats().query(parent=f"domains/{domain}", body=body))
            entries.extend(response.get("domainStats", []))
            next_page_token: str | None = response.get("nextPageToken")
            if not next_page_token:
                break
            body = {**body, "pageToken": next_page_token}
        return entries

    @staticmethod
    def candidate_domains(domain: str) -> list[str]:
        """The sending domain, then each parent domain above it (``mail.dibodev.fr`` then ``dibodev.fr``).

        Args:
            domain: Sending domain.

        Returns:
            The domains to try in Postmaster, most specific first; never a bare top-level domain.
        """
        labels: list[str] = domain.lower().strip(".").split(".")
        return [".".join(labels[index:]) for index in range(len(labels) - 1)]

    @classmethod
    def _first_registered(cls, candidates: list[str], fetch: Callable[[str], Any]) -> tuple[str | None, Any]:
        """The first candidate domain Google answers for, with its answer.

        Args:
            candidates: Domains to try, most specific first.
            fetch: The call to make for one domain.

        Returns:
            ``(domain, answer)``, or ``(None, None)`` when no candidate is registered for this account.

        Raises:
            HttpError: When Google refuses for another reason (missing scope, retired API, outage).
        """
        for candidate in candidates:
            try:
                return candidate, fetch(candidate)
            except HttpError as exc:
                if cls._is_missing_scope(exc) or exc.resp is None or exc.resp.status not in _NOT_REGISTERED_STATUSES:
                    raise
        return None, None

    @staticmethod
    def _metric_definition(name: str, metric: str, metric_filter: str | None) -> dict[str, Any]:
        """One metric to query, named after the field it fills in a day.

        Args:
            name: Key of the day row the value lands in.
            metric: Google's standard metric.
            metric_filter: Google's filter expression, or ``None``.

        Returns:
            The ``MetricDefinition`` payload.
        """
        definition: dict[str, Any] = {"name": name, "baseMetric": {"standardMetric": metric}}
        if metric_filter:
            definition["filter"] = metric_filter
        return definition

    @staticmethod
    def _api_date(day: date) -> dict[str, int]:
        """A calendar day in the shape of Google's ``Date`` message.

        Args:
            day: The day.

        Returns:
            Year, month and day.
        """
        return {"year": day.year, "month": day.month, "day": day.day}

    @classmethod
    def _daily_rows(cls, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Group Google's statistics into one row per day, oldest first.

        Args:
            entries: Raw ``domainStats`` entries.

        Returns:
            Rows carrying ``date`` and one share between 0 and 1 (or ``None``) per daily metric.
        """
        rows: dict[str, dict[str, Any]] = {}
        for entry in entries:
            day: dict[str, int] = entry.get("date") or {}
            if not day.get("year"):
                continue
            iso_date = f"{day['year']:04d}-{day.get('month', 0):02d}-{day.get('day', 0):02d}"
            row = rows.setdefault(iso_date, {"date": iso_date, **{name: None for name, _, _ in _DAILY_METRICS}})
            metric_name: str | None = entry.get("metric")
            if metric_name in row and metric_name != "date":
                row[metric_name] = cls._as_ratio(cls._statistic_number(entry.get("value")))
        return [rows[iso_date] for iso_date in sorted(rows)]

    @staticmethod
    def _statistic_number(value: dict[str, Any] | None) -> float | None:
        """The numeric part of Google's ``StatisticValue``.

        Args:
            value: The statistic value.

        Returns:
            The number, or ``None`` when the value holds none.
        """
        if not value:
            return None
        for key in ("doubleValue", "floatValue", "intValue"):
            if value.get(key) is not None:
                return float(value[key])
        return None

    @staticmethod
    def _as_ratio(value: float | None) -> float | None:
        """A rate as a share between 0 and 1; a value above 1 is read as a percentage.

        Args:
            value: The rate as Google gives it.

        Returns:
            The share, or ``None``.
        """
        if value is None:
            return None
        return value / 100 if value > 1 else value

    @staticmethod
    def _compliance_summary(payload: dict[str, Any]) -> dict[str, Any]:
        """Gmail's verdict and sender requirements for a domain, the subdomain's own data first.

        Args:
            payload: The ``DomainComplianceStatus`` answer.

        Returns:
            The domain judged, the deliverability verdict and its reason, and one status per requirement.
        """
        data: dict[str, Any] = payload.get("subdomainComplianceData") or payload.get("complianceData") or {}
        verdict: dict[str, Any] = data.get("deliverabilityStatusVerdict") or {}
        return {
            "domain": data.get("domainId"),
            "deliverability_status": (verdict.get("state") or {}).get("status"),
            "deliverability_reason": verdict.get("reason"),
            "requirements": [
                {"requirement": row["requirement"], "status": (row.get("status") or {}).get("status")}
                for row in data.get("rowData", [])
                if row.get("requirement")
            ],
        }

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

        The refresh asks for no scope: Google then renews exactly the access the user granted, and a token
        granted for an older scope fails on the call itself, where it reads as « reconnect », not on the refresh.

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
        if PostmasterService._is_missing_scope(exc):
            return (
                "Google demande une nouvelle autorisation pour la nouvelle version de Postmaster : "
                "cliquez sur « Reconnecter Google »."
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

    @staticmethod
    def _is_missing_scope(exc: Exception) -> bool:
        """Whether the stored Google access lacks the scope the current API needs (the user must reconnect).

        Args:
            exc: Raised exception.

        Returns:
            True when only a new consent can fix it.
        """
        lowered = str(exc).lower()
        return any(marker in lowered for marker in _MISSING_SCOPE_MARKERS)


postmaster_service = PostmasterService()
