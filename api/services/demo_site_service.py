"""Business logic for demo site generation and lifecycle."""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from enums.acquisition import AcquisitionItemStep, AcquisitionRunStatus
from enums.demo_site_status import DemoSiteStatus
from enums.storyblok_collaborator_status import StoryblokCollaboratorStatus
from models.acquisition_run import AcquisitionRun
from models.acquisition_run_item import AcquisitionRunItem
from models.demo_site import DemoSite
from models.order import Order
from models.prospect_db import ProspectDB
from models.sms_message import SmsMessage
from models.sms_suppression import SmsSuppression
from models.user import User
from services.activity_log_service import (
    CATEGORY_DEMO_SITE,
    STATUS_ERROR,
    STATUS_INFO,
    STATUS_SUCCESS,
    STATUS_WARNING,
    activity_log_service,
)
from services.brand_color_service import brand_color_service
from services.demo_site_verification_service import (
    DemoSiteVerificationResult,
    demo_site_verification_service,
)
from services.enrichment_service import enrichment_service
from services.sms.phone_normalizer import is_mobile_fr, to_e164_fr
from services.storyblok_service import (
    StoryblokProvisionError,
    StoryblokProvisionResult,
    storyblok_service,
)
from services.templates import registry as template_registry
from services.templates.site_content import from_storyblok_site_content, usable_site_photos

logger = logging.getLogger(__name__)

_storyblok_swap_locks: dict[int, asyncio.Lock] = {}

# Sentinel expiry while the demo link has not been emailed yet (TTL not started).
_PENDING_TTL_EXPIRES: datetime = datetime(2099, 12, 31, 23, 59, 59, tzinfo=UTC)

AVAILABLE_TEMPLATES: list[dict[str, object]] = template_registry.AVAILABLE_TEMPLATES


def reenqueue_campaigns_after_demo_ready(db: Session, prospect_id: int | None, user_id: int) -> None:
    """
    Best-effort: pull a prospect into its active campaigns once its demo site is live.

    A prospect added to a launched campaign before its demo existed gets no queue row (the J1 would
    ship an empty ``{lien_demo}``), and nothing reconsiders it. When the demo goes live the prospect
    can finally be emailed, so the per-prospect enqueue re-runs here and the pending sends are re-dated
    to the table order. Mirrors ``reenqueue_campaigns_after_video_ready``. Never raises: a queue hiccup
    must not undo a generated site.

    Args:
        db: Active database session.
        prospect_id: The prospect whose demo just became live (None for a site with no prospect).
        user_id: Owner of the prospect's campaigns.
    """
    if not prospect_id:
        return
    try:
        from services.campaign_queue_service import CampaignQueueService

        added: int = CampaignQueueService(db).enqueue_ready_prospect(prospect_id, user_id)
        if added:
            logger.info(
                "[Demo] Demo live for prospect %d — auto-enqueued into %d active campaign send(s)", prospect_id, added
            )
    except Exception:
        logger.warning("[Demo] Auto re-enqueue after demo ready failed for prospect %s", prospect_id, exc_info=True)


