"""
Storyblok Management API integration for demo site provisioning.

When STORYBLOK_MANAGEMENT_TOKEN is not configured, runs in mock mode and stores
content locally in the database (demo-host renders from content_json).
"""
from __future__ import annotations

import logging
import secrets
import string
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from core.config import settings

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
    ) -> dict[str, Any]:
        """
        Build the default Storyblok story payload for a template.

        @param business_name - Client business display name.
        @param phone - Contact phone number.
        @param email - Contact email address.
        @param city - Service area / city.
        @param description - Short business description.
        @param template_id - Selected template identifier.
        @returns Storyblok-compatible content object.
        """
        subtitle: str = description or f"Professional services in {city or 'your area'}"
        services: list[str] = ["Emergency repairs", "Installations", "Maintenance"]
        if template_id == "plumber-simple":
            services = ["Leak repair", "Boiler installation", "Drain unblocking"]

        return {
            "component": "page",
            "body": [
                {
                    "_uid": "hero-1",
                    "component": "hero",
                    "title": business_name,
                    "subtitle": subtitle,
                    "phone": phone or "",
                    "cta_label": "Call now",
                },
                {
                    "_uid": "services-1",
                    "component": "services",
                    "heading": "Our services",
                    "items": [
                        {
                            "_uid": f"s-{i}",
                            "component": "service_item",
                            "label": label,
                        }
                        for i, label in enumerate(services)
                    ],
                },
                {
                    "_uid": "contact-1",
                    "component": "contact",
                    "heading": "Contact us",
                    "email": email or "",
                    "phone": phone or "",
                    "city": city or "",
                },
            ],
        }

    def _storyblok_error_message(self, exc: httpx.HTTPStatusError) -> str:
        """Build a readable Storyblok API error for API responses."""
        detail: str = exc.response.text.strip()
        if detail:
            return f"Storyblok API error ({exc.response.status_code}): {detail}"
        return f"Storyblok API error ({exc.response.status_code}) for {exc.request.method} {exc.request.url}"

    async def _publish_home_story(
        self,
        client: httpx.AsyncClient,
        space_id: int,
        content_json: dict[str, Any],
        *,
        story_id: Optional[int] = None,
    ) -> None:
        """Create or update the home story and publish it."""
        payload: dict[str, Any] = {
            "story": {
                "name": "Home",
                "slug": "home",
                "content": content_json,
            },
            "publish": 1,
        }

        if story_id is not None:
            update_resp = await client.put(
                f"{self._base_url}/spaces/{space_id}/stories/{story_id}",
                headers=self._headers(),
                json={"story": {"content": content_json}, "publish": 1},
            )
            try:
                update_resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise ValueError(self._storyblok_error_message(exc)) from exc
            return

        create_resp = await client.post(
            f"{self._base_url}/spaces/{space_id}/stories/",
            headers=self._headers(),
            json=payload,
        )
        try:
            create_resp.raise_for_status()
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
    ) -> StoryblokProvisionResult:
        """
        Create a Storyblok space and seed the home story.

        The client receives a collaborator invite on ``collaborator_email``.
        Falls back to mock mode when Management API credentials are missing.
        """
        content_json: dict[str, Any] = self.build_content_json(
            business_name=business_name,
            phone=phone,
            email=email,
            city=city,
            description=description,
            template_id=template_id,
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

        space_name: str = f"Demo — {business_name} ({slug})"
        async with httpx.AsyncClient(timeout=60.0) as client:
            space_resp = await client.post(
                f"{self._base_url}/spaces/",
                headers=self._headers(),
                json={"space": {"name": space_name}},
            )
            space_resp.raise_for_status()
            space_data: dict[str, Any] = space_resp.json()["space"]
            space_id: int = int(space_data["id"])

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
            editor_url: str = f"https://app.storyblok.com/#/me/spaces/{space_id}/dashboard"

            invite_sent: bool = False
            try:
                invite_resp = await client.post(
                    f"{self._base_url}/spaces/{space_id}/collaborators/",
                    headers=self._headers(),
                    json={
                        "collaborator": {
                            "email": collaborator_email,
                            "role": "admin",
                            "permissions": [],
                        }
                    },
                )
                invite_resp.raise_for_status()
                invite_sent = True
            except httpx.HTTPError as exc:
                logger.warning("Storyblok collaborator invite failed for %s: %s", collaborator_email, exc)

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

    async def update_home_story_content(self, space_id: int, content_json: dict[str, Any]) -> None:
        """Update and publish the home story content in an existing Storyblok space."""
        if not self.is_configured or not space_id:
            return

        async with httpx.AsyncClient(timeout=60.0) as client:
            await self._ensure_template_components(client, space_id)

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
            story_id: Optional[int] = int(stories[0]["id"]) if stories else None
            await self._publish_home_story(client, space_id, content_json, story_id=story_id)

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
        """Register minimal blok components for the plumber-simple template."""
        components: list[dict[str, Any]] = [
            {
                "name": "page",
                "display_name": "Page",
                "is_root": True,
                "is_nestable": False,
                "schema": {},
            },
            {
                "name": "hero",
                "display_name": "Hero",
                "schema": {
                    "title": {"type": "text"},
                    "subtitle": {"type": "textarea"},
                    "phone": {"type": "text"},
                    "cta_label": {"type": "text"},
                },
            },
            {
                "name": "services",
                "display_name": "Services",
                "schema": {
                    "heading": {"type": "text"},
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
                "schema": {"label": {"type": "text"}},
            },
            {
                "name": "contact",
                "display_name": "Contact",
                "schema": {
                    "heading": {"type": "text"},
                    "email": {"type": "text"},
                    "phone": {"type": "text"},
                    "city": {"type": "text"},
                },
            },
        ]

        for component in components:
            try:
                await client.post(
                    f"{self._base_url}/spaces/{space_id}/components/",
                    headers=self._headers(),
                    json={"component": component},
                )
            except httpx.HTTPError as exc:
                logger.warning("Storyblok component '%s' creation skipped: %s", component["name"], exc)

    @staticmethod
    def _generate_password(length: int = 14) -> str:
        alphabet: str = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))


storyblok_service = StoryblokService()
