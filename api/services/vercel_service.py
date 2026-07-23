"""
Vercel integration for putting a sold demo site into production.

On a closed sale we attach the client's domain to the demo-host production
project and (optionally) trigger a rebuild via a Vercel Deploy Hook. The domain
must already exist on the Vercel account/team — automatic domain *purchase* at a
registrar is out of scope.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from core.config import settings
from models.demo_site import DemoSite

logger = logging.getLogger(__name__)


class VercelService:
    """Thin client over the Vercel REST API for domain attachment + deploys."""

    def __init__(self) -> None:
        self._token: Optional[str] = settings.vercel_token
        self._team_id: Optional[str] = settings.vercel_team_id
        self._project_id: Optional[str] = settings.vercel_demo_host_project_id
        self._deploy_hook_url: Optional[str] = settings.vercel_deploy_hook_url
        self._base_url: str = "https://api.vercel.com"

    @property
    def is_configured(self) -> bool:
        """True when a Vercel token is available."""
        return bool(self._token and self._token.strip())

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}

    def _params(self) -> dict[str, str]:
        return {"teamId": self._team_id} if self._team_id else {}

    async def attach_domain(self, domain: str) -> dict[str, Any]:
        """
        Attach a domain to the production project.

        Returns:
            Vercel API response (includes verification records when the domain is not yet verified). Raises on HTTP error.
        """
        if not self.is_configured or not self._project_id:
            raise ValueError("Vercel n'est pas configuré (VERCEL_TOKEN / VERCEL_DEMO_HOST_PROJECT_ID).")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base_url}/v10/projects/{self._project_id}/domains",
                headers=self._headers(),
                params=self._params(),
                json={"name": domain},
            )
            # 409 = domain already attached → treat as success
            if response.status_code == 409:
                return {"name": domain, "alreadyAttached": True}
            response.raise_for_status()
            return response.json()

    async def trigger_deploy(self) -> Optional[str]:
        """Trigger a production rebuild via the configured Deploy Hook. Returns a job id."""
        if not self._deploy_hook_url:
            return None
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self._deploy_hook_url)
            response.raise_for_status()
            try:
                data = response.json()
                job = data.get("job") if isinstance(data, dict) else None
                return str(job.get("id")) if isinstance(job, dict) and job.get("id") else None
            except Exception:  # noqa: BLE001
                return None

    async def deploy_demo_site(
        self, db: Session, demo_site: DemoSite, *, domain: Optional[str] = None
    ) -> DemoSite:
        """
        Put a demo site live in production.

        Attaches ``domain`` (when provided) to the prod project, triggers a
        rebuild, and records the production URL on the demo site. Best-effort:
        when Vercel is not configured, records the intended prod URL only.
        """
        target_domain = (domain or "").strip() or None
        prod_url = f"https://{target_domain}" if target_domain else demo_site.demo_url

        if self.is_configured and target_domain and self._project_id:
            try:
                await self.attach_domain(target_domain)
            except Exception:  # noqa: BLE001
                logger.exception("Vercel domain attach failed for %s", target_domain)
                raise
        elif not self.is_configured:
            logger.warning("Vercel not configured — recording prod URL only for slug=%s", demo_site.slug)

        deployment_id: Optional[str] = None
        try:
            deployment_id = await self.trigger_deploy()
        except Exception:  # noqa: BLE001
            logger.warning("Vercel deploy hook failed for slug=%s", demo_site.slug, exc_info=True)

        if deployment_id:
            demo_site.vercel_deployment_id = deployment_id
        if prod_url:
            demo_site.vercel_deployment_url = prod_url
        db.commit()
        db.refresh(demo_site)
        return demo_site


vercel_service = VercelService()
