"""Demo site model for template-based client websites."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from enums.demo_site_status import DemoSiteStatus

if TYPE_CHECKING:
    from models.user import User


class DemoSite(Base):
    """
    A temporary demo website generated from a template.

    Hosted at demo.dibodev.fr/{slug}. The 21-day TTL starts when the demo link
    is first emailed to the prospect (``demo_link_sent_at``), not at generation.
    """

    __tablename__ = "demo_sites"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False, default="plumber-signature")
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DemoSiteStatus.PENDING.value,
        index=True,
    )
    storyblok_space_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    storyblok_public_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storyblok_preview_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storyblok_editor_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    storyblok_login_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storyblok_login_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storyblok_invite_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # When the current Storyblok space was provisioned (reset after an outreach swap).
    storyblok_space_created_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Where the client stands on the CMS handover (see StoryblokCollaboratorStatus): NULL until
    # first observed, then not_invited / pending / joined. Refreshed on demand from Storyblok.
    storyblok_collaborator_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # First time the client was observed as having joined the space (accepted the invite).
    storyblok_joined_at: Mapped[datetime | None] = mapped_column(nullable=True)
    content_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # User-curated photo order for the site (list of URLs). NULL = default scraped order.
    # When set, it overrides the prospect photos at generation: [0]→hero, [1]→about, [2:]→gallery.
    image_order: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # The photo pool known when image_order was last saved. A pool photo missing from BOTH the order
    # and this snapshot is genuinely new (auto-appended); one in the snapshot but not the order was
    # removed on purpose (kept hidden). NULL until the first save after this column shipped.
    image_pool_snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Operator-curated section content that must survive every regeneration, like ``image_order``
    # does for photos: ``{"services": [{"title", "description", "image"}], "services_source":
    # "manual" | "ai" | "ai_auto"}``. Without it the specialties typed by hand were wiped by the next
    # colour tweak (a regeneration rebuilds the story from enrichment). NULL = generated as usual.
    section_overrides: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Whether the action colour is pulled from the prospect's logo (True) or kept as the template
    # default (False). Default True — the logo colour is used when a usable one exists.
    use_brand_color: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    vercel_deployment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    vercel_deployment_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    demo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Client production domain once sold (e.g. toto-plombier-rennes.fr).
    custom_domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    demo_url_live: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Prospection video (webcam + capture du site) — NULL = jamais générée.
    video_status: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    video_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_generated_at: Mapped[datetime | None] = mapped_column(nullable=True)
    local_demo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    verification_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # When the demo link was first emailed to the prospect — NULL until then (TTL not started).
    demo_link_sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # When the operator manually reviewed this site as good-to-send from the campaign forecast
    # (distinct from ``verification_message``, which is the automated live-URL check). NULL = not
    # yet reviewed; cleared whenever the site content is rebuilt so a stale review never lingers.
    site_reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="demo_sites")

    def __repr__(self) -> str:
        return f"<DemoSite id={self.id} slug={self.slug} status={self.status}>"
