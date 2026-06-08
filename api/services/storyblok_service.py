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
from typing import Any, Optional

import httpx

from core.config import settings
from services.enrichment_content import apply_to_content as apply_enrichment_to_content
from services.templates import registry as template_registry

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
        subtitle: str = description or f"Plombier professionnel — dépannage rapide à {area}"
        palette: dict[str, str] = theme or {
            "primary": "#0284c7",
            "secondary": "#0f172a",
            "accent": "#f59e0b",
        }

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

    def _to_storyblok_content(self, content_json: dict[str, Any]) -> dict[str, Any]:
        """Adapt local demo content to Storyblok blok schemas."""
        theme_raw = content_json.get("theme")
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
                    "primary": str(theme_raw.get("primary", theme_block["primary"])),
                    "secondary": str(theme_raw.get("secondary", theme_block["secondary"])),
                    "accent": str(theme_raw.get("accent", theme_block["accent"])),
                }
            )

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
    ) -> None:
        """Create or update the home story and publish it."""
        storyblok_content = self._to_storyblok_content(content_json)
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

    async def invite_collaborator(self, space_id: int, collaborator_email: str) -> None:
        """Invite a client as Storyblok space admin. Storyblok sends the invitation email."""
        if not self.is_configured:
            raise ValueError("Storyblok is not configured. Set STORYBLOK_MANAGEMENT_TOKEN on the API.")
        if not space_id:
            raise ValueError("This demo site has no Storyblok space.")
        if not collaborator_email or not collaborator_email.strip():
            raise ValueError("Client email is required to send a Storyblok invitation.")

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
                await self._configure_preview_url(client, space_id, preview_url)
                await self._ensure_template_components(client, space_id)
                await self._publish_home_story(client, space_id, content_json)

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

    async def update_home_story_content(self, space_id: int, content_json: dict[str, Any]) -> None:
        """Update and publish the home story content in an existing Storyblok space."""
        if not self.is_configured or not space_id:
            return

        async with httpx.AsyncClient(timeout=60.0) as client:
            await self._ensure_template_components(client, space_id)

            story_id = await self._find_home_story_id(client, space_id)
            await self._publish_home_story(client, space_id, content_json, story_id=story_id)

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

    async def _ensure_template_components(self, client: httpx.AsyncClient, space_id: int) -> None:
        """Register blok components required by the plumber-simple template."""
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
                        "component_whitelist": [
                            "hero",
                            "trust",
                            "services",
                            "why_us",
                            "contact",
                            *template_registry.body_components(),
                        ],
                    },
                },
            },
            {
                "name": "hero",
                "display_name": "Hero",
                "schema": {
                    "title": {"type": "text"},
                    "subtitle": {"type": "textarea"},
                    "phone": {"type": "text"},
                    "cta_label": {"type": "text"},
                    "badge": {"type": "text"},
                    "city": {"type": "text"},
                    "image": {"type": "text"},
                },
            },
            {
                "name": "trust",
                "display_name": "Trust",
                "schema": {
                    "heading": {"type": "text"},
                    "items": {
                        "type": "bloks",
                        "restrict_components": True,
                        "component_whitelist": ["trust_item"],
                    },
                },
            },
            {
                "name": "trust_item",
                "display_name": "Trust item",
                "schema": {
                    "value": {"type": "text"},
                    "label": {"type": "text"},
                },
            },
            {
                "name": "services",
                "display_name": "Services",
                "schema": {
                    "heading": {"type": "text"},
                    "subheading": {"type": "textarea"},
                    "items": {
                        "type": "bloks",
                        "restrict_components": True,
                        "component_whitelist": ["service_item"],
                    },
                },
            },
            {
                "name": "service_item",
                "display_name": "Service item",
                "schema": {
                    "label": {"type": "text"},
                    "description": {"type": "textarea"},
                    "icon": {"type": "text"},
                },
            },
            {
                "name": "why_us",
                "display_name": "Why us",
                "schema": {
                    "heading": {"type": "text"},
                    "items": {
                        "type": "bloks",
                        "restrict_components": True,
                        "component_whitelist": ["why_item"],
                    },
                },
            },
            {
                "name": "why_item",
                "display_name": "Why item",
                "schema": {"label": {"type": "text"}},
            },
            {
                "name": "contact",
                "display_name": "Contact",
                "schema": {
                    "heading": {"type": "text"},
                    "subheading": {"type": "textarea"},
                    "email": {"type": "text"},
                    "phone": {"type": "text"},
                    "city": {"type": "text"},
                    "hours": {"type": "text"},
                },
            },
        ]
        components.extend(template_registry.component_schemas())

        for component in components:
            response = await self._storyblok_request(
                client,
                "POST",
                f"{self._base_url}/spaces/{space_id}/components/",
                json={"component": component},
            )
            if response.status_code not in (200, 201, 422):
                response.raise_for_status()
            await asyncio.sleep(0.15)

    @staticmethod
    def _generate_password(length: int = 14) -> str:
        alphabet: str = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))


storyblok_service = StoryblokService()
