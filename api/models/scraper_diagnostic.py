"""ScraperDiagnostic model — one row per source run, for the admin monitoring page.

Written reactively by the orchestrator after each source runs (ok / empty / blocked /
timeout / error), with the HTML captured at the moment of a block. This is what lets an
admin see "Google broke" without proactively probing anything.
"""

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base


class ScraperDiagnostic(Base):
    """Outcome of a single source run within a scraping job."""

    __tablename__ = "scraper_diagnostics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    # Source value (google / pagesjaunes / brightdata / osm / auto).
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # Classified outcome: ok | empty | blocked | timeout | error.
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)

    results_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    expected_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Short error message (timeouts / exceptions) — capped.
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Page HTML captured when the source was blocked (for the operator to write a new selector).
    html_snapshot: Mapped[str | None] = mapped_column(Text().with_variant(MEDIUMTEXT, "mysql"), nullable=True)

    # Who triggered the run (nullable — background/system runs have none).
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<ScraperDiagnostic id={self.id} source={self.source} status={self.status} n={self.results_count}>"
