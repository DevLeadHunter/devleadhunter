"""Demo site model for template-based client websites."""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text, JSON
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
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False, default="plumber-simple")
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=DemoSiteStatus.PENDING.value,
        index=True,
    )
    storyblok_space_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    storyblok_public_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    storyblok_preview_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    storyblok_editor_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    storyblok_login_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    storyblok_login_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    storyblok_invite_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    content_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    vercel_deployment_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    vercel_deployment_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    demo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    demo_url_live: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    local_demo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    verification_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="demo_sites")

    def __repr__(self) -> str:
        return f"<DemoSite id={self.id} slug={self.slug} status={self.status}>"
