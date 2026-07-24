"""
Organization models — team workspace sharing the prospect list.

An organization groups users who prospect together: the prospect list is shared
across members (each prospect keeps its creator via ``user_id``), while campaigns,
demo sites, emails and credits stay personal (each member outreaches with their
OWN sending identity / Resend config).

A user belongs to at most ONE organization (UNIQUE constraint on ``user_id`` in
``organization_members``) — keeps scoping rules simple and leak-proof.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Organization(Base):
    """A team workspace owned by one user.

    Attributes:
        id: Unique organization identifier.
        name: Display name of the organization.
        owner_user_id: The user who created (and administers) the organization.
        created_at: Creation timestamp.
    """

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)

    members: Mapped[list[OrganizationMember]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class OrganizationMember(Base):
    """Membership of a user in an organization.

    Attributes:
        organization_id: The organization.
        user_id: The member — UNIQUE across the table (one org per user).
        role: ``owner`` or ``member``.
        created_at: When the user joined.
    """

    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("user_id", name="uq_organization_members_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="members")
