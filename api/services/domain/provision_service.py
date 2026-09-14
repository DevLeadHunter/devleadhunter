"""Provision a client domain end to end: register it, then point its DNS once it is active.

One operator action ("Réserver et mettre en ligne") maps to :meth:`provision`. Registration is
async at OVH, so the DNS pointing runs in a background task that waits for the zone to exist, then
sets the apex ``A`` record to the Vercel demo-host. Best-effort — every step is logged to the
activity feed so the operator can follow the go-live from the monitoring page.
"""

from __future__ import annotations

import asyncio
import logging

from services.activity_log_service import (
    CATEGORY_SALE,
    STATUS_ERROR,
    STATUS_INFO,
    STATUS_SUCCESS,
    activity_log_service,
)
from services.domain.ovh_provider import DomainProviderError, ovh_domain_provider
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

# OVH activates a .fr within minutes; poll its new zone this often, for this long, before giving up.
_POLL_INTERVAL_SECONDS = 30
_POLL_ATTEMPTS = 40  # ~20 minutes


class DomainProvisionService:
    """Register a domain and bring it online (DNS → Vercel) in one operator action."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()  # keep finalize tasks alive against GC

    async def provision(self, domain: str, *, user_id: int | None = None) -> dict[str, object]:
        """Order the domain now and schedule its DNS pointing once OVH activates it.

        Args:
            domain: The full ``.fr`` domain to register and bring online.
            user_id: The operator, for the activity log.

        Returns:
            The OVH order payload (``orderId`` / ``url``).

        Raises:
            DomainProviderError: When OVH is not configured or the order fails.
        """
        order = await ovh_domain_provider.register(domain)
        activity_log_service.record(
            category=CATEGORY_SALE,
            action="domain_registered",
            status=STATUS_INFO,
            title=f"Domaine commandé · {domain} — mise en ligne en cours",
            user_id=user_id,
            entity_type="domain",
        )
        if user_id is not None:
            await notification_service.notify_go_live_step(
                user_id=user_id,
                title=f"🌐 {domain}",
                body="Domaine commandé chez OVH — mise en ligne en cours",
                tag=f"go-live-{domain}",
            )
        task = asyncio.create_task(self._finalize(domain, user_id))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return order

    async def _finalize(self, domain: str, user_id: int | None) -> None:
        """Bring the domain online: attach it to Vercel, then point the apex DNS once the zone exists."""
        from services.vercel_service import vercel_service

        try:
            # Tell Vercel « this domain → the demo-host project » so it routes + issues SSL once the DNS lands.
            try:
                await vercel_service.attach_domain(domain)
                await vercel_service.attach_domain(f"www.{domain}")
            except Exception as exc:
                # Best-effort: an unconfigured or transient Vercel must not stop the DNS pointing.
                logger.warning("Vercel attach for %s failed: %s", domain, exc)
            for _ in range(_POLL_ATTEMPTS):
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
                if await ovh_domain_provider.zone_ready(domain):
                    await ovh_domain_provider.point_to_vercel(domain)
                    activity_log_service.record(
                        category=CATEGORY_SALE,
                        action="domain_live",
                        status=STATUS_SUCCESS,
                        title=f"Domaine en ligne · {domain} (DNS → Vercel)",
                        user_id=user_id,
                        entity_type="domain",
                    )
                    if user_id is not None:
                        await notification_service.notify_go_live_step(
                            user_id=user_id,
                            title=f"🌐 {domain}",
                            body="DNS pointés vers le site — accessible dans quelques minutes (SSL en cours)",
                            level="success",
                            tag=f"go-live-{domain}",
                        )
                    return
            activity_log_service.record(
                category=CATEGORY_SALE,
                action="domain_provision_timeout",
                status=STATUS_ERROR,
                title=f"Domaine {domain} : DNS non pointé (zone pas prête à temps)",
                user_id=user_id,
                entity_type="domain",
            )
            if user_id is not None:
                await notification_service.notify_go_live_step(
                    user_id=user_id,
                    title=f"⏳ {domain}",
                    body="OVH n'a pas fini de livrer le domaine — l'outil re-pointera les DNS automatiquement",
                    level="warning",
                    tag=f"go-live-{domain}",
                )
        except DomainProviderError as exc:
            logger.warning("Domain provision failed for %s: %s", domain, exc)
            activity_log_service.record(
                category=CATEGORY_SALE,
                action="domain_provision_failed",
                status=STATUS_ERROR,
                title=f"Échec mise en ligne du domaine {domain}",
                detail=str(exc),
                user_id=user_id,
                entity_type="domain",
            )
            if user_id is not None:
                await notification_service.notify_go_live_step(
                    user_id=user_id,
                    title=f"❌ {domain}",
                    body=f"Échec de la mise en ligne du domaine : {str(exc)[:140]}",
                    level="error",
                    tag=f"go-live-{domain}",
                )


domain_provision_service = DomainProvisionService()
