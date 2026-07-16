"""Gmail Postmaster Tools — the authoritative Gmail-side reputation feed.

Free Google API. Setup (one-time, manual):
1. https://postmaster.google.com → add + verify the sending domain (TXT DNS).
2. Google Cloud console → enable the "Postmaster Tools API" → create a
   service account → download its JSON key.
3. In Postmaster Tools → domain → "Manage users" → add the service-account
   email address (…@…iam.gserviceaccount.com) — read access is enough.
4. Point the service at the key, either way:
   - Local dev: ``GOOGLE_POSTMASTER_CREDENTIALS_FILE`` = path to the JSON key.
   - Production: ``GOOGLE_POSTMASTER_CREDENTIALS_JSON`` = the key inline (raw JSON
     or base64 of it), shipped as a single env secret — no file to write on the
     server. When both are set, the inline JSON wins.

When neither is configured the service reports ``configured: False`` and the
UI shows the setup card instead of data.
"""
from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from core.config import settings

logger = logging.getLogger(__name__)

_SCOPE: str = "https://www.googleapis.com/auth/postmaster.readonly"
_CACHE_TTL_SECONDS: float = 3600.0  # Postmaster data is daily — 1 h cache is plenty.


class PostmasterService:
    """Read-only client for the Gmail Postmaster Tools API (cached)."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    @property
    def credentials_file(self) -> Optional[str]:
        """Path to the service-account JSON key file (None = not set/found).

        A relative path is resolved against the ``api/`` root, so a value like
        ``credentials/google-postmaster.json`` works regardless of the current
        working directory the server was launched from.

        @returns The absolute path when the file exists on disk.
        """
        path = settings.google_postmaster_credentials_file
        if not path:
            return None
        if not os.path.isabs(path):
            api_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(api_root, path)
        if os.path.isfile(path):
            return path
        return None

    @property
    def is_configured(self) -> bool:
        """Whether credentials are available via inline JSON or a key file.

        @returns True when the service can authenticate against the API.
        """
        return bool(settings.google_postmaster_credentials_json) or self.credentials_file is not None

    def _service_account_info(self) -> Optional[dict[str, Any]]:
        """Parse the inline service-account JSON (raw or base64), when set.

        Accepts the key file's contents pasted directly, or a base64 encoding of
        it (the deploy-safe form: a single line, no quotes/newlines to escape
        through the CI heredoc → ``.env`` → dotenv chain).

        @returns The parsed credentials dict, or None when no inline JSON is set.
        @raises ValueError - When the inline value is set but cannot be decoded.
        """
        raw = settings.google_postmaster_credentials_json
        if not raw:
            return None
        text = raw.strip()
        if not text.startswith("{"):
            try:
                text = base64.b64decode(text, validate=True).decode("utf-8")
            except (binascii.Error, ValueError) as exc:
                raise ValueError("GOOGLE_POSTMASTER_CREDENTIALS_JSON is neither JSON nor valid base64") from exc
        return json.loads(text)

    def domain_stats(self, domain: str, days: int = 30) -> dict[str, Any]:
        """Fetch Gmail reputation + spam-rate history for a domain.

        @param domain - The sending domain (must be verified in Postmaster Tools).
        @param days - History depth (Postmaster keeps ~120 days).
        @returns ``configured`` flag, then reputation/spam series when available.
        """
        if not self.is_configured:
            return {"configured": False, "domain": domain, "reason": "missing_credentials"}

        cache_key = f"{domain}:{days}"
        cached = self._cache.get(cache_key)
        if cached and (time.monotonic() - cached[0]) < _CACHE_TTL_SECONDS:
            return cached[1]

        try:
            result = self._fetch(domain, days)
        except Exception as exc:  # noqa: BLE001 — surfaced as a friendly error, never a 500
            logger.warning("Postmaster fetch failed for %s: %s", domain, exc)
            result = {
                "configured": True,
                "domain": domain,
                "error": self._friendly_error(exc),
            }
        self._cache[cache_key] = (time.monotonic(), result)
        return result

    def _fetch(self, domain: str, days: int) -> dict[str, Any]:
        """Call the API (import here so the app boots without the lib configured).

        @param domain - Verified domain.
        @param days - History depth.
        @returns Parsed daily stats.
        """
        from google.oauth2 import service_account  # local import: optional feature
        from googleapiclient.discovery import build

        info = self._service_account_info()
        if info is not None:
            credentials = service_account.Credentials.from_service_account_info(info, scopes=[_SCOPE])
        else:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file, scopes=[_SCOPE]
            )
        client = build("gmailpostmastertools", "v1", credentials=credentials, cache_discovery=False)

        start = datetime.utcnow().date() - timedelta(days=days)
        parent = f"domains/{domain}"
        response = (
            client.domains()
            .trafficStats()
            .list(
                parent=parent,
                startDate_year=start.year,
                startDate_month=start.month,
                startDate_day=start.day,
                pageSize=days,
            )
            .execute()
        )

        days_out: list[dict[str, Any]] = []
        for stat in response.get("trafficStats", []):
            # name = domains/<domain>/trafficStats/YYYYMMDD
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
            "configured": True,
            "domain": domain,
            "latest": latest,
            "days": days_out,
        }

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        """Translate common API failures into actionable French messages.

        @param exc - Raised exception.
        @returns A short explanation for the UI.
        """
        text = str(exc)
        if "403" in text or "permission" in text.lower():
            return (
                "Accès refusé : ajoutez l'email du service account comme utilisateur du domaine "
                "dans Postmaster Tools (Manage users)."
            )
        if "404" in text:
            return "Domaine introuvable dans Postmaster Tools — vérifiez-le d'abord sur postmaster.google.com."
        return f"Erreur Postmaster : {text[:200]}"


postmaster_service = PostmasterService()
