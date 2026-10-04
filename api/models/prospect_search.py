"""
Prospect search model — one objective-driven search and its running totals.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import UTF8MB4_TABLE_OPTIONS, Base
from enums.prospect_search import ProspectSearchChannel, ProspectSearchStatus, ProspectSearchValidationMode


class ProspectSearch(Base):
    """
    One search launched with an objective (« 5 landscapers in Switzerland »).

    Attributes:
        id: Unique identifier
        user_id: Owner of the search
        trades: Searched trades, as typed by the user
        country: ISO alpha-2 country of the search
        cities: Cities asked by the user (empty = chosen by the search)
        count_per_trade: Prospects wanted for each trade
        channel: Contact channel the kept prospects must allow
        only_without_website: Whether a business with a working website is discarded
        minimum_rating: Google rating under which a business is discarded
        validation_mode: Whether the user accepts each candidate, or the search creates the prospects itself
        status: Lifecycle state
        progress: Counters and scanned cities, per trade
        journal: Short log lines shown to the user, each with the time it was written (naive UTC)
        request_count: Paid web requests spent so far
        judge_call_count: Language-model calls spent so far
        error_message: Why the search failed
        created_at: When the search was asked
        started_at: When the run started
        completed_at: When the run ended
        updated_at: Last change
    """

    __tablename__ = "prospect_searches"
    __table_args__ = (UTF8MB4_TABLE_OPTIONS,)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    trades: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="FR")
    cities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    count_per_trade: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default=ProspectSearchChannel.EMAIL.value)
    only_without_website: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    minimum_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    validation_mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ProspectSearchValidationMode.MANUAL.value
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProspectSearchStatus.PENDING.value, index=True
    )
    progress: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    journal: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False, default=list)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    judge_call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)