class DemoSiteService:
    """Orchestrates demo site creation, listing, and cleanup."""

    def list_templates(self) -> list[dict[str, object]]:
        """Return templates available in the stepper."""
        return AVAILABLE_TEMPLATES

    def _theme_from_content(self, content_json: dict | None) -> dict[str, str] | None:
        """Extract a theme palette from stored content JSON."""
        if not content_json:
            return None
        theme = content_json.get("theme")
        if isinstance(theme, dict):
            return {
                "primary": str(theme.get("primary", "#0284c7")),
                "secondary": str(theme.get("secondary", "#0f172a")),
                "accent": str(theme.get("accent", "#f59e0b")),
            }
        return None

    def _default_theme_for_template(self, template_id: str) -> dict[str, str]:
        """Return default theme colors for a template id."""
        for template in AVAILABLE_TEMPLATES:
            if template["id"] == template_id:
                default_theme = template.get("default_theme")
                if isinstance(default_theme, dict):
                    return {
                        "primary": str(default_theme.get("primary", "#0284c7")),
                        "secondary": str(default_theme.get("secondary", "#0f172a")),
                        "accent": str(default_theme.get("accent", "#f59e0b")),
                    }
        return {"primary": "#0284c7", "secondary": "#0f172a", "accent": "#f59e0b"}

    def build_preview_content(
        self,
        *,
        business_name: str,
        template_id: str,
        phone: str | None = None,
        email: str | None = None,
        city: str | None = None,
        description: str | None = None,
        theme: dict[str, str] | None = None,
    ) -> dict:
        """Build content JSON for client-side preview without provisioning."""
        palette = theme or self._default_theme_for_template(template_id)
        return storyblok_service.build_content_json(
            business_name=business_name,
            phone=phone,
            email=email,
            city=city,
            description=description,
            template_id=template_id,
            theme=palette,
        )

    def _enrichment_dict_for_site(self, db: Session, demo_site: DemoSite) -> dict | None:
        """Return the prospect's enrichment data for a demo site, when linked."""
        prospect_id: int | None = getattr(demo_site, "prospect_id", None)
        if not prospect_id:
            return None
        record = enrichment_service.get_for_prospect(db, demo_site.user_id, prospect_id)
        prospect = enrichment_service.get_prospect_for_user(db, demo_site.user_id, prospect_id)
        return self._with_prospect_location(enrichment_service.to_dict(record), prospect)

    async def _resolve_enrichment_for_creation(self, db: Session, user_id: int, prospect_id: int | None) -> dict | None:
        """Fetch (and run on demand if missing) the prospect enrichment before generation."""
        if not prospect_id:
            return None
        try:
            prospect = enrichment_service.get_prospect_for_user(db, user_id, prospect_id)
            if not prospect:
                return None
            record = await enrichment_service.ensure_enriched(db, user_id, prospect)
            return self._with_prospect_location(enrichment_service.to_dict(record), prospect)
        except Exception:
            logger.warning("Enrichment resolution failed for prospect_id=%s", prospect_id, exc_info=True)
            return None

    _MAPS_COORDS_RE = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")

    @classmethod
    def _coords_from_maps_url(cls, url: object) -> tuple[float, float] | None:
        """Extract ``(lat, lng)`` from a Google Maps URL's ``@lat,lng`` segment, or None.

        A scraped place URL embeds its coordinates (``…/@47.39,0.68,17z/…``); these centre the
        "nous trouver" map on the business instead of the template's default city.
        """
        if not isinstance(url, str):
            return None
        match = cls._MAPS_COORDS_RE.search(url)
        if not match:
            return None
        return float(match.group(1)), float(match.group(2))

    @classmethod
    def _with_prospect_location(cls, enrichment: dict | None, prospect: object) -> dict | None:
        """Fold the prospect's real street address + map coordinates into the enrichment dict.

        The street address and Google Maps URL live on the prospect, not the enrichment record,
        yet the templates need them for the contact block and the map. Returns an augmented copy
        (the record's dict is never mutated); may return a fresh dict even without enrichment so the
        location still reaches generation.
        """
        if prospect is None:
            return enrichment
        data: dict = dict(enrichment or {})
        address = getattr(prospect, "address", None)
        if isinstance(address, str) and address.strip():
            data["address"] = address.strip()
        coords = cls._coords_from_maps_url(getattr(prospect, "google_maps_url", None))
        if coords:
            data["lat"], data["lng"] = coords
        return data or None

    def _build_content_for_site(self, db: Session, demo_site: DemoSite) -> dict:
        """Build Storyblok content JSON from the demo site record."""
        return self._build_content_for_site_with_theme(db, demo_site, theme=None)

    def _build_content_for_site_with_theme(
        self, db: Session, demo_site: DemoSite, theme: dict[str, str] | None = None
    ) -> dict:
        """Build Storyblok content JSON from the demo site record (with enrichment)."""
        enrichment = self._enrichment_dict_for_site(db, demo_site)
        # A user-curated photo placement overrides the scraped order: fold it into the photo pool so
        # the shared mapping ([0]→hero, [1]→about, [2:]→gallery) produces the arrangement they chose,
        # with photos added to the prospect since the last save appended to the gallery.
        if isinstance(enrichment, dict) and isinstance(demo_site.image_order, list) and demo_site.image_order:
            pool: list[str] = usable_site_photos(enrichment)
            enrichment = {
                **enrichment,
                "photos": self._effective_photos(pool, demo_site.image_order, demo_site.image_pool_snapshot),
            }
        palette = (
            theme
            or self._theme_from_content(demo_site.content_json)
            or self._default_theme_for_template(demo_site.template_id)
        )
        palette = self._apply_brand_color(
            palette, demo_site.template_id, enrichment, use_brand_color=demo_site.use_brand_color
        )
        return storyblok_service.build_content_json(
            business_name=demo_site.business_name,
            phone=demo_site.phone,
            email=demo_site.email,
            city=demo_site.city,
            description=demo_site.description,
            template_id=demo_site.template_id,
            theme=palette,
            enrichment=enrichment,
        )

    @staticmethod
    def _apply_brand_color(
        palette: dict[str, str],
        template_id: str,
        enrichment: dict | None,
        *,
        use_brand_color: bool = True,
    ) -> dict[str, str]:
        """Override the template's action colour with the prospect's brand colour (from its logo), if usable.

        A logo that yields no vivid colour leaves the template palette untouched, so the DA is never degraded.
        When ``use_brand_color`` is False the site keeps the template's default action colour (the client
        preferred it to the logo colour) — the palette is returned unchanged.

        Args:
            palette: The base palette (template default or stored theme).
            template_id: Template whose action-colour key receives the brand colour.
            enrichment: The prospect enrichment dict (holds ``logo_url``), or None.
            use_brand_color: Whether to pull the action colour from the logo (True) or keep the template's.

        Returns:
            A new palette with the action colour overridden, or the base palette unchanged.
        """
        if not use_brand_color:
            return palette
        brand = brand_color_service.extract_brand_color((enrichment or {}).get("logo_url"))
        if not brand:
            return palette
        return {**palette, template_registry.brand_color_key(template_id): brand}

    def slugify(self, value: str) -> str:
        """Convert a business name into a URL-safe slug."""
        normalized: str = unicodedata.normalize("NFKD", value)
        ascii_value: str = normalized.encode("ascii", "ignore").decode("ascii")
        slug: str = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
        return slug or "demo-site"

    def unique_slug(self, db: Session, business_name: str) -> str:
        """Generate a unique slug for a new demo site."""
        base_slug: str = self.slugify(business_name)[:80]
        candidate: str = base_slug
        suffix: int = 1

        while db.query(DemoSite).filter(DemoSite.slug == candidate).first() is not None:
            suffix += 1
            candidate = f"{base_slug}-{suffix}"

        return candidate

    def demo_url_for_slug(self, slug: str) -> str:
        """Build the public demo URL for a slug."""
        base: str = settings.demo_host_base_url.rstrip("/")
        return f"{base}/{slug}"

    def _apply_verification(self, demo_site: DemoSite, verification: DemoSiteVerificationResult) -> None:
        """Persist verification outcome and set the lifecycle status."""
        demo_site.demo_url_live = verification.demo_url_live
        demo_site.local_demo_url = verification.local_demo_url if verification.local_demo_url_live else None
        demo_site.verification_message = verification.message

        if not verification.public_api_ok:
            demo_site.status = DemoSiteStatus.FAILED.value
            demo_site.error_message = verification.message
            return

        if verification.demo_url_live:
            demo_site.status = DemoSiteStatus.ACTIVE.value
            demo_site.error_message = None
            return

        if verification.local_demo_url_live and not settings.is_production:
            demo_site.status = DemoSiteStatus.ACTIVE.value
            demo_site.demo_url_live = True
            demo_site.error_message = None
            return

        demo_site.status = DemoSiteStatus.UNAVAILABLE.value
        demo_site.error_message = verification.message

    async def verify_and_update(self, db: Session, demo_site: DemoSite) -> DemoSite:
        """Re-run HTTP checks and update the demo site record."""
        verification: DemoSiteVerificationResult = await demo_site_verification_service.verify(db, demo_site)
        self._apply_verification(demo_site, verification)
        db.commit()
        db.refresh(demo_site)
        return demo_site

    def set_reviewed(self, db: Session, demo_site: DemoSite, reviewed: bool) -> DemoSite:
        """Record (or clear) the operator's manual "good to send" sign-off for a site.

        This is the review surfaced in the campaign forecast, kept separate from the automated
        live-URL check. ``reviewed=True`` stamps the current UTC instant; ``False`` clears it.

        Args:
            db: Active database session.
            demo_site: The site to mark.
            reviewed: True to sign off, False to reset.

        Returns:
            The refreshed demo site.
        """
        demo_site.site_reviewed_at = datetime.now(UTC).replace(tzinfo=None) if reviewed else None
        db.commit()
        db.refresh(demo_site)
        return demo_site

    async def regenerate_demo_site(self, db: Session, demo_site: DemoSite) -> DemoSite:
        """
        Rebuild demo site content from stored fields and sync to Storyblok.

        Updates ``content_json`` in the database and publishes the home story
        when a Storyblok space exists, then re-runs URL verification.
        """
        content_json: dict = self._build_content_for_site(db, demo_site)
        demo_site.content_json = content_json
        demo_site.demo_url = demo_site.demo_url or self.demo_url_for_slug(demo_site.slug)
        demo_site.vercel_deployment_url = demo_site.demo_url
        demo_site.error_message = None
        # A rebuilt site is no longer the one the operator reviewed: clear the sign-off so the
        # campaign forecast asks for a fresh look before the next send.
        demo_site.site_reviewed_at = None

        if demo_site.storyblok_space_id:
            try:
                await storyblok_service.configure_preview_url(
                    demo_site.storyblok_space_id,
                    demo_site.demo_url or self.demo_url_for_slug(demo_site.slug),
                )
                await storyblok_service.update_home_story_content(
                    demo_site.storyblok_space_id,
                    content_json,
                    demo_site.template_id,
                )
            except Exception as exc:
                # Sync CMS en échec : on garde le content_json rebâti, la vérification statue.
                logger.warning(
                    "Storyblok content sync failed for slug=%s; keeping content_json (%s)", demo_site.slug, exc
                )

        verification: DemoSiteVerificationResult = await demo_site_verification_service.verify(db, demo_site)
        self._apply_verification(demo_site, verification)
        db.commit()
        db.refresh(demo_site)
        self._log_generation(demo_site, demo_site.user_id, action="demo_site_regenerated")
        return demo_site

    async def update_demo_site(
        self,
        db: Session,
        demo_site: DemoSite,
        *,
        business_name: str | None = None,
        template_id: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        city: str | None = None,
        description: str | None = None,
        theme: dict[str, str] | None = None,
        use_brand_color: bool | None = None,
        image_order: list[str] | None = None,
    ) -> DemoSite:
        """Update demo site fields and regenerate its published content.

        ``image_order`` uses the same semantics as :meth:`set_site_images` (cleaned against the
        pool, default order stored as NULL) so one PATCH can save every pending edit — template,
        colours and photo placement — with a single regeneration.
        """
        pending_theme = theme
        if use_brand_color is not None:
            demo_site.use_brand_color = use_brand_color
        if image_order is not None:
            pool: list[str] = usable_site_photos(self._enrichment_dict_for_site(db, demo_site))
            cleaned: list[str] = self._clean_image_order(image_order, pool)
            demo_site.image_order = cleaned if cleaned and cleaned != pool else None
            # Record the pool seen at save time so photos added later are detected as new, not re-shown.
            demo_site.image_pool_snapshot = list(pool)
        if business_name is not None:
            demo_site.business_name = business_name
        if template_id is not None:
            demo_site.template_id = template_id
        if phone is not None:
            demo_site.phone = phone or None
        if email is not None:
            if not str(email).strip():
                raise ValueError("Client email cannot be empty.")
            demo_site.email = str(email).strip()
            demo_site.storyblok_login_email = demo_site.email
        if city is not None:
            demo_site.city = city or None
        if description is not None:
            demo_site.description = description or None

        if pending_theme is not None:
            existing_content = dict(demo_site.content_json or {})
            existing_content["theme"] = pending_theme
            demo_site.content_json = existing_content

        return await self.regenerate_demo_site(db, demo_site)

    def get_site_images(self, db: Session, demo_site: DemoSite) -> dict[str, list[str]]:
        """Return the site's photo pool and its current placement order.

        ``pool`` is every usable prospect photo (what could go on the site); ``order`` is the current
        arrangement ([0]→hero, [1]→about, [2:]→gallery), i.e. the saved override cleaned to the pool,
        or the default scraped order when none is saved. Photos in ``pool`` but not in ``order`` are
        unused. Empty pool means the site has no editable photos (no prospect, or none usable).
        """
        pool: list[str] = usable_site_photos(self._enrichment_dict_for_site(db, demo_site))
        order: list[str] = self._effective_photos(pool, demo_site.image_order, demo_site.image_pool_snapshot)
        return {"pool": pool, "order": order}

    async def set_site_images(self, db: Session, demo_site: DemoSite, order: list[str]) -> DemoSite:
        """Persist a user-curated photo order and regenerate the site so the new placement goes live.

        The order is cleaned against the current pool (unknown or duplicate URLs dropped); an order
        that matches the default is stored as NULL so the site keeps following the scraped order.
        """
        pool: list[str] = usable_site_photos(self._enrichment_dict_for_site(db, demo_site))
        cleaned: list[str] = self._clean_image_order(order, pool)
        demo_site.image_order = cleaned if cleaned and cleaned != pool else None
        # Record the pool seen at save time so photos added later are detected as new, not re-shown.
        demo_site.image_pool_snapshot = list(pool)
        return await self.regenerate_demo_site(db, demo_site)

    @staticmethod
    def _clean_image_order(order: object, pool: list[str]) -> list[str]:
        """Keep only pool URLs, first occurrence, in the given order (drops unknown/duplicate URLs)."""
        if not isinstance(order, list):
            return []
        allowed: set[str] = set(pool)
        seen: set[str] = set()
        cleaned: list[str] = []
        for url in order:
            if isinstance(url, str) and url in allowed and url not in seen:
                seen.add(url)
                cleaned.append(url)
        return cleaned

    @classmethod
    def _effective_photos(cls, pool: list[str], image_order: object, snapshot: object) -> list[str]:
        """The site's ordered photos: curated placement kept, genuinely-new photos appended.

        ``image_order`` is the operator's placement; ``snapshot`` is the pool known when they last saved
        it. A pool photo absent from both is **new** → appended to the gallery so photos added to the
        prospect show up; one present in ``snapshot`` but dropped from the order was **removed on
        purpose** → stays hidden. No curation (empty order) means the default full pool. A legacy site
        with no snapshot keeps its exact order until the next save records one (so nothing reappears).

        Args:
            pool: Every usable prospect photo, current.
            image_order: The saved placement (list of URLs), or None.
            snapshot: The pool known at the last save (list of URLs), or None (legacy).

        Returns:
            The ordered photo list to render.
        """
        order: list[str] = cls._clean_image_order(image_order, pool)
        if not order:
            return list(pool)
        if not isinstance(snapshot, list):
            return order
        decided: set[str] = set(snapshot) | set(order)
        extras: list[str] = [url for url in pool if url not in decided]
        return order + extras

    async def invite_client_to_cms(self, db: Session, demo_site: DemoSite) -> DemoSite:
        """Send a Storyblok CMS invitation to the demo site client email."""
        if demo_site.storyblok_invite_sent:
            raise ValueError("The client has already been invited to Storyblok.")

        email: str | None = demo_site.email or demo_site.storyblok_login_email
        if not email or not email.strip():
            raise ValueError("Client email is required to send a Storyblok invitation.")

        space_id: int | None = demo_site.storyblok_space_id
        if not space_id:
            space_id = await storyblok_service.resolve_space_id(
                space_id=None,
                editor_url=demo_site.storyblok_editor_url,
                business_name=demo_site.business_name,
                slug=demo_site.slug,
            )
            if space_id:
                demo_site.storyblok_space_id = space_id

        if not space_id:
            raise ValueError("This demo site has no Storyblok space.")

        await storyblok_service.invite_collaborator(space_id, email.strip())
        demo_site.storyblok_login_email = email.strip()
        demo_site.storyblok_invite_sent = True
        demo_site.storyblok_collaborator_status = StoryblokCollaboratorStatus.PENDING.value
        db.commit()
        db.refresh(demo_site)
        return demo_site

    async def refresh_cms_collaborator_status(self, db: Session, demo_site: DemoSite) -> DemoSite:
        """Re-read whether the client has joined the Storyblok space and persist the result.

        Cheap short-circuit: an uninvited site is ``not_invited`` without any API call. Otherwise the
        live status is fetched best-effort — a transient ``unknown`` never overwrites a known state,
        and the first observed ``joined`` stamps ``storyblok_joined_at``.
        """
        if not demo_site.storyblok_invite_sent:
            if demo_site.storyblok_collaborator_status != StoryblokCollaboratorStatus.NOT_INVITED.value:
                demo_site.storyblok_collaborator_status = StoryblokCollaboratorStatus.NOT_INVITED.value
                db.commit()
                db.refresh(demo_site)
            return demo_site

        space_id: int | None = demo_site.storyblok_space_id
        if not space_id:
            space_id = await storyblok_service.resolve_space_id(
                space_id=None,
                editor_url=demo_site.storyblok_editor_url,
                business_name=demo_site.business_name,
                slug=demo_site.slug,
            )
            if space_id:
                demo_site.storyblok_space_id = space_id
        if not space_id:
            return demo_site

        email: str | None = demo_site.email or demo_site.storyblok_login_email
        if not email or not email.strip():
            return demo_site

        status: str = await storyblok_service.get_collaborator_status(space_id, email.strip())
        # A transient read failure must not erase a state we already trust.
        if status == StoryblokCollaboratorStatus.UNKNOWN.value:
            return demo_site
        # The invite was sent (guard above), so never downgrade to "not_invited": a pending
        # invitation the collaborators list doesn't surface (or an unmatched email shape) stays pending.
        if status == StoryblokCollaboratorStatus.NOT_INVITED.value:
            status = StoryblokCollaboratorStatus.PENDING.value

        demo_site.storyblok_collaborator_status = status
        if status == StoryblokCollaboratorStatus.JOINED.value:
            if demo_site.storyblok_joined_at is None:
                demo_site.storyblok_joined_at = datetime.now(UTC)
        else:
            # Keep the stamp consistent if a client is ever read back as not-yet-joined.
            demo_site.storyblok_joined_at = None
        db.commit()
        db.refresh(demo_site)
        return demo_site

    async def create_demo_site(
        self,
        db: Session,
        *,
        user: User,
        business_name: str,
        template_id: str,
        phone: str | None,
        email: str | None,
        city: str | None,
        description: str | None,
        invite_client_to_cms: bool = False,
        theme: dict[str, str] | None = None,
        prospect_id: int | None = None,
    ) -> DemoSite:
        """
        Create and provision a demo site for the authenticated user.

        Args:
            db: SQLAlchemy session.
            user: Owner account.
            prospect_id: Optional source prospect; its enrichment data (run on demand here if missing) is merged into the generated site content.

        Returns:
            Persisted demo site record in ACTIVE or FAILED status.
        """
        # A client email is only required to invite them to the CMS right away (a sale); a
        # cold-SMS demo (prospect with a mobile but no email) generates without one, rendering
        # from content_json — the email is captured later at the sale.
        normalized_email: str | None = email.strip() if email and email.strip() else None
        if invite_client_to_cms and not normalized_email:
            raise ValueError("Client email is required to invite them to the CMS.")

        slug: str = self.unique_slug(db, business_name)
        expires_at: datetime = self._pending_ttl_expires_at()

        demo_site: DemoSite = DemoSite(
            user_id=user.id,
            prospect_id=prospect_id,
            slug=slug,
            template_id=template_id,
            business_name=business_name,
            phone=phone,
            email=normalized_email,
            city=city,
            description=description,
            status=DemoSiteStatus.PROVISIONING.value,
            expires_at=expires_at,
        )
        db.add(demo_site)
        db.commit()
        db.refresh(demo_site)

        enrichment_dict: dict | None = await self._resolve_enrichment_for_creation(db, user.id, prospect_id)
        # Personalise the action colour from the prospect's logo at first generation, not only on regenerate.
        palette: dict[str, str] = self._apply_brand_color(
            theme or self._default_theme_for_template(template_id), template_id, enrichment_dict
        )

        try:
            provision: StoryblokProvisionResult = await storyblok_service.provision_space(
                business_name=business_name,
                slug=slug,
                phone=phone,
                email=normalized_email or "",
                city=city,
                description=description,
                template_id=template_id,
                collaborator_email=normalized_email or "",
                preview_url=self.demo_url_for_slug(slug),
                invite_client=invite_client_to_cms,
                theme=palette,
                enrichment=enrichment_dict,
            )

            demo_site.storyblok_space_id = provision.space_id
            demo_site.storyblok_public_token = provision.public_token
            demo_site.storyblok_preview_token = provision.preview_token
            demo_site.storyblok_editor_url = provision.editor_url
            demo_site.storyblok_login_email = provision.login_email
            demo_site.storyblok_login_password = provision.login_password
            demo_site.storyblok_invite_sent = provision.invite_sent
            demo_site.storyblok_space_created_at = datetime.now(UTC)
            demo_site.content_json = provision.content_json
            demo_site.demo_url = self.demo_url_for_slug(slug)
            demo_site.vercel_deployment_url = demo_site.demo_url
            if provision.mock_mode:
                demo_site.verification_message = (
                    "Storyblok mock mode: configure STORYBLOK_MANAGEMENT_TOKEN for live CMS spaces."
                )

            db.commit()
            db.refresh(demo_site)

            verification: DemoSiteVerificationResult = await demo_site_verification_service.verify(db, demo_site)
            self._apply_verification(demo_site, verification)
            if provision.mock_mode and demo_site.status == DemoSiteStatus.ACTIVE.value:
                demo_site.verification_message = f"{verification.message} Storyblok mock mode is enabled."
        except StoryblokProvisionError as exc:
            # Échec Storyblok (ex. 401 fin d'essai) : le site se rend depuis content_json, on ne le condamne pas.
            logger.warning("Storyblok provisioning failed for slug=%s; serving demo from content_json (%s)", slug, exc)
            demo_site.storyblok_space_id = exc.space_id
            demo_site.storyblok_editor_url = exc.editor_url
            demo_site.content_json = exc.content_json or self._build_content_for_site(db, demo_site)
            demo_site.demo_url = demo_site.demo_url or self.demo_url_for_slug(slug)
            demo_site.vercel_deployment_url = demo_site.demo_url
            db.commit()
            db.refresh(demo_site)
            verification = await demo_site_verification_service.verify(db, demo_site)
            self._apply_verification(demo_site, verification)
        except Exception as exc:
            logger.exception("Demo site provisioning failed for slug=%s", slug)
            demo_site.content_json = demo_site.content_json or self._build_content_for_site(db, demo_site)
            demo_site.demo_url = demo_site.demo_url or self.demo_url_for_slug(slug)
            demo_site.vercel_deployment_url = demo_site.demo_url
            demo_site.status = DemoSiteStatus.FAILED.value
            demo_site.error_message = str(exc)
            demo_site.demo_url_live = False

        db.commit()
        db.refresh(demo_site)

        # Vidéo de prospection : génération auto en tâche de fond dès que le
        # site est actif, si l'utilisateur a configuré son clip webcam avec
        # l'option activée (couvre le tunnel unitaire, le bulk ET l'automation).
        if demo_site.status == DemoSiteStatus.ACTIVE.value:
            from services.demo_video_service import demo_video_service

            demo_video_service.maybe_start_auto_generation(db, demo_site, user.id)

        self._log_generation(demo_site, user.id, action="demo_site_generated")
        return demo_site

    def _log_generation(self, demo_site: DemoSite, user_id: int, *, action: str) -> None:
        """Record a demo-site generation/regeneration outcome in the activity feed.

        Args:
            demo_site: The persisted site, in its final status.
            user_id: Owner of the site.
            action: The activity action name (``demo_site_generated`` / ``demo_site_regenerated``).
        """
        if demo_site.status == DemoSiteStatus.ACTIVE.value:
            status, verb = STATUS_SUCCESS, "généré" if action == "demo_site_generated" else "régénéré"
        elif demo_site.status == DemoSiteStatus.FAILED.value:
            status, verb = STATUS_ERROR, "en échec"
        else:
            status, verb = STATUS_WARNING, "indisponible"
        activity_log_service.record(
            category=CATEGORY_DEMO_SITE,
            action=action,
            status=status,
            title=f"Site démo {verb} · {demo_site.business_name} ({demo_site.template_id})",
            detail=demo_site.error_message,
            user_id=user_id,
            entity_type="demo_site",
            entity_id=demo_site.id,
        )

    def list_for_user(self, db: Session, user_id: int) -> list[DemoSite]:
        """List demo sites owned by a user."""
        return (
            db.query(DemoSite)
            .filter(DemoSite.user_id == user_id, DemoSite.status != DemoSiteStatus.DELETED.value)
            .order_by(DemoSite.created_at.desc())
            .all()
        )

    def get_for_user(self, db: Session, user_id: int, demo_site_id: int) -> DemoSite | None:
        """Fetch a demo site owned by the given user."""
        return (
            db.query(DemoSite)
            .filter(
                DemoSite.id == demo_site_id,
                DemoSite.user_id == user_id,
                DemoSite.status != DemoSiteStatus.DELETED.value,
            )
            .first()
        )

    def get_public_by_slug(self, db: Session, slug: str) -> DemoSite | None:
        """
        Fetch a *demo* by slug for demo.dibodev.fr/{slug}.

        Served while the demo lives (pending/provisioning/active/unavailable…), so
        post-provisioning verification and the demo-host render work. A **sold**
        site (status DELIVERED), a deleted one, or a **dormant** one (EXPIRED, kept
        for a possible SMS relance) is taken down here (404) until it is sold or
        revived — a sold site then lives only on the client's own domain.
        """
        now: datetime = datetime.now(UTC)
        site: DemoSite | None = (
            db.query(DemoSite)
            .filter(
                DemoSite.slug == slug,
                DemoSite.status.notin_(
                    [DemoSiteStatus.DELETED.value, DemoSiteStatus.DELIVERED.value, DemoSiteStatus.EXPIRED.value]
                ),
                DemoSite.content_json.isnot(None),
            )
            .first()
        )
        if not site:
            return None

        if site.demo_link_sent_at is not None:
            expires_at: datetime = site.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)

            if expires_at <= now:
                return None

        return site

    @staticmethod
    def _pending_ttl_expires_at() -> datetime:
        """Expiry placeholder until the demo link is first emailed to the prospect."""
        return _PENDING_TTL_EXPIRES

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def ttl_is_pending(self, site: DemoSite) -> bool:
        """True when the 21-day countdown has not started yet (link not emailed)."""
        return site.demo_link_sent_at is None and site.status != DemoSiteStatus.DELIVERED.value

    def email_body_contains_demo_link(self, site: DemoSite, body_html: str) -> bool:
        """Whether rendered outreach HTML includes this site's public demo URL."""
        haystack: str = body_html or ""
        if site.slug and f"/{site.slug}" in haystack:
            return True
        return bool(site.demo_url and site.demo_url in haystack)

    def start_demo_ttl(self, db: Session, site: DemoSite, sent_at: datetime) -> bool:
        """
        Start (or leave unchanged) the demo TTL from the first email carrying the link.

        Returns:
            True when ``expires_at`` was set from this send.
        """
        if site.demo_link_sent_at is not None:
            return False
        if site.status == DemoSiteStatus.DELIVERED.value:
            return False

        sent_utc: datetime = self._as_utc(sent_at)
        site.demo_link_sent_at = sent_utc
        site.expires_at = sent_utc + timedelta(days=settings.demo_site_ttl_days)
        db.commit()
        logger.info(
            "Demo TTL started for slug=%s expires_at=%s",
            site.slug,
            site.expires_at.isoformat(),
        )
        return True

    def restart_demo_ttl(self, db: Session, site: DemoSite, sent_at: datetime) -> None:
        """Reset the demo TTL to a fresh window from *sent_at* (an SMS relance revival).

        Unlike :meth:`start_demo_ttl` (which only starts once), this always resets the
        clock — a relance one month later gives the prospect a brand-new 21-day demo.

        Args:
            db: Active database session.
            site: The demo site being relanced.
            sent_at: When the relance SMS was sent.
        """
        if site.status == DemoSiteStatus.DELIVERED.value:
            return
        sent_utc: datetime = self._as_utc(sent_at)
        site.demo_link_sent_at = sent_utc
        site.expires_at = sent_utc + timedelta(days=settings.demo_site_ttl_days)
        db.commit()
        logger.info("Demo TTL restarted for slug=%s expires_at=%s", site.slug, site.expires_at.isoformat())

    def maybe_start_ttl_after_demo_email(
        self,
        db: Session,
        *,
        user_id: int,
        prospect_id: int,
        sent_at: datetime,
        body_html: str,
    ) -> None:
        """Start the demo TTL when an outreach email ships the prospect's demo link."""
        site: DemoSite | None = (
            db.query(DemoSite)
            .filter(
                DemoSite.prospect_id == prospect_id,
                DemoSite.user_id == user_id,
                DemoSite.status == DemoSiteStatus.ACTIVE.value,
            )
            .order_by(DemoSite.created_at.desc())
            .first()
        )
        if site is None or not self.email_body_contains_demo_link(site, body_html):
            return
        self.start_demo_ttl(db, site, sent_at)

    @staticmethod
    def _storyblok_swap_lock(site_id: int) -> asyncio.Lock:
        lock = _storyblok_swap_locks.get(site_id)
        if lock is None:
            lock = asyncio.Lock()
            _storyblok_swap_locks[site_id] = lock
        return lock

    def storyblok_space_age_days(self, site: DemoSite, at: datetime) -> float:
        """Return the age in days of the current Storyblok space."""
        anchor: datetime | None = site.storyblok_space_created_at or site.created_at
        if anchor is None:
            return 0.0
        delta = self._as_utc(at) - self._as_utc(anchor)
        return max(delta.total_seconds(), 0.0) / 86400.0

    def needs_storyblok_space_swap(self, site: DemoSite, at: datetime) -> bool:
        """
        Return True when the Storyblok trial would expire before the demo TTL ends.

        Only applies before the first outreach email carrying the demo link.
        """
        if site.demo_link_sent_at is not None:
            return False
        if not storyblok_service.is_configured:
            return False
        if not site.storyblok_space_id and not site.storyblok_public_token:
            return False
        if site.status not in (
            DemoSiteStatus.ACTIVE.value,
            DemoSiteStatus.UNAVAILABLE.value,
        ):
            return False
        remaining_trial: float = settings.storyblok_trial_days - self.storyblok_space_age_days(site, at)
        return remaining_trial < settings.demo_site_ttl_days

    async def sync_content_json_from_storyblok_published(self, db: Session, site: DemoSite) -> bool:
        """
        Refresh ``content_json`` from the published Storyblok home story.

        Same source-of-truth path as the publish webhook (published only, never draft).
        """
        token: str | None = site.storyblok_public_token
        if not token:
            return False

        story_content = await storyblok_service.fetch_published_home_content(token)
        if story_content is None:
            return False

        flat_content = from_storyblok_site_content(story_content)
        if flat_content is None:
            return False

        previous = site.content_json if isinstance(site.content_json, dict) else {}
        for key in ("address", "rating", "reviewsCount", "lat", "lng"):
            if key not in flat_content and previous.get(key) is not None:
                flat_content[key] = previous[key]

        site.content_json = flat_content
        db.commit()
        db.refresh(site)
        return True

    def _apply_storyblok_provision(self, site: DemoSite, provision: StoryblokProvisionResult) -> None:
        """Copy Storyblok provisioning fields onto a demo site row."""
        site.storyblok_space_id = provision.space_id
        site.storyblok_public_token = provision.public_token
        site.storyblok_preview_token = provision.preview_token
        site.storyblok_editor_url = provision.editor_url
        site.storyblok_login_email = provision.login_email
        site.storyblok_login_password = provision.login_password
        site.storyblok_invite_sent = provision.invite_sent
        site.storyblok_space_created_at = datetime.now(UTC)
        site.storyblok_collaborator_status = None
        site.storyblok_joined_at = None
        site.content_json = provision.content_json

    async def swap_storyblok_space_for_outreach(self, db: Session, site: DemoSite) -> bool:
        """
        Replace the Storyblok space with a fresh trial, preserving published edits.

        Returns:
            True when a new space was provisioned.
        """
        if not self.needs_storyblok_space_swap(site, datetime.now(UTC)):
            return False

        lock = self._storyblok_swap_lock(site.id)
        async with lock:
            db.refresh(site)
            if not self.needs_storyblok_space_swap(site, datetime.now(UTC)):
                return False

            await self.sync_content_json_from_storyblok_published(db, site)
            content_json: dict = site.content_json if isinstance(site.content_json, dict) else {}
            if not content_json:
                logger.warning("Storyblok swap skipped for site %s — empty content_json", site.id)
                return False

            old_space_id = site.storyblok_space_id
            old_editor_url = site.storyblok_editor_url

            provision = await storyblok_service.provision_space_with_content(
                business_name=site.business_name,
                slug=site.slug,
                template_id=site.template_id,
                collaborator_email=(site.email or site.storyblok_login_email or "").strip(),
                preview_url=self.demo_url_for_slug(site.slug),
                content_json=content_json,
                invite_client=False,
                rehost_all_assets=True,
            )

            self._apply_storyblok_provision(site, provision)
            db.commit()
            db.refresh(site)

            try:
                await storyblok_service.delete_demo_space(
                    space_id=old_space_id,
                    editor_url=old_editor_url,
                    business_name=site.business_name,
                    slug=site.slug,
                )
            except Exception:
                logger.warning(
                    "Old Storyblok space cleanup failed after swap for site %s",
                    site.id,
                    exc_info=True,
                )

            logger.info(
                "Storyblok space swapped for outreach slug=%s new_space_id=%s",
                site.slug,
                site.storyblok_space_id,
            )
            return True

    async def ensure_storyblok_space_for_outreach(self, db: Session, site: DemoSite) -> None:
        """Sync published CMS content and swap the space when the trial would not cover the demo TTL."""
        if not self.needs_storyblok_space_swap(site, datetime.now(UTC)):
            return
        await self.swap_storyblok_space_for_outreach(db, site)

    def get_public_by_domain(self, db: Session, host: str) -> DemoSite | None:
        """
        Fetch a sold site by its production domain (host → site).

        Used to serve the client's site on their own domain once DELIVERED.
        """
        normalized: str = (host or "").strip().lower().removeprefix("www.")
        if not normalized:
            return None
        return (
            db.query(DemoSite)
            .filter(
                DemoSite.custom_domain == normalized,
                DemoSite.status == DemoSiteStatus.DELIVERED.value,
                DemoSite.content_json.isnot(None),
            )
            .first()
        )

    async def mark_delivered(self, db: Session, demo_site: DemoSite, domain: str) -> DemoSite:
        """
        Take the demo offline and promote it to the client's production domain.

        Sets status DELIVERED (excluded from TTL cleanup), stores the custom
        domain, makes it permanent, and points the Storyblok preview URL to the
        new domain so the client edits against their real site.
        """
        normalized: str = (domain or "").strip().lower().removeprefix("www.")
        demo_site.custom_domain = normalized or None
        demo_site.status = DemoSiteStatus.DELIVERED.value
        # Make permanent: a sold site must never be auto-expired.
        demo_site.expires_at = datetime.now(UTC) + timedelta(days=365 * 50)
        if normalized:
            demo_site.demo_url = f"https://{normalized}"
            demo_site.vercel_deployment_url = demo_site.demo_url
            if demo_site.storyblok_space_id:
                try:
                    await storyblok_service.configure_preview_url(demo_site.storyblok_space_id, demo_site.demo_url)
                except Exception:
                    logger.warning("Storyblok preview URL update failed for slug=%s", demo_site.slug, exc_info=True)
        db.commit()
        db.refresh(demo_site)
        activity_log_service.record(
            category=CATEGORY_DEMO_SITE,
            action="demo_site_delivered",
            status=STATUS_SUCCESS,
            title=f"Site livré en production · {demo_site.business_name} → {normalized or demo_site.slug}",
            user_id=demo_site.user_id,
            entity_type="demo_site",
            entity_id=demo_site.id,
        )
        return demo_site

    async def delete_demo_site(self, db: Session, demo_site: DemoSite) -> None:
        """Delete a demo site and its Storyblok space, freeing its slug for a clean regeneration.

        A site tied to a sale (already delivered, or referenced by an order) is soft-deleted so the
        order keeps a valid ``demo_site_id``; any other site is hard-deleted so its unique slug is
        freed and a later regeneration reuses it without a ``-2`` suffix.
        """
        try:
            deleted_space_id: int | None = await storyblok_service.delete_demo_space(
                space_id=demo_site.storyblok_space_id,
                editor_url=demo_site.storyblok_editor_url,
                business_name=demo_site.business_name,
                slug=demo_site.slug,
            )
            if deleted_space_id:
                logger.info("Deleted Storyblok space %s for demo site slug=%s", deleted_space_id, demo_site.slug)
        except Exception as exc:
            logger.warning("Failed to delete Storyblok space for slug=%s: %s", demo_site.slug, exc)

        # Purge the generated prospection video files with the demo, whichever deletion path we take.
        from services.demo_video_service import delete_files_for_slug

        delete_files_for_slug(demo_site.slug)

        # Deleting the generated demo frees the prospect from its automation, so it can be re-run and
        # the orchestrator never campaigns a site that no longer exists.
        self._free_prospect_from_automation(db, demo_site.prospect_id)

        deleted_user_id = demo_site.user_id
        deleted_business_name = demo_site.business_name
        deleted_id = demo_site.id
        if self._is_tied_to_sale(db, demo_site):
            self._soft_delete(demo_site)
        else:
            db.delete(demo_site)
        db.commit()
        activity_log_service.record(
            category=CATEGORY_DEMO_SITE,
            action="demo_site_deleted",
            status=STATUS_INFO,
            title=f"Site démo supprimé · {deleted_business_name}",
            user_id=deleted_user_id,
            entity_type="demo_site",
            entity_id=deleted_id,
        )

    @staticmethod
    def _free_prospect_from_automation(db: Session, prospect_id: int | None) -> None:
        """Release the prospect's automation claim when its generated demo is deleted.

        An automation item stays "claimed" (see ``acquisition_service.used_prospect_ids``) until it is
        skipped or fails; deleting the demo it produced must free the prospect so it can be re-run — and
        must stop the orchestrator from later campaigning a site that no longer exists. Marks every
        non-terminal item for this prospect (in a live run) as SKIPPED.
        """
        if not prospect_id:
            return
        items = (
            db.execute(
                select(AcquisitionRunItem)
                .join(AcquisitionRun, AcquisitionRunItem.run_id == AcquisitionRun.id)
                .where(
                    AcquisitionRunItem.prospect_id == prospect_id,
                    AcquisitionRun.status != AcquisitionRunStatus.CANCELLED.value,
                    AcquisitionRunItem.step.notin_(
                        [AcquisitionItemStep.SKIPPED.value, AcquisitionItemStep.FAILED.value]
                    ),
                )
            )
            .scalars()
            .all()
        )
        for item in items:
            item.step = AcquisitionItemStep.SKIPPED.value

    @staticmethod
    def _is_tied_to_sale(db: Session, demo_site: DemoSite) -> bool:
        """Whether the site was sold — delivered, or referenced by an order — so its row must be kept."""
        if demo_site.status == DemoSiteStatus.DELIVERED.value:
            return True
        return db.query(Order.id).filter(Order.demo_site_id == demo_site.id).first() is not None

    @staticmethod
    def _soft_delete(demo_site: DemoSite) -> None:
        """Blank a sold site's provisioning data and flag it deleted, keeping the row for its order link."""
        demo_site.storyblok_space_id = None
        demo_site.storyblok_public_token = None
        demo_site.storyblok_preview_token = None
        demo_site.storyblok_editor_url = None
        demo_site.storyblok_login_email = None
        demo_site.storyblok_login_password = None
        demo_site.storyblok_invite_sent = False
        demo_site.content_json = None
        demo_site.demo_url = None
        demo_site.demo_url_live = False
        demo_site.local_demo_url = None
        demo_site.vercel_deployment_id = None
        demo_site.vercel_deployment_url = None
        demo_site.verification_message = None
        demo_site.error_message = None
        demo_site.status = DemoSiteStatus.DELETED.value
        demo_site.deleted_at = datetime.now(UTC)
        demo_site.video_status = None
        demo_site.video_error = None
        demo_site.video_generated_at = None

    async def revive_demo_site(self, db: Session, site: DemoSite) -> DemoSite:
        """Wake a dormant (EXPIRED) demo so an SMS relance can push it again.

        The public demo renders from ``content_json`` (Storyblok is only needed at
        sale), so reviving rebuilds the content when it was cleared, restores the URL
        and flips the status back to ACTIVE — no re-scrape, no Storyblok re-provision.

        Args:
            db: Active database session.
            site: The dormant demo site.

        Returns:
            The revived site (ACTIVE), or the site unchanged when it is not dormant.
        """
        if site.status != DemoSiteStatus.EXPIRED.value:
            return site
        if not site.content_json:
            site.content_json = self._build_content_for_site(db, site)
        site.demo_url = site.demo_url or self.demo_url_for_slug(site.slug)
        site.vercel_deployment_url = site.demo_url
        site.error_message = None
        site.demo_url_live = True
        site.status = DemoSiteStatus.ACTIVE.value
        db.commit()
        db.refresh(site)
        logger.info("Demo site revived for slug=%s", site.slug)
        return site

    def _should_keep_dormant(self, db: Session, site: DemoSite) -> bool:
        """Whether an expiring demo should be kept dormant for a possible SMS relance.

        Kept when the prospect can still be SMS-reached: a French mobile, not marked
        « ne plus contacter », not opted out (STOP), and not already texted (the one-SMS
        touch is still available).

        Args:
            db: Active database session.
            site: The demo site reaching its TTL.

        Returns:
            ``True`` to keep the site dormant (EXPIRED), ``False`` to hard-delete it.
        """
        if not site.prospect_id:
            return False
        prospect = db.query(ProspectDB).filter(ProspectDB.id == site.prospect_id).first()
        if prospect is None or not prospect.phone or not is_mobile_fr(prospect.phone):
            return False
        if prospect.do_not_contact:
            return False
        phone_e164 = to_e164_fr(prospect.phone)
        if phone_e164 and (
            db.query(SmsSuppression.id)
            .filter(SmsSuppression.user_id == site.user_id, SmsSuppression.phone_e164 == phone_e164)
            .first()
            is not None
        ):
            return False
        already_texted = (
            db.query(SmsMessage.id)
            .filter(SmsMessage.user_id == site.user_id, SmsMessage.prospect_id == site.prospect_id)
            .first()
            is not None
        )
        return not already_texted

    @staticmethod
    def _purge_demo_video(site: DemoSite) -> None:
        """Delete the site's generated prospection video (its link dies with the demo)."""
        from services.demo_video_service import delete_files_for_slug

        delete_files_for_slug(site.slug)
        site.video_status = None
        site.video_error = None
        site.video_generated_at = None

    async def expire_due_sites(self, db: Session) -> int:
        """Expire demo sites past their TTL: keep the SMS-reachable ones dormant, delete the rest.

        The Storyblok space is freed in every case (only needed at sale). A prospect who can
        still receive an SMS keeps a dormant (EXPIRED) demo — ``content_json`` retained — so an
        auto-relance can revive it with a fresh TTL; everyone else is hard-deleted. Dormant demos
        nobody relanced are hard-deleted once past the retention window.

        Returns:
            Number of sites cleaned up.
        """
        now: datetime = datetime.now(UTC)
        due_sites: list[DemoSite] = (
            db.query(DemoSite)
            .filter(
                DemoSite.status.in_([DemoSiteStatus.ACTIVE.value, DemoSiteStatus.UNAVAILABLE.value]),
                DemoSite.demo_link_sent_at.isnot(None),
                DemoSite.expires_at <= now,
            )
            .all()
        )

        cleaned: int = 0
        for site in due_sites:
            # The Storyblok space is only needed at sale, never for a dormant/dead demo.
            try:
                await storyblok_service.delete_demo_space(
                    space_id=site.storyblok_space_id,
                    editor_url=site.storyblok_editor_url,
                    business_name=site.business_name,
                    slug=site.slug,
                )
            except Exception as exc:
                logger.warning("Failed to delete Storyblok space for slug=%s: %s", site.slug, exc)
            site.storyblok_space_id = None
            site.storyblok_public_token = None
            site.storyblok_preview_token = None
            site.storyblok_editor_url = None
            self._purge_demo_video(site)

            if self._should_keep_dormant(db, site):
                # Dormant: keep content_json so an auto-relance can revive it instantly.
                site.status = DemoSiteStatus.EXPIRED.value
            else:
                site.content_json = None
                site.status = DemoSiteStatus.DELETED.value
                site.deleted_at = now
            cleaned += 1

        # Dormant demos nobody relanced within the window are finally hard-deleted.
        dormant_cutoff: datetime = now - timedelta(days=settings.demo_dormant_retention_days)
        stale_dormant: list[DemoSite] = (
            db.query(DemoSite)
            .filter(DemoSite.status == DemoSiteStatus.EXPIRED.value, DemoSite.expires_at < dormant_cutoff)
            .all()
        )
        for site in stale_dormant:
            site.content_json = None
            site.status = DemoSiteStatus.DELETED.value
            site.deleted_at = now
            cleaned += 1

        if cleaned:
            db.commit()

        return cleaned


demo_site_service = DemoSiteService()
