"""
Contract between the DevLeadHunter core and its optional product modules.

The websites module is the core itself. Every other sellable module (the AI receptionist, the Apple Wallet loyalty
cards) lives in its own repository and is installed as a Python distribution that declares an entry point in the
``devleadhunter.product_modules`` group. The core never imports a module: it discovers the installed ones through
:mod:`core.product_modules.registry` and calls the hooks of :class:`ProductModule`. Every hook has a neutral
default, so a module only overrides what it plugs into.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from fastapi import APIRouter, FastAPI
    from sqlalchemy.orm import Session

    from core.product_modules.campaign_offer import CampaignOffer
    from core.product_modules.sidecar import SidecarVideoBuildApi
    from schemas.notification import DemoEventIn

ENTRY_POINT_GROUP: str = "devleadhunter.product_modules"
WEBSITES_MODULE_KEY: str = "websites"
WEBSITES_MODULE_LABEL: str = "Sites web"

BackgroundLoop = Callable[[], Coroutine[Any, Any, None]]


@dataclass(frozen=True)
class StorageKind:
    """
    A category of the bucket's objects that a module stores, read from the key prefix.

    Attributes:
        kind: The category, as the storage page files and filters it (« assistant_video »).
        prefix: The key prefix of its objects, slash included where a sibling prefix shares its start.
        label: How the storage page names one object of it (« Vidéo (réceptionniste) »).
        filter_label: How the storage page's filter names them all (« Vidéos réceptionniste »).
        media: What the page previews: ``video``, ``image`` or ``file``.
        is_demo_deliverable: True when the object lives and dies with one of the module's demos (its video and
            thumbnail), its slug being the key's file name.
        is_prospection_video: True for the module's prospection videos (``{prefix}{slug}.mp4``), which the storage
            health check compares with the module's ``ready_video_slugs``.
        retention_days: Days an object of this kind is kept after its upload, when the module purges it on a clock.
    """

    kind: str
    prefix: str
    label: str
    filter_label: str
    media: str
    is_demo_deliverable: bool = False
    is_prospection_video: bool = False
    retention_days: int | None = None


@dataclass(frozen=True)
class DeliverableExpiry:
    """
    When a demo deliverable of the bucket expires, decided by the module from its demo's lifecycle.

    Attributes:
        is_expired: The demo is gone or past its date: the file may be purged.
        expires_in_days: Days left, None when expired, permanent (sold) or not started.
        ttl_pending: The demo's countdown has not started yet (its link was never sent).
        name: The business the demo belongs to, for the storage page.
    """

    is_expired: bool
    expires_in_days: int | None
    ttl_pending: bool
    name: str | None = None


class ProductModule:
    """
    One optional product module, as the core sees it.

    Subclasses set the class attributes and override the hooks they need.

    Attributes:
        key: Stored in the database (module switches, contact locks, presenter takes): it never changes once the
            module has shipped.
        label: The module's name on the admin page and in the module switcher.
        description: One sentence on the admin page.
        enabled_by_default: The switch while the super admin has stored none.
        notification_tag: The prefix of the module's pushes on a phone (« 🤖 Assistant IA »).
        demo_beacon_prefix: The event prefix of the module's own demo pages (« assistant_video_ »), whose beacons
            the module handles.
    """

    key: ClassVar[str]
    label: ClassVar[str]
    description: ClassVar[str] = ""
    enabled_by_default: ClassVar[bool] = False
    notification_tag: ClassVar[str] = ""
    demo_beacon_prefix: ClassVar[str | None] = None

    def load(self) -> None:
        """Import the module's models so their tables join the core metadata, and configure its loggers."""

    def routers(self) -> list[APIRouter]:
        """
        The module's API routers, mounted under the API prefix in this order.

        They answer 404 while the module is switched off.
        """
        return []

    def background_loops(self) -> list[BackgroundLoop]:
        """
        The module's long-running loops.

        The core runs them only while the module is switched on: they start with the API, stop when the super admin
        switches the module off and start again when it is switched back on.
        """
        return []

    def migrations(self) -> list[tuple[str, str]]:
        """The module's tracked migrations, as (name, dotted module path), run in order after the core's."""
        return []

    def seed(self) -> None:
        """Seed the module's reference data (idempotent), after the core's seeders."""

    def campaign_offer(self) -> CampaignOffer | None:
        """What the module sells through the campaigns, or None when it sells nothing there."""
        return None

    def email_template_library(self) -> list[dict[str, object]]:
        """
        The module's cold emails, appended to the shared library by the seeder (matched by name, never rewritten).

        Each entry has the keys of the core library: ``name``, ``subject``, ``body_html``, ``category``, ``sort_order``.
        """
        return []

    async def handle_stripe_event(self, db: Session, event: dict[str, Any]) -> str | None:
        """
        Handle a Stripe webhook event that belongs to the module (its own subscriptions).

        Called whether the module is switched on or off, after the core's own orders and refunds: billing must stay
        in step with Stripe. An event of no concern to the module is left alone.

        Args:
            db: Active database session.
            event: The verified Stripe event.

        Returns:
            A short message when the module handled the event, None when it is not the module's.
        """
        return None

    async def handle_demo_beacon(self, db: Session, payload: DemoEventIn) -> None:
        """
        React to a beacon of the module's own demo pages (its event starts with ``demo_beacon_prefix``).

        Only called while the module is switched on.

        Args:
            db: Active database session.
            payload: The beaconed event.
        """

    def demo_slugs(self, db: Session, *, user_id: int) -> list[tuple[str, int | None]]:
        """
        The user's demos of this module, as (slug, prospect id), which the visit tracking counts with the sites'.

        Args:
            db: Active database session.
            user_id: The owner.

        Returns:
            One pair per live demo.
        """
        return []

    def is_demo_slug_taken(self, db: Session, slug: str, *, prospect_id: int | None) -> bool:
        """
        Whether a demo of this module, of another prospect, holds the slug: every module's pages share the demo host.

        Args:
            db: Active database session.
            slug: The slug a new demo would take.
            prospect_id: The prospect of the new demo (a demo of the same prospect may share it).

        Returns:
            True when the slug is taken.
        """
        return False

    def tracking_event_labels(self) -> dict[str, str]:
        """The French label of each tracked event of the module's pages, for the prospect timeline."""
        return {}

    def lead_score_event_aliases(self) -> dict[str, str]:
        """Module events that score as a site event (« assistant_video_play » scores as « demo_video_play »)."""
        return {}

    def posthog_event_names(self) -> tuple[str, ...]:
        """The module's PostHog events that the behaviour queries read along with the sites'."""
        return ()

    def storage_kinds(self) -> list[StorageKind]:
        """The categories of the bucket's objects the module stores, matched in this order before the core's."""
        return []

    def deliverable_expiries(self, db: Session, slugs: set[str], now: datetime) -> dict[str, DeliverableExpiry]:
        """
        When the module's demo deliverables of these slugs expire (``StorageKind.is_demo_deliverable``).

        Args:
            db: Active database session.
            slugs: The slugs read from the keys of the deliverables.
            now: The current instant (aware UTC).

        Returns:
            The expiry of each slug whose demo still exists; a missing slug reads as a leftover to purge.
        """
        return {}

    def ready_video_slugs(self, db: Session) -> set[str]:
        """
        The slugs of the module's demos whose prospection video is ready (and so stored in the bucket).

        Args:
            db: Active database session.

        Returns:
            The slugs, for the storage health check.
        """
        return set()

    def register_sidecar_routes(self, app: FastAPI, video_builds: SidecarVideoBuildApi) -> None:
        """
        Add the module's routes to the desktop sidecar, the local API the Windows app runs on the owner's PC.

        Args:
            app: The sidecar's application.
            video_builds: The sidecar's video build machinery, for a module with a prospection video of its own.
        """
