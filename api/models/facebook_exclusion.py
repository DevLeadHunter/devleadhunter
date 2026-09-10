"""
Facebook page exclusion model — pages rejected by the discovery match filter.
"""

from datetime import datetime

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class FacebookPageExclusion(Base):
    """A Facebook page a user's discovery must skip (already tested, unusable).

    Written when the post-search match filter rejects an enriched candidate:
    ``no_email`` (the page exposes no contact email) or ``has_website`` (the
    business turned out to have a real website while the search asked for
    site-less prospects). Discovery then skips these URLs so the same page is
    never re-enriched search after search.

    Attributes:
        id: Unique identifier (auto-increment)
        user_id: User whose searches skip this page
        page_url: Canonical page URL as produced by the discovery scraper
        reason: Why the page is unusable (``no_email`` | ``has_website``)
        created_at: Timestamp when the exclusion was recorded
    """

    __tablename__ = "facebook_page_exclusions"
    __table_args__ = (UniqueConstraint("user_id", "page_url", name="uq_fb_exclusion_user_page"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    page_url: Mapped[str] = mapped_column(String(512), nullable=False)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
