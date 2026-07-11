"""
Storyblok Management API integration for demo site provisioning.

When STORYBLOK_MANAGEMENT_TOKEN is not configured, runs in mock mode and stores
content locally in the database (demo-host renders from content_json).
"""
from __future__ import annotations

import asyncio
import logging
import re
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from core.config import settings
from services.enrichment_content import apply_to_content as apply_enrichment_to_content
from services.templates import registry as template_registry
from services.templates.site_content import SITE_CONTENT_SCHEMAS

logger = logging.getLogger(__name__)


@dataclass
class StoryblokProvisionResult:
    """Result of Storyblok space provisioning."""

    space_id: Optional[int]
    public_token: Optional[str]
    preview_token: Optional[str]
    editor_url: Optional[str]
    login_email: Optional[str]
    login_password: Optional[str]
    invite_sent: bool
    content_json: dict[str, Any]
    mock_mode: bool


class StoryblokProvisionError(Exception):
    """Raised when Storyblok provisioning fails after the space was created."""

    def __init__(
        self,
        message: str,
        *,
        space_id: Optional[int] = None,
        editor_url: Optional[str] = None,
        content_json: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.space_id = space_id
        self.editor_url = editor_url
        self.content_json = content_json


class StoryblokService:
    """Creates and tears down Storyblok spaces for demo websites."""

    def __init__(self) -> None:
        self._token: Optional[str] = settings.storyblok_management_token
        self._region: str = settings.storyblok_region
        self._base_url: str = f"https://mapi.storyblok.com/v1"

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
        phone: Optional[str],
        email: Optional[str],
        city: Optional[str],
        description: Optional[str],
        template_id: str,
        theme: Optional[dict[str, str]] = None,
        enrichment: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Build the default Storyblok story payload for a template.

        @param business_name - Client business display name.
        @param phone - Contact phone number.
        @param email - Contact email address.
        @param city - Service area / city.
        @param description - Short business description.
        @param template_id - Selected template identifier.
        @param theme - Optional color palette (primary, secondary, accent).
        @param enrichment - Optional rich data merged into the content (photos, reviews…).
        @returns Storyblok-compatible content object.
        """
        area: str = city or "votre secteur"
        subtitle: str = description or template_registry.default_subtitle(template_id, area)
        # No explicit theme → use the template's own signature palette (Lumen yellow,
        # Cuivre water-blue…) instead of a generic fallback, so generated demos keep their DA.
        palette: dict[str, str] = theme or template_registry.default_theme(template_id)

        # Phase 4b — templates that opt in produce a FLAT SiteContent that already
        # consumes enrichment; the rich enrichment merge must not run for them.
        if template_registry.uses_site_content(template_id):
            return template_registry.build_site_content(
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
        return apply_enrichment_to_content(content, enrichment)

    @staticmethod
    def _is_flat_site_content(content_json: dict[str, Any]) -> bool:
        """Detect the flat ``SiteContent`` shape (Phase 4b) vs the rich body-based content.

        Flat SiteContent has no ``body`` list and carries a ``businessName`` key.
        """
        return "body" not in content_json and "businessName" in content_json

    def _to_storyblok_content(
        self, content_json: dict[str, Any], template_id: Optional[str] = None
    ) -> dict[str, Any]:
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

        if self._is_flat_site_content(content_json) and template_id and template_registry.uses_site_content(template_id):
            site_content_blok = template_registry.to_storyblok_site_content(template_id, content_json)
            return {
                "component": "page",
                "theme": theme_block,
                "body": [site_content_blok],
            }

        return {
            "component": "page",
            "theme": theme_block,
            "body": content_json.get("body", []),
        }

    async def _storyblok_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        *,
        retries: int = 4,
        **kwargs: Any,
    ) -> httpx.Response:
        """Perform a Storyblok request with basic retry on rate limits."""
        delay_seconds: float = 0.35
        last_response: Optional[httpx.Response] = None

        for attempt in range(retries):
            if attempt:
                await asyncio.sleep(delay_seconds * attempt)
            response = await client.request(method, url, headers=self._headers(), **kwargs)
            last_response = response
            if response.status_code != 429:
                return response

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

    async def _find_home_story_id(
        self,
        client: httpx.AsyncClient,
        space_id: int,
    ) -> Optional[int]:
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

    async def _publish_home_story(
        self,
        client: httpx.AsyncClient,
        space_id: int,
        content_json: dict[str, Any],
        *,
        story_id: Optional[int] = None,
        template_id: Optional[str] = None,
    ) -> None:
        """Create or update the home story and publish it."""
        storyblok_content = self._to_storyblok_content(content_json, template_id)
        if story_id is None:
            story_id = await self._find_home_story_id(client, space_id)

        if story_id is not None:
            await self._delete_home_story(client, space_id, story_id)

        payload: dict[str, Any] = {
            "story": {
                "name": "Home",
                "slug": "home",
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

    async def resync_components(self, space_id: int) -> None:
        """Re-sync (upsert) the blok schemas of an EXISTING space.

        Propagates new fields (e.g. ``social``) and updated FR labels to
        already-provisioned spaces — the audit's missing "re-sync command".
        Idempotent; no-op in mock mode.
        """
        if not self.is_configured or not space_id:
            return
        async with httpx.AsyncClient(timeout=60.0) as client:
            await self._ensure_template_components(client, space_id)

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
            invite_resp = await client.post(
                f"{self._base_url}/spaces/{space_id}/collaborators/",
                headers=self._headers(),
                json={
                    "collaborator": {
                        "email": collaborator_email.strip(),
                        "role": "admin",
                        "permissions": [],
                    }
                },
            )
            try:
                invite_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ValueError(self._storyblok_error_message(exc)) from exc

    async def provision_space(
        self,
        *,
        business_name: str,
        slug: str,
        phone: Optional[str],
        email: Optional[str],
        city: Optional[str],
        description: Optional[str],
        template_id: str,
        collaborator_email: str,
        preview_url: str,
        invite_client: bool = False,
        theme: Optional[dict[str, str]] = None,
        enrichment: Optional[dict[str, Any]] = None,
    ) -> StoryblokProvisionResult:
        """
        Create a Storyblok space and seed the home story.

        When ``invite_client`` is True, Storyblok sends a collaborator invite to
        ``collaborator_email``. Falls back to mock mode when credentials are missing.
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
        async with httpx.AsyncClient(timeout=60.0) as client:
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
                # These three are independent of each other → run concurrently
                # (webhook registration is best-effort and never raises).
                await asyncio.gather(
                    self._configure_preview_url(client, space_id, preview_url),
                    self._ensure_template_components(client, space_id),
                    self._register_publish_webhook(client, space_id),
                )
                # Publish last: the home story references the ``site_content`` component.
                await self._publish_home_story(client, space_id, content_json, template_id=template_id)

                space_detail = await client.get(
                    f"{self._base_url}/spaces/{space_id}",
                    headers=self._headers(),
                )
                space_detail.raise_for_status()
                detail: dict[str, Any] = space_detail.json()["space"]

                public_token: Optional[str] = detail.get("first_token")
                preview_token: Optional[str] = detail.get("preview_token") or public_token

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
        self, space_id: int, content_json: dict[str, Any], template_id: Optional[str] = None
    ) -> None:
        """Update and publish the home story content in an existing Storyblok space."""
        if not self.is_configured or not space_id:
            return

        async with httpx.AsyncClient(timeout=60.0) as client:
            await self._ensure_template_components(client, space_id)

            story_id = await self._find_home_story_id(client, space_id)
            await self._publish_home_story(
                client, space_id, content_json, story_id=story_id, template_id=template_id
            )

    def expected_space_name(self, business_name: str, slug: str) -> str:
        """Return the Storyblok space name used when provisioning a demo site."""
        return f"Demo — {business_name} ({slug})"

    @staticmethod
    def parse_space_id_from_editor_url(editor_url: Optional[str]) -> Optional[int]:
        """Extract a Storyblok space id from an editor dashboard URL."""
        if not editor_url:
            return None
        match: Optional[re.Match[str]] = re.search(r"/spaces/(\d+)", editor_url)
        if not match:
            return None
        return int(match.group(1))

    async def find_space_id_by_name(self, space_name: str) -> Optional[int]:
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
        space_id: Optional[int],
        editor_url: Optional[str],
        business_name: str,
        slug: str,
    ) -> Optional[int]:
        """Resolve a Storyblok space id from stored metadata or the expected space name."""
        if space_id:
            return space_id

        parsed_id: Optional[int] = self.parse_space_id_from_editor_url(editor_url)
        if parsed_id:
            return parsed_id

        return await self.find_space_id_by_name(self.expected_space_name(business_name, slug))

    async def delete_demo_space(
        self,
        *,
        space_id: Optional[int],
        editor_url: Optional[str],
        business_name: str,
        slug: str,
    ) -> Optional[int]:
        """Delete the Storyblok space linked to a demo site when it can be resolved."""
        resolved_space_id: Optional[int] = await self.resolve_space_id(
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
        response = await self._storyblok_request(
            client, "GET", f"{self._base_url}/spaces/{space_id}/components/"
        )
        if response.status_code != 200:
            return {}
        return {
            component["name"]: int(component["id"])
            for component in response.json().get("components", [])
            if component.get("name") and component.get("id") is not None
        }

    async def _ensure_template_components(self, client: httpx.AsyncClient, space_id: int) -> None:
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
                        "type": "blok",
                        "restrict_components": True,
                        "component_whitelist": ["theme_palette"],
                        "maximum": 1,
                    },
                    "body": {
                        "type": "bloks",
                        "restrict_components": True,
                        # The flat SiteContent page carries one ``site_content`` blok.
                        "component_whitelist": ["site_content"],
                    },
                },
            },
            *SITE_CONTENT_SCHEMAS,
        ]

        existing: dict[str, int] = await self._list_component_ids(client, space_id)
        semaphore = asyncio.Semaphore(5)

        async def _upsert(component: dict[str, Any]) -> None:
            async with semaphore:
                name: str = component["name"]
                component_id: Optional[int] = existing.get(name)
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
                if response.status_code not in (200, 201, 422):
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
        secret: Optional[str] = settings.storyblok_webhook_secret
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

    async def fetch_published_home_content(self, public_token: str) -> Optional[dict[str, Any]]:
        """Fetch the PUBLISHED home story content from the Storyblok CDN API.

        Used by the publish webhook: the payload is never trusted, the story is
        always re-fetched from Storyblok (source of truth) with the space's own
        public token.

        @param public_token - The space's public (published-only) token.
        @returns The story ``content`` dict, or None when unavailable.
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
                    "cv": str(int(datetime.now(timezone.utc).timestamp())),
                },
            )
            if response.status_code != 200:
                logger.warning(
                    "Storyblok CDN fetch failed (%s): %s", response.status_code, response.text[:300]
                )
                return None
            content = response.json().get("story", {}).get("content")
            return content if isinstance(content, dict) else None

    @staticmethod
    def _generate_password(length: int = 14) -> str:
        alphabet: str = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))


storyblok_service = StoryblokService()
