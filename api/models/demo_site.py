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

    Hosted at demo.dibodev.fr/{slug} for 14 days by default.
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
    content_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
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
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="demo_sites")

    def __repr__(self) -> str:
        return f"<DemoSite id={self.id} slug={self.slug} status={self.status}>"
