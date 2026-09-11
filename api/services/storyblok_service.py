"""
Storyblok Management API integration for demo site provisioning.

When STORYBLOK_MANAGEMENT_TOKEN is not configured, runs in mock mode and stores
content locally in the database (demo-host renders from content_json).
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import logging
import random
import re
import secrets
import string
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from core.config import settings
from services.enrichment_content import EnrichmentContentMapper
from services.templates import registry as template_registry
from services.templates.default_images import apply_default_images
from services.templates.site_content import SECTION_COMPONENT_NAMES, SITE_CONTENT_SCHEMAS, apply_section_overrides

logger = logging.getLogger(__name__)


@dataclass
class StoryblokProvisionResult:
    """Result of Storyblok space provisioning."""

    space_id: int | None
    public_token: str | None
    preview_token: str | None
    editor_url: str | None
    login_email: str | None
    login_password: str | None
    invite_sent: bool
    content_json: dict[str, Any]
    mock_mode: bool


class StoryblokProvisionError(Exception):
    """Raised when Storyblok provisioning fails after the space was created."""

    def __init__(
        self,
        message: str,
        *,
        space_id: int | None = None,
        editor_url: str | None = None,
        content_json: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.space_id = space_id
        self.editor_url = editor_url
        self.content_json = content_json


_DATA_URI_RE = re.compile(r"^data:(?P<mime>[\w/\-.+]+)?;base64,(?P<data>.+)$", re.DOTALL)


def _decode_data_uri(uri: str) -> tuple[bytes | None, str]:
    """Decode a base64 ``data:`` image URI into ``(bytes, content-type)``, or ``(None, "")`` if malformed."""
    match = _DATA_URI_RE.match(uri)
    if not match:
        return None, ""
    try:
        content = base64.b64decode(match.group("data"), validate=False)
    except (ValueError, binascii.Error):
        return None, ""
    return content, (match.group("mime") or "image/jpeg")


class StoryblokService:
    """Creates and tears down Storyblok spaces for demo websites."""

    def __init__(self) -> None:
        self._token: str | None = settings.storyblok_management_token
        self._region: str = settings.storyblok_region
        self._base_url: str = "https://mapi.storyblok.com/v1"
        # The Management API caps at ~6 req/s. The sectioned schema registers ~19 components (plus the
        # per-image asset uploads), so we pace request STARTS below that to avoid a fatal 429.
        self._rate_lock: asyncio.Lock = asyncio.Lock()
        self._min_request_interval: float = 0.18
        self._next_request_at: float = 0.0

    @property
    def is_configured(self) -> bool:
        """Return True when a Management API token is available."""
        return bool(self._token and self._token.strip())

    @property
    def cdn_base_url(self) -> str:
        """Return the Storyblok CDN API base URL for the configured region."""
        region_urls: dict[str, str] = {
            "eu": "https://api.storyblok.com",
            "us": "https://api-us.storyblok.com",
            "ap": "https://api-ap.storyblok.com",
            "ca": "https://api-ca.storyblok.com",
            "cn": "https://api-cn.storyblok.com",
        }
        return region_urls.get(self._region, region_urls["eu"])

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._token or "",
            "Content-Type": "application/json",
        }

    def build_content_json(
        self,
        *,
        business_name: str,
        phone: str | None,
        email: str | None,
        city: str | None,
        description: str | None,
        template_id: str,
        theme: dict[str, str] | None = None,
        enrichment: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Build the default Storyblok story payload for a template.

        Args:
            business_name: Client business display name.
            phone: Contact phone number.
            email: Contact email address.
            city: Service area / city.
            description: Short business description.
            template_id: Selected template identifier.
            theme: Optional color palette (primary, secondary, accent).
            enrichment: Optional rich data merged into the content (photos, reviews…).

        Returns:
            Storyblok-compatible content object.
        """
        area: str = city or "votre secteur"
        subtitle: str = description or template_registry.default_subtitle(template_id, area)
        # No explicit theme → use the template's own signature palette (Lumen yellow,
        # Cuivre water-blue…) instead of a generic fallback, so generated demos keep their DA.
        palette: dict[str, str] = theme or template_registry.default_theme(template_id)

        # Phase 4b — templates that opt in produce a FLAT SiteContent that already
        # consumes enrichment; the rich enrichment merge must not run for them.
        if template_registry.uses_site_content(template_id):
            site_content = template_registry.build_site_content(
                template_id=template_id,
                business_name=business_name,
                phone=phone,
                email=email,
                city=city,
                area=area,
                subtitle=subtitle,
                palette=palette,
                enrichment=enrichment,
            )
            # Seed empty image slots with the template's own default images so they reach Storyblok
            # (uploaded as real, editable assets) — not just the render-time layer fallback.
            apply_default_images(site_content, template_id)
            return site_content

        content = template_registry.build_content(
            template_id=template_id,
            business_name=business_name,
            phone=phone,
            email=email,
            city=city,
            area=area,
            subtitle=subtitle,
            palette=palette,
        )
        return EnrichmentContentMapper.apply_to_content(content, enrichment)

    @staticmethod
    def _is_flat_site_content(content_json: dict[str, Any]) -> bool:
        """Detect the flat ``SiteContent`` shape (Phase 4b) vs the rich body-based content.

        Flat SiteContent has no ``body`` list and carries a ``businessName`` key.
        """
        return "body" not in content_json and "businessName" in content_json

    def _to_storyblok_content(self, content_json: dict[str, Any], template_id: str | None = None) -> dict[str, Any]:
        """Adapt local demo content to Storyblok blok schemas.

        Rich content (``{theme, body:[...]}``) is wrapped as a ``page`` with its
        body bloks. Flat ``SiteContent`` (Phase 4b) is expressed as a native
        ``site_content`` blok (via the template) and dropped into the page body,
        so the Visual Editor can edit every field.
        """
        theme_raw = content_json.get("theme")
        # Flat SiteContent keeps the palette under ``palette`` (theme lives inside it).
        if theme_raw is None and isinstance(content_json.get("palette"), dict):
            theme_raw = content_json.get("palette")
        theme_block: dict[str, Any] = {
            "_uid": "theme-1",
            "component": "theme_palette",
            "primary": "#0284c7",
            "secondary": "#0f172a",
            "accent": "#f59e0b",
        }
        if isinstance(theme_raw, dict):
            theme_block.update(
                {
                    "primary": str(theme_raw.get("primary") or theme_block["primary"]),
                    "secondary": str(theme_raw.get("secondary") or theme_block["secondary"]),
                    "accent": str(theme_raw.get("accent") or theme_block["accent"]),
                }
            )

        if (
            self._is_flat_site_content(content_json)
            and template_id
            and template_registry.uses_site_content(template_id)
        ):
            section_bloks = template_registry.to_storyblok_site_content(template_id, content_json)
            return {
                "component": "page",
                "theme": [theme_block],
                "body": section_bloks,
            }

        return {
            "component": "page",
            "theme": [theme_block],
            "body": content_json.get("body", []),
        }

    async def _storyblok_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        retries: int = 6,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform a Storyblok request, paced under the rate limit and retrying on 429.

        Request STARTS are spaced by ``_min_request_interval`` (shared across concurrent calls) to stay
        below the ~6 req/s cap; a 429 is still retried, honouring ``Retry-After`` then exponential backoff.
        """
        last_response: httpx.Response | None = None

        for attempt in range(retries):
            async with self._rate_lock:
                wait: float = self._next_request_at - time.monotonic()
                if wait > 0:
                    await asyncio.sleep(wait)
                self._next_request_at = time.monotonic() + self._min_request_interval

            response = await client.request(method, url, headers=self._headers(), **kwargs)
            last_response = response
            if response.status_code != 429:
                return response

            retry_after: str | None = response.headers.get("Retry-After")
            try:
                backoff: float = float(retry_after) if retry_after else min(2.0**attempt, 8.0)
            except ValueError:
                backoff = min(2.0**attempt, 8.0)
            await asyncio.sleep(backoff + random.uniform(0.0, 0.3))

        assert last_response is not None
        return last_response

    async def _delete_home_story(
        self,
        client: httpx.AsyncClient,
        space_id: int,
        story_id: int,
    ) -> None:
        """Remove the default Storyblok home story before seeding template content."""
        response = await self._storyblok_request(
            client,
            "DELETE",
            f"{self._base_url}/spaces/{space_id}/stories/{story_id}",
        )
        if response.status_code not in (200, 204, 404):
            response.raise_for_status()

    def _storyblok_error_message(self, exc: httpx.HTTPStatusError) -> str:
        """Build a readable Storyblok API error for API responses."""
        detail: str = exc.response.text.strip()
        if detail:
            return f"Storyblok API error ({exc.response.status_code}): {detail}"
        return f"Storyblok API error ({exc.response.status_code}) for {exc.request.method} {exc.request.url}"

    async def get_home_story_id(self, space_id: int) -> int | None:
        """Public: resolve a space's home story id (used to open its Visual Editor).

        Returns ``None`` when Storyblok is unconfigured (mock mode) or the story is
        missing.
        """
        if not self.is_configured:
            return None
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await self._find_home_story_id(client, space_id)

    async def _find_home_story_id(
        self,
        client: httpx.AsyncClient,
        space_id: int,
    ) -> int | None:
        """Return the Storyblok story id for slug ``home`` when it already exists."""
        list_resp = await client.get(
            f"{self._base_url}/spaces/{space_id}/stories/",
            headers=self._headers(),
            params={"with_slug": "home"},
        )
        try:
            list_resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(self._storyblok_error_message(exc)) from exc

        stories: list[dict[str, Any]] = list_resp.json().get("stories", [])
        if not stories:
            return None
        return int(stories[0]["id"])

    async def _upload_asset(
        self, client: httpx.AsyncClient, space_id: int, source_url: str, key: str
    ) -> dict[str, Any] | None:
        """Upload one external image into the space's asset library (sign → S3 → finish).

        The stored filename is ``{key}.{ext}`` — a deterministic digest of the source URL — so the same
        photo re-uploaded later is recognisable in the library and never duplicated (see
        ``_upload_external_assets``). Returns ``{id, filename}`` (the real Storyblok CDN asset) or None
        on any failure, so the caller can fall back to the external URL.
        """
        try:
            if source_url.startswith("data:"):
                # A base64 data URI: the desktop scraper captured the bytes in-browser (e.g. Facebook
                # photos the VPS can't fetch). Decode instead of downloading.
                content, content_type = _decode_data_uri(source_url)
                if not content:
                    return None
            else:
                image = await client.get(source_url, follow_redirects=True, timeout=30.0)
                if image.status_code != 200 or not image.content:
                    return None
                content = image.content
                content_type = image.headers.get("content-type", "image/jpeg").split(";")[0].strip()
            extension: str = {"image/png": "png", "image/webp": "webp", "image/gif": "gif"}.get(content_type, "jpg")
            filename: str = f"{key}.{extension}"
            sign = await self._storyblok_request(
                client, "POST", f"{self._base_url}/spaces/{space_id}/assets/", json={"filename": filename}
            )
            if sign.status_code not in (200, 201):
                return None
            signed: dict[str, Any] = sign.json()
            asset_id: int = int(signed["id"])
            upload = await client.post(
                signed["post_url"],
                data=signed.get("fields", {}),
                files={"file": (filename, content, content_type)},
                timeout=60.0,
            )
            if upload.status_code not in (200, 201, 204):
                return None
            finish = await self._storyblok_request(
                client, "GET", f"{self._base_url}/spaces/{space_id}/assets/{asset_id}/finish_upload"
            )
            filename_url: Any = finish.json().get("filename") if finish.status_code == 200 else None
            if not isinstance(filename_url, str) or not filename_url:
                return None
            return {"id": asset_id, "filename": filename_url}
        except (httpx.HTTPError, ValueError, KeyError):
            return None

    async def _upload_external_assets(
        self,
        client: httpx.AsyncClient,
        space_id: int,
        content: dict[str, Any],
        *,
        rehost_all_assets: bool = False,
    ) -> None:
        """Upload every external-URL asset in the story content into the space library, in place.

        Storyblok can't preview an extension-less external URL (Google photos) and its picker stays
        empty; uploading each photo makes it a real library asset (CDN URL + extension) so the client
        sees a thumbnail and "Replace" works. Best-effort — a failed upload keeps the external URL.

        When ``rehost_all_assets`` is True (outreach space swap), Storyblok CDN URLs from the old
        space are downloaded and re-uploaded into the new space so images survive the old space deletion.
        """
        asset_nodes: list[dict[str, Any]] = []

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                filename = node.get("filename")
                if node.get("fieldtype") == "asset" and isinstance(filename, str) and filename.strip():
                    asset_nodes.append(node)
                for value in node.values():
                    _walk(value)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)

        _walk(content)
        external_urls: set[str] = {
            node["filename"]
            for node in asset_nodes
            if node["filename"] and (rehost_all_assets or not node["filename"].startswith("https://a.storyblok.com/"))
        }
        if not external_urls:
            return

        existing: dict[str, dict[str, Any]] = await self._list_space_assets(client, space_id)
        semaphore = asyncio.Semaphore(4)

        async def _resolve_one(url: str) -> tuple[str, dict[str, Any] | None]:
            key: str = self._asset_key(url)
            already: dict[str, Any] | None = existing.get(key)
            if already is not None:
                # Same photo already in the library → reuse it, never re-upload (no duplicate asset).
                return url, already
            async with semaphore:
                return url, await self._upload_asset(client, space_id, url, key)

        results = await asyncio.gather(*(_resolve_one(url) for url in external_urls))
        uploaded: dict[str, dict[str, Any]] = {url: asset for url, asset in results if asset is not None}
        for node in asset_nodes:
            replacement = uploaded.get(node["filename"])
            if replacement is not None:
                node["id"] = replacement["id"]
                node["filename"] = replacement["filename"]

    @staticmethod
    def _asset_key(source_url: str) -> str:
        """Deterministic short digest of a source URL, used as the uploaded asset's filename stem."""
        return hashlib.sha1(source_url.encode("utf-8")).hexdigest()[:20]

    async def _list_space_assets(self, client: httpx.AsyncClient, space_id: int) -> dict[str, dict[str, Any]]:
        """Map each already-uploaded asset's filename stem to ``{id, filename}`` so a re-publish reuses it.

        Without this, every regeneration re-uploaded all photos and the asset store filled with duplicates.
        Best-effort — an unreachable listing just yields no reuse (a fresh upload), never an error.
        """
        assets_by_key: dict[str, dict[str, Any]] = {}
        for page in range(1, 6):  # up to 500 assets, far beyond a demo site's photo count
            try:
                response = await self._storyblok_request(
                    client, "GET", f"{self._base_url}/spaces/{space_id}/assets/?per_page=100&page={page}"
                )
            except httpx.HTTPError:
                break
            if response.status_code != 200:
                break
            assets: list[dict[str, Any]] = response.json().get("assets", [])
            for asset in assets:
                filename = asset.get("filename")
                asset_id = asset.get("id")
                if not isinstance(filename, str) or asset_id is None:
                    continue
                stem: str = filename.split("?")[0].rstrip("/").split("/")[-1].split(".")[0]
                if stem:
                    assets_by_key.setdefault(stem, {"id": asset_id, "filename": filename})
            if len(assets) < 100:
                break
        return assets_by_key

    async def _publish_home_story(
        self,
        client: httpx.AsyncClient,
        space_id: int,
        content_json: dict[str, Any],
        *,
        story_id: int | None = None,
        template_id: str | None = None,
        rehost_all_assets: bool = False,
    ) -> None:
        """Create or update the home story and publish it."""
        storyblok_content = self._to_storyblok_content(content_json, template_id)
        await self._upload_external_assets(client, space_id, storyblok_content, rehost_all_assets=rehost_all_assets)
        if story_id is None:
            story_id = await self._find_home_story_id(client, space_id)

        if story_id is not None:
            await self._delete_home_story(client, space_id, story_id)

        payload: dict[str, Any] = {
            "story": {
                "name": "Home",
                "slug": "home",
                # Real path so the Visual Editor previews the home at the space root, not ``/home``.
                "path": "/",
                "content": storyblok_content,
            },
            "publish": 1,
        }
        create_resp = await self._storyblok_request(
            client,
            "POST",
            f"{self._base_url}/spaces/{space_id}/stories/",
            json=payload,
        )
        try:
            create_resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 422 and "already taken" in exc.response.text:
                existing_id = await self._find_home_story_id(client, space_id)
                if existing_id is not None:
                    await self._publish_home_story(
                        client,
                        space_id,
                        content_json,
                        story_id=existing_id,
                        template_id=template_id,
                        rehost_all_assets=rehost_all_assets,
                    )
                    return
            raise ValueError(self._storyblok_error_message(exc)) from exc

    async def _configure_preview_url(
        self,
        client: httpx.AsyncClient,
        space_id: int,
        preview_url: str,
    ) -> None:
        """Set the Visual Editor preview URL (space domain) for a Storyblok space."""
        normalized_url: str = preview_url.rstrip("/") + "/"
        response = await client.put(
            f"{self._base_url}/spaces/{space_id}",
            headers=self._headers(),
            json={"space": {"domain": normalized_url}},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ValueError(self._storyblok_error_message(exc)) from exc

    async def configure_preview_url(self, space_id: int, preview_url: str) -> None:
        """Update the Visual Editor preview URL for an existing Storyblok space."""
        if not self.is_configured or not space_id:
            return

        async with httpx.AsyncClient(timeout=60.0) as client:
            await self._configure_preview_url(client, space_id, preview_url)

    async def resync_components(self, space_id: int, template_id: str | None = None) -> None:
        """Re-sync (upsert) the blok schemas of an EXISTING space.

        Propagates new fields (e.g. ``social``) and updated FR labels to
        already-provisioned spaces — the audit's missing "re-sync command".
        ``template_id`` uses that template's own schema (per-template ``SECTION_FIELDS``
        overrides included, e.g. landscaper's editable hero title); ``None`` falls back to
        the shared default schema. Idempotent; no-op in mock mode.
        """
        if not self.is_configured or not space_id:
            return
        async with httpx.AsyncClient(timeout=60.0) as client:
            await self._ensure_template_components(client, space_id, template_id)

    async def invite_collaborator(self, space_id: int, collaborator_email: str) -> None:
        """Invite a client as Storyblok space admin. Storyblok sends the invitation email."""
        if not self.is_configured:
            raise ValueError("Storyblok is not configured. Set STORYBLOK_MANAGEMENT_TOKEN on the API.")
        if not space_id:
            raise ValueError("This demo site has no Storyblok space.")
        if not collaborator_email or not collaborator_email.strip():
            raise ValueError("Client email is required to send a Storyblok invitation.")

        # Dev safety: never send a CMS invite to a real client. Storyblok sends this email
        # itself, so it bypasses EmailSendingService's redirect — reroute it here. When
        # DEV_EMAIL_REDIRECT is set, the invitation goes to the dev inbox instead.
        redirect = getattr(settings, "dev_email_redirect", None)
        if redirect:
            logger.warning("[DEV] Storyblok invite rerouted %s -> %s", collaborator_email, redirect)
            collaborator_email = redirect.strip()

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Storyblok expects the fields at the top level of the body — NOT wrapped in a
            # ``collaborator`` object (which it ignores, then rejects with 422 "Email is required").
            # An email with no Storyblok account yet triggers an invitation (account created on accept).
            invite_resp = await client.post(
                f"{self._base_url}/spaces/{space_id}/collaborators/",
                headers=self._headers(),
                json={
                    "email": collaborator_email.strip(),
                    "role": "admin",
                    "space_role_id": None,
                    "space_role_ids": [],
                    "permissions": [],
                },
            )
            try:
                invite_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ValueError(self._storyblok_error_message(exc)) from exc

    @staticmethod
    def _collaborator_emails(collaborator: dict[str, Any]) -> set[str]:
        """Collect the lower-cased emails a collaborator entry may carry (linked user + pending invite).

        Storyblok exposes the address in different places for an accepted member vs a still-pending
        invitation, and the object is loosely documented — so every plausible field is probed.
        """
        emails: set[str] = set()

        def _add(value: Any) -> None:
            if isinstance(value, str) and "@" in value:
                emails.add(value.strip().lower())

        user = collaborator.get("user")
        if isinstance(user, dict):
            for key in ("real_email", "alt_email", "userid", "email", "friendly_name"):
                _add(user.get(key))
        for key in ("email", "invitation_email"):
            _add(collaborator.get(key))
        invitation = collaborator.get("invitation")
        if isinstance(invitation, dict):
            _add(invitation.get("email"))
        else:
            _add(invitation)
        return emails

    async def get_collaborator_status(self, space_id: int, email: str) -> str:
        """Return the client's state on a space: ``not_invited`` / ``pending`` / ``joined`` / ``unknown``.

        Reads ``GET /spaces/{id}/collaborators/`` and matches the invited email. A pending invitation
        (email not yet accepted, no Storyblok account) is told apart from a joined member by the
        presence of a linked user vs an ``invitation`` marker. Best-effort: any failure returns
        ``unknown`` so callers never break and never clobber a previously known state.
        """
        if not self.is_configured or not space_id or not email or not email.strip():
            return "unknown"
        target: str = email.strip().lower()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self._base_url}/spaces/{space_id}/collaborators/",
                    headers=self._headers(),
                )
            if response.status_code != 200:
                logger.warning(
                    "Storyblok collaborators fetch failed for space %s (%s): %s",
                    space_id,
                    response.status_code,
                    response.text[:300],
                )
                return "unknown"
            collaborators: list[dict[str, Any]] = response.json().get("collaborators", [])
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Storyblok collaborators fetch error for space %s: %s", space_id, exc)
            return "unknown"

        for collaborator in collaborators:
            if not isinstance(collaborator, dict) or target not in self._collaborator_emails(collaborator):
                continue
            user = collaborator.get("user")
            is_disabled: bool = bool(user.get("disabled")) if isinstance(user, dict) else False
            has_real_user: bool = bool(
                collaborator.get("user_id") or (user.get("id") if isinstance(user, dict) else None)
            )
            # Joined = a real, enabled user is linked and no pending-invitation marker remains. A
            # populated ``invitation``, a disabled (not-yet-activated) user, or no linked user at all
            # each mean the client was invited but hasn't joined yet → still pending.
            if has_real_user and not collaborator.get("invitation") and not is_disabled:
                return "joined"
            return "pending"

        # No entry matched the invited email — log the shape (keys only, no PII) to catch field drift.
        logger.info(
            "Storyblok: invited email not matched among %d collaborators for space %s; entry keys=%s",
            len(collaborators),
            space_id,
            [sorted(c.keys()) for c in collaborators if isinstance(c, dict)][:5],
        )
        return "not_invited"

    async def provision_space(
        self,
        *,
        business_name: str,
        slug: str,
        phone: str | None,
        email: str | None,
        city: str | None,
        description: str | None,
        template_id: str,
        collaborator_email: str,
        preview_url: str,
        invite_client: bool = False,
        theme: dict[str, str] | None = None,
        enrichment: dict[str, Any] | None = None,
        section_overrides: dict[str, Any] | None = None,
    ) -> StoryblokProvisionResult:
        """
        Create a Storyblok space and seed the home story.

        When ``invite_client`` is True, Storyblok sends a collaborator invite to
        ``collaborator_email``. Falls back to mock mode when credentials are missing.
        ``section_overrides`` (curated cards) replace the generated sections, as on regeneration.
        """
        content_json: dict[str, Any] = self.build_content_json(
            business_name=business_name,
            phone=phone,
            email=email,
            city=city,
            description=description,
            template_id=template_id,
            theme=theme,
            enrichment=enrichment,
        )
        apply_section_overrides(content_json, section_overrides, enrichment)

        return await self.provision_space_with_content(
            business_name=business_name,
            slug=slug,
            template_id=template_id,
            collaborator_email=collaborator_email,
            preview_url=preview_url,
            content_json=content_json,
            invite_client=invite_client,
        )

    async def provision_space_with_content(
        self,
        *,
        business_name: str,
        slug: str,
        template_id: str,
        collaborator_email: str,
        preview_url: str,
        content_json: dict[str, Any],
        invite_client: bool = False,
        rehost_all_assets: bool = False,
    ) -> StoryblokProvisionResult:
        """
        Create a Storyblok space and seed the home story from an existing ``content_json``.

        Used for initial provisioning and for outreach swaps that must preserve published edits.
        """
        if not self.is_configured:
            mock_password: str = self._generate_password()
            return StoryblokProvisionResult(
                space_id=None,
                public_token=None,
                preview_token=None,
                editor_url="https://app.storyblok.com/#/me/spaces",
                login_email=collaborator_email,
                login_password=mock_password,
                invite_sent=False,
                content_json=content_json,
                mock_mode=True,
            )

        space_name: str = self.expected_space_name(business_name, slug)
        async with httpx.AsyncClient(timeout=120.0) as client:
            space_resp = await client.post(
                f"{self._base_url}/spaces/",
                headers=self._headers(),
                json={"space": {"name": space_name}},
            )
            try:
                space_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ValueError(self._storyblok_error_message(exc)) from exc

            space_data: dict[str, Any] = space_resp.json()["space"]
            space_id: int = int(space_data["id"])
            editor_url: str = f"https://app.storyblok.com/#/me/spaces/{space_id}/dashboard"

            try:
                await asyncio.gather(
                    self._configure_preview_url(client, space_id, preview_url),
                    self._ensure_template_components(client, space_id, template_id),
                    self._register_publish_webhook(client, space_id),
                )
                await self._publish_home_story(
                    client,
                    space_id,
                    content_json,
                    template_id=template_id,
                    rehost_all_assets=rehost_all_assets,
                )

                space_detail = await client.get(
                    f"{self._base_url}/spaces/{space_id}",
                    headers=self._headers(),
                )
                space_detail.raise_for_status()
                detail: dict[str, Any] = space_detail.json()["space"]

                public_token: str | None = detail.get("first_token")
                preview_token: str | None = detail.get("preview_token") or public_token

                invite_sent: bool = False
                if invite_client:
                    try:
                        await self.invite_collaborator(space_id, collaborator_email)
                        invite_sent = True
                    except ValueError as exc:
                        logger.warning(
                            "Storyblok collaborator invite failed for %s: %s",
                            collaborator_email,
                            exc,
                        )

                return StoryblokProvisionResult(
                    space_id=space_id,
                    public_token=public_token,
                    preview_token=preview_token,
                    editor_url=editor_url,
                    login_email=collaborator_email,
                    login_password=None,
                    invite_sent=invite_sent,
                    content_json=content_json,
                    mock_mode=False,
                )
            except Exception as exc:
                raise StoryblokProvisionError(
                    str(exc),
                    space_id=space_id,
                    editor_url=editor_url,
                    content_json=content_json,
                ) from exc

    async def update_home_story_content(
        self, space_id: int, content_json: dict[str, Any], template_id: str | None = None
    ) -> None:
        """Update and publish the home story content in an existing Storyblok space."""
        if not self.is_configured or not space_id:
            return

        async with httpx.AsyncClient(timeout=60.0) as client:
            await self._ensure_template_components(client, space_id, template_id)

            story_id = await self._find_home_story_id(client, space_id)
            await self._publish_home_story(client, space_id, content_json, story_id=story_id, template_id=template_id)

    def expected_space_name(self, business_name: str, slug: str) -> str:
        """Return the Storyblok space name used when provisioning a demo site."""
        return f"Demo — {business_name} ({slug})"

    @staticmethod
    def parse_space_id_from_editor_url(editor_url: str | None) -> int | None:
        """Extract a Storyblok space id from an editor dashboard URL."""
        if not editor_url:
            return None
        match: re.Match[str] | None = re.search(r"/spaces/(\d+)", editor_url)
        if not match:
            return None
        return int(match.group(1))

    async def find_space_id_by_name(self, space_name: str) -> int | None:
        """Find a Storyblok space id by its exact display name."""
        if not self.is_configured:
            return None

        page: int = 1
        async with httpx.AsyncClient(timeout=60.0) as client:
            while page <= 20:
                response = await client.get(
                    f"{self._base_url}/spaces/",
                    headers=self._headers(),
                    params={"page": page, "per_page": 100},
                )
                response.raise_for_status()
                payload: dict[str, Any] = response.json()
                spaces: list[dict[str, Any]] = payload.get("spaces", [])
                if not spaces:
                    break
                for space in spaces:
                    if space.get("name") == space_name:
                        return int(space["id"])
                page += 1
        return None

    async def resolve_space_id(
        self,
        *,
        space_id: int | None,
        editor_url: str | None,
        business_name: str,
        slug: str,
    ) -> int | None:
        """Resolve a Storyblok space id from stored metadata or the expected space name."""
        if space_id:
            return space_id

        parsed_id: int | None = self.parse_space_id_from_editor_url(editor_url)
        if parsed_id:
            return parsed_id

        return await self.find_space_id_by_name(self.expected_space_name(business_name, slug))

    async def delete_demo_space(
        self,
        *,
        space_id: int | None,
        editor_url: str | None,
        business_name: str,
        slug: str,
    ) -> int | None:
        """Delete the Storyblok space linked to a demo site when it can be resolved."""
        resolved_space_id: int | None = await self.resolve_space_id(
            space_id=space_id,
            editor_url=editor_url,
            business_name=business_name,
            slug=slug,
        )
        if not resolved_space_id:
            return None

        await self.delete_space(resolved_space_id)
        return resolved_space_id

    async def delete_space(self, space_id: int) -> None:
        """Delete a Storyblok space by id."""
        if not self.is_configured or not space_id:
            return

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.delete(
                f"{self._base_url}/spaces/{space_id}",
                headers=self._headers(),
            )
            if response.status_code not in (200, 204, 404):
                response.raise_for_status()

    async def _list_component_ids(self, client: httpx.AsyncClient, space_id: int) -> dict[str, int]:
        """Return ``{component_name: id}`` for the space's existing components."""
        response = await self._storyblok_request(client, "GET", f"{self._base_url}/spaces/{space_id}/components/")
        if response.status_code != 200:
            return {}
        return {
            component["name"]: int(component["id"])
            for component in response.json().get("components", [])
            if component.get("name") and component.get("id") is not None
        }

    async def _ensure_template_components(
        self, client: httpx.AsyncClient, space_id: int, template_id: str | None = None
    ) -> None:
        """Upsert (create OR update) the blok components the client actually edits.

        All active templates use the flat ``SiteContent`` path, so a space only
        needs: ``page`` (root), ``theme_palette``, and the shared ``site_content``
        blok family (``SITE_CONTENT_SCHEMAS``). The legacy per-section bloks
        (hero/trust/…) and the per-template rich schemas are intentionally NOT
        registered anymore — they were never consumed by demo-host and polluted
        the client's editor with ~60 unusable blok types.

        **Existing components are UPDATED (PUT)** — this is what propagates new fields
        (e.g. ``social``) and FR labels to already-provisioned spaces (the re-sync the
        audit asked for). Upserts run with bounded concurrency instead of the old
        sequential loop, so provisioning is markedly faster.
        """
        components: list[dict[str, Any]] = [
            {
                "name": "theme_palette",
                "display_name": "Theme palette",
                "schema": {
                    "primary": {"type": "text"},
                    "secondary": {"type": "text"},
                    "accent": {"type": "text"},
                },
            },
            {
                "name": "page",
                "display_name": "Page",
                "is_root": True,
                "is_nestable": False,
                "schema": {
                    "theme": {
                        "type": "bloks",
                        "restrict_components": True,
                        "component_whitelist": ["theme_palette"],
                        "maximum": 1,
                    },
                    "body": {
                        "type": "bloks",
                        "restrict_components": True,
                        # The flat SiteContent is split into small ``section_*`` bloks (readable editor).
                        "component_whitelist": SECTION_COMPONENT_NAMES,
                    },
                },
            },
            # Per-template schemas add that template's one-off image fields to the right sections;
            # ``None`` (e.g. a space-only resync) falls back to the shared default schema.
            *(template_registry.content_schemas(template_id) if template_id else SITE_CONTENT_SCHEMAS),
        ]

        existing: dict[str, int] = await self._list_component_ids(client, space_id)
        semaphore = asyncio.Semaphore(5)

        async def _upsert(component: dict[str, Any]) -> None:
            async with semaphore:
                name: str = component["name"]
                component_id: int | None = existing.get(name)
                if component_id is not None:
                    response = await self._storyblok_request(
                        client,
                        "PUT",
                        f"{self._base_url}/spaces/{space_id}/components/{component_id}",
                        json={"component": component},
                    )
                else:
                    response = await self._storyblok_request(
                        client,
                        "POST",
                        f"{self._base_url}/spaces/{space_id}/components/",
                        json={"component": component},
                    )
                    # A 422 here is almost always "name already taken" from a concurrent
                    # create or a stale listing — re-list and PUT so the rich schema still
                    # lands. Swallowing every 422 (the old behaviour) let a genuine schema
                    # rejection pass silently, leaving the client an empty placeholder blok.
                    if response.status_code == 422:
                        refreshed: dict[str, int] = await self._list_component_ids(client, space_id)
                        existing_id: int | None = refreshed.get(name)
                        if existing_id is not None:
                            response = await self._storyblok_request(
                                client,
                                "PUT",
                                f"{self._base_url}/spaces/{space_id}/components/{existing_id}",
                                json={"component": component},
                            )
                response.raise_for_status()

        await asyncio.gather(*(_upsert(component) for component in components))

    async def _register_publish_webhook(self, client: httpx.AsyncClient, space_id: int) -> None:
        """Register the story-publish webhook so client edits sync back to ``content_json``.

        The public site renders ``demo_site.content_json`` — without this webhook a
        client publishing in Storyblok would never see their edits live. Failures are
        logged, never raised (the webhook can be re-registered later); localhost API
        URLs are skipped because Storyblok could not reach them anyway.
        """
        endpoint_url: str = f"{settings.api_base_url.rstrip('/')}{settings.api_prefix}/webhooks/storyblok"
        if "localhost" in endpoint_url or "127.0.0.1" in endpoint_url:
            logger.info("Skipping Storyblok webhook registration (local API URL: %s)", endpoint_url)
            return

        payload: dict[str, Any] = {
            "webhook_endpoint": {
                "name": "DevLeadHunter — sync content_json",
                "endpoint": endpoint_url,
                "actions": ["story.published"],
                "activated": True,
            }
        }
        secret: str | None = settings.storyblok_webhook_secret
        if secret:
            payload["webhook_endpoint"]["secret"] = secret

        response = await self._storyblok_request(
            client,
            "POST",
            f"{self._base_url}/spaces/{space_id}/webhook_endpoints",
            json=payload,
        )
        if response.status_code not in (200, 201, 422):
            logger.warning(
                "Storyblok webhook registration failed for space %s (%s): %s",
                space_id,
                response.status_code,
                response.text[:300],
            )

    async def fetch_published_home_content(self, public_token: str) -> dict[str, Any] | None:
        """Fetch the PUBLISHED home story content from the Storyblok CDN API.

        Used by the publish webhook: the payload is never trusted, the story is
        always re-fetched from Storyblok (source of truth) with the space's own
        public token.

        Args:
            public_token: The space's public (published-only) token.

        Returns:
            The story ``content`` dict, or None when unavailable.
        """
        # follow_redirects: the EU CDN host 301-redirects; without this the webhook
        # re-fetch would silently fail and client edits would never sync back.
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                f"{self.cdn_base_url}/v2/cdn/stories/home",
                params={
                    "token": public_token,
                    "version": "published",
                    # Cache-buster: always read the freshly published version.
                    "cv": str(int(datetime.now(UTC).timestamp())),
                },
            )
            if response.status_code != 200:
                logger.warning("Storyblok CDN fetch failed (%s): %s", response.status_code, response.text[:300])
                return None
            content = response.json().get("story", {}).get("content")
            return content if isinstance(content, dict) else None

    @staticmethod
    def _generate_password(length: int = 14) -> str:
        alphabet: str = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))


storyblok_service = StoryblokService()
