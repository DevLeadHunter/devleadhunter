"""
Prospect search candidate model — one business seen by a search, with its verdict and proofs.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, ColumnElement, Float, Integer, String, and_
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from core.database import UTF8MB4_TABLE_OPTIONS, Base
from enums.prospect_search import CandidateStatus

_STATUSES_OPEN_TO_A_DECISION: tuple[str, ...] = (
    CandidateStatus.KEPT.value,
    CandidateStatus.SET_ASIDE.value,
    CandidateStatus.TO_CONFIRM.value,
)


class ProspectSearchCandidate(Base):
    """
    One business a search looked at, kept or not.

    The row is the search's memory: a discarded candidate is never verified again by
    a later search, and each kept field carries the page that proves it.

    Attributes:
        id: Unique identifier
        search_id: The search that found it
        user_id: Owner of the search
        trade: Trade the candidate was searched for
        searched_city: City of the query that surfaced it
        origin: Where it was first seen
        name: Business name
        address: Street address
        city: City of the business
        country: ISO alpha-2 country
        phone: Phone number, national form
        phone_is_mobile: Whether the number can receive an SMS
        email: Best email found
        email_proof_level: How well the email is proven
        website: Website found for the business, working or not
        website_status: Liveness of that website
        google_cid: Google's identifier of the listing
        google_maps_url: Link to the Google Maps listing
        facebook_url: Facebook page of the business
        google_rating: Google rating
        google_reviews_count: Number of Google reviews
        google_category: Category shown by Google
        owner_name: Owner's name read on a page, never invented
        registry_number: Company number read on a registry page
        has_website_button: Whether its Google listing shows a website button (unknown when not read there)
        status: Where the candidate stands
        reject_reason: Why it was discarded
        reject_detail: The reason in plain words, shown to the user
        evidence: Proof lines (field, value, source, url, snippet)
        identity_keys: Keys used to recognise the same business elsewhere
        prospect_id: The prospect created from this candidate
        created_at: When it was found
        updated_at: Last change
        is_pending: Whether it waits for the user to accept or refuse it (derived, usable in a query)
    """

    __tablename__ = "prospect_search_candidates"
    __table_args__ = (UTF8MB4_TABLE_OPTIONS,)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    trade: Mapped[str] = mapped_column(String(80), nullable=False)
    searched_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    origin: Mapped[str] = mapped_column(String(24), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str] = mapped_column(String(2), nullable=False, default="FR")
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    phone_is_mobile: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_proof_level: Mapped[str | None] = mapped_column(String(1), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    website_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    google_cid: Mapped[str | None] = mapped_column(String(32), nullable=True)
    google_maps_url: Mapped[str | None] = mapped_column(String(700), nullable=True)
    facebook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    google_reviews_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    google_category: Mapped[str | None] = mapped_column(String(160), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    registry_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    has_website_button: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CandidateStatus.DISCOVERED.value, index=True
    )
    reject_reason: Mapped[str | None] = mapped_column(String(24), nullable=True)
    reject_detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    identity_keys: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)

    @hybrid_property
    def is_pending(self) -> bool:
        """Whether the candidate waits for the user's decision: placed by the search and not a prospect yet."""
        return self.prospect_id is None and self.status in _STATUSES_OPEN_TO_A_DECISION

    @is_pending.inplace.expression
    @classmethod
    def _is_pending_filter(cls) -> ColumnElement[bool]:
        """The same rule as a query filter."""
        return and_(cls.prospect_id.is_(None), cls.status.in_(_STATUSES_OPEN_TO_A_DECISION))
