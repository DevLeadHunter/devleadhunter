"""Business logic for demo site generation and lifecycle."""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from core.config import settings
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.user import User
from services.storyblok_service import (
    storyblok_service,
    StoryblokProvisionResult,
    StoryblokProvisionError,
)
from services.demo_site_verification_service import (
    demo_site_verification_service,
    DemoSiteVerificationResult,
)
from services.enrichment_service import enrichment_service
from services.templates import registry as template_registry

logger = logging.getLogger(__name__)

AVAILABLE_TEMPLATES: list[dict[str, object]] = template_registry.AVAILABLE_TEMPLATES


class DemoSiteService:
    """Orchestrates demo site creation, listing, and cleanup."""

    def list_templates(self) -> list[dict[str, object]]:
        """Return templates available in the stepper."""
        return AVAILABLE_TEMPLATES

    def _theme_from_content(self, content_json: Optional[dict]) -> Optional[dict[str, str]]:
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
        phone: Optional[str] = None,
        email: Optional[str] = None,
        city: Optional[str] = None,
        description: Optional[str] = None,
        theme: Optional[dict[str, str]] = None,
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

    def _enrichment_dict_for_site(self, db: Session, demo_site: DemoSite) -> Optional[dict]:
        """Return the prospect's enrichment data for a demo site, when linked."""
        prospect_id: Optional[int] = getattr(demo_site, "prospect_id", None)
        if not prospect_id:
            return None
        record = enrichment_service.get_for_prospect(db, demo_site.user_id, prospect_id)
        return enrichment_service.to_dict(record)

    async def _resolve_enrichment_for_creation(
        self, db: Session, user_id: int, prospect_id: Optional[int]
    ) -> Optional[dict]:
        """Fetch (and run on demand if missing) the prospect enrichment before generation."""
        if not prospect_id:
            return None
        try:
            prospect = enrichment_service.get_prospect_for_user(db, user_id, prospect_id)
            if not prospect:
                return None
            record = await enrichment_service.ensure_enriched(db, user_id, prospect)
            return enrichment_service.to_dict(record)
        except Exception:  # noqa: BLE001 — never block site creation on enrichment
            logger.warning("Enrichment resolution failed for prospect_id=%s", prospect_id, exc_info=True)
            return None

    def _build_content_for_site(self, db: Session, demo_site: DemoSite) -> dict:
        """Build Storyblok content JSON from the demo site record."""
        return self._build_content_for_site_with_theme(db, demo_site, theme=None)

    def _build_content_for_site_with_theme(
        self, db: Session, demo_site: DemoSite, theme: Optional[dict[str, str]] = None
    ) -> dict:
        """Build Storyblok content JSON from the demo site record (with enrichment)."""
        palette = theme or self._theme_from_content(demo_site.content_json) or self._default_theme_for_template(
            demo_site.template_id
        )
        return storyblok_service.build_content_json(
            business_name=demo_site.business_name,
            phone=demo_site.phone,
            email=demo_site.email,
            city=demo_site.city,
            description=demo_site.description,
            template_id=demo_site.template_id,
            theme=palette,
            enrichment=self._enrichment_dict_for_site(db, demo_site),
        )

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
            except Exception as exc:  # noqa: BLE001
                logger.exception("Demo site content sync failed for slug=%s", demo_site.slug)
                demo_site.status = DemoSiteStatus.FAILED.value
                demo_site.error_message = str(exc)
                demo_site.demo_url_live = False
                db.commit()
                db.refresh(demo_site)
                return demo_site

        verification: DemoSiteVerificationResult = await demo_site_verification_service.verify(db, demo_site)
        self._apply_verification(demo_site, verification)
        db.commit()
        db.refresh(demo_site)
        return demo_site

    async def update_demo_site(
        self,
        db: Session,
        demo_site: DemoSite,
        *,
        business_name: Optional[str] = None,
        template_id: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        city: Optional[str] = None,
        description: Optional[str] = None,
        theme: Optional[dict[str, str]] = None,
    ) -> DemoSite:
        """Update demo site fields and regenerate its published content."""
        pending_theme = theme
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

    async def invite_client_to_cms(self, db: Session, demo_site: DemoSite) -> DemoSite:
        """Send a Storyblok CMS invitation to the demo site client email."""
        if demo_site.storyblok_invite_sent:
            raise ValueError("The client has already been invited to Storyblok.")

        email: Optional[str] = demo_site.email or demo_site.storyblok_login_email
        if not email or not email.strip():
            raise ValueError("Client email is required to send a Storyblok invitation.")

        space_id: Optional[int] = demo_site.storyblok_space_id
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
        phone: Optional[str],
        email: Optional[str],
        city: Optional[str],
        description: Optional[str],
        invite_client_to_cms: bool = False,
        theme: Optional[dict[str, str]] = None,
        prospect_id: Optional[int] = None,
    ) -> DemoSite:
        """
        Create and provision a demo site for the authenticated user.

        @param db - SQLAlchemy session.
        @param user - Owner account.
        @param prospect_id - Optional source prospect; its enrichment data (run on
            demand here if missing) is merged into the generated site content.
        @returns Persisted demo site record in ACTIVE or FAILED status.
        """
        if not email or not email.strip():
            raise ValueError("Client email is required for the demo site record.")

        slug: str = self.unique_slug(db, business_name)
        expires_at: datetime = datetime.now(timezone.utc) + timedelta(days=settings.demo_site_ttl_days)

        demo_site: DemoSite = DemoSite(
            user_id=user.id,
            prospect_id=prospect_id,
            slug=slug,
            template_id=template_id,
            business_name=business_name,
            phone=phone,
            email=email,
            city=city,
            description=description,
            status=DemoSiteStatus.PROVISIONING.value,
            expires_at=expires_at,
        )
        db.add(demo_site)
        db.commit()
        db.refresh(demo_site)

        enrichment_dict: Optional[dict] = await self._resolve_enrichment_for_creation(db, user.id, prospect_id)

        try:
            provision: StoryblokProvisionResult = await storyblok_service.provision_space(
                business_name=business_name,
                slug=slug,
                phone=phone,
                email=email,
                city=city,
                description=description,
                template_id=template_id,
                collaborator_email=email.strip(),
                preview_url=self.demo_url_for_slug(slug),
                invite_client=invite_client_to_cms,
                theme=theme,
                enrichment=enrichment_dict,
            )

            demo_site.storyblok_space_id = provision.space_id
            demo_site.storyblok_public_token = provision.public_token
            demo_site.storyblok_preview_token = provision.preview_token
            demo_site.storyblok_editor_url = provision.editor_url
            demo_site.storyblok_login_email = provision.login_email
            demo_site.storyblok_login_password = provision.login_password
            demo_site.storyblok_invite_sent = provision.invite_sent
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
                demo_site.verification_message = (
                    f"{verification.message} Storyblok mock mode is enabled."
                )
        except StoryblokProvisionError as exc:
            logger.exception("Demo site provisioning failed for slug=%s after Storyblok space creation", slug)
            demo_site.storyblok_space_id = exc.space_id
            demo_site.storyblok_editor_url = exc.editor_url
            demo_site.content_json = exc.content_json or self._build_content_for_site(db, demo_site)
            demo_site.demo_url = demo_site.demo_url or self.demo_url_for_slug(slug)
            demo_site.vercel_deployment_url = demo_site.demo_url
            demo_site.status = DemoSiteStatus.FAILED.value
            demo_site.error_message = str(exc)
            demo_site.demo_url_live = False
        except Exception as exc:  # noqa: BLE001 — surface provisioning failure on the record
            logger.exception("Demo site provisioning failed for slug=%s", slug)
            demo_site.content_json = demo_site.content_json or self._build_content_for_site(db, demo_site)
            demo_site.demo_url = demo_site.demo_url or self.demo_url_for_slug(slug)
            demo_site.vercel_deployment_url = demo_site.demo_url
            demo_site.status = DemoSiteStatus.FAILED.value
            demo_site.error_message = str(exc)
            demo_site.demo_url_live = False

        db.commit()
        db.refresh(demo_site)
        return demo_site

    def list_for_user(self, db: Session, user_id: int) -> list[DemoSite]:
        """List demo sites owned by a user."""
        return (
            db.query(DemoSite)
            .filter(DemoSite.user_id == user_id, DemoSite.status != DemoSiteStatus.DELETED.value)
            .order_by(DemoSite.created_at.desc())
            .all()
        )

    def get_for_user(self, db: Session, user_id: int, demo_site_id: int) -> Optional[DemoSite]:
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

    def get_public_by_slug(self, db: Session, slug: str) -> Optional[DemoSite]:
        """
        Fetch a *demo* by slug for demo.dibodev.fr/{slug}.

        Served while the demo lives (pending/provisioning/active/unavailable…), so
        post-provisioning verification and the demo-host render work. A **sold**
        site (status DELIVERED) or a deleted one is taken down here (404) — a sold
        site then lives only on the client's own domain.
        """
        now: datetime = datetime.now(timezone.utc)
        site: Optional[DemoSite] = (
            db.query(DemoSite)
            .filter(
                DemoSite.slug == slug,
                DemoSite.status.notin_([DemoSiteStatus.DELETED.value, DemoSiteStatus.DELIVERED.value]),
                DemoSite.content_json.isnot(None),
            )
            .first()
        )
        if not site:
            return None

        expires_at: datetime = site.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now:
            return None

        return site

    def get_public_by_domain(self, db: Session, host: str) -> Optional[DemoSite]:
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
        demo_site.expires_at = datetime.now(timezone.utc) + timedelta(days=365 * 50)
        if normalized:
            demo_site.demo_url = f"https://{normalized}"
            demo_site.vercel_deployment_url = demo_site.demo_url
            if demo_site.storyblok_space_id:
                try:
                    await storyblok_service.configure_preview_url(
                        demo_site.storyblok_space_id, demo_site.demo_url
                    )
                except Exception:  # noqa: BLE001 — preview URL is non-critical
                    logger.warning("Storyblok preview URL update failed for slug=%s", demo_site.slug, exc_info=True)
        db.commit()
        db.refresh(demo_site)
        return demo_site

    async def delete_demo_site(self, db: Session, demo_site: DemoSite) -> None:
        """Soft-delete a demo site and remove its Storyblok space when present."""
        now: datetime = datetime.now(timezone.utc)
        try:
            deleted_space_id: Optional[int] = await storyblok_service.delete_demo_space(
                space_id=demo_site.storyblok_space_id,
                editor_url=demo_site.storyblok_editor_url,
                business_name=demo_site.business_name,
                slug=demo_site.slug,
            )
            if deleted_space_id:
                logger.info("Deleted Storyblok space %s for demo site slug=%s", deleted_space_id, demo_site.slug)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to delete Storyblok space for slug=%s: %s", demo_site.slug, exc)

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
        demo_site.deleted_at = now

        # Purge the generated prospection video files with the demo.
        from services.demo_video_service import delete_files_for_slug

        delete_files_for_slug(demo_site.slug)
        demo_site.video_status = None
        demo_site.video_error = None
        demo_site.video_generated_at = None
        db.commit()

    async def expire_due_sites(self, db: Session) -> int:
        """
        Mark expired demo sites and delete their Storyblok spaces.

        @returns Number of sites cleaned up.
        """
        now: datetime = datetime.now(timezone.utc)
        due_sites: list[DemoSite] = (
            db.query(DemoSite)
            .filter(
                DemoSite.status.in_(
                    [
                        DemoSiteStatus.ACTIVE.value,
                        DemoSiteStatus.UNAVAILABLE.value,
                    ]
                ),
                DemoSite.expires_at <= now,
            )
            .all()
        )

        cleaned: int = 0
        for site in due_sites:
            try:
                await storyblok_service.delete_demo_space(
                    space_id=site.storyblok_space_id,
                    editor_url=site.storyblok_editor_url,
                    business_name=site.business_name,
                    slug=site.slug,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to delete Storyblok space for slug=%s: %s", site.slug, exc)

            site.storyblok_space_id = None
            site.storyblok_public_token = None
            site.storyblok_preview_token = None
            site.storyblok_editor_url = None
            site.content_json = None
            site.status = DemoSiteStatus.DELETED.value
            site.deleted_at = now

            # La vidéo de prospection suit le TTL de la démo (lien mort sinon).
            from services.demo_video_service import delete_files_for_slug

            delete_files_for_slug(site.slug)
            site.video_status = None
            site.video_error = None
            site.video_generated_at = None
            cleaned += 1

        if cleaned:
            db.commit()

        return cleaned


demo_site_service = DemoSiteService()
