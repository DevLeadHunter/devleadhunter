"""Contracts of the objective-driven prospect search."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from enums.prospect_search import ProspectSearchChannel, ProspectSearchValidationMode

TypedTrade = Annotated[str, StringConstraints(max_length=60)]
TypedCity = Annotated[str, StringConstraints(max_length=80)]

_MAX_DECISIONS_PER_REQUEST: int = 100


class ProspectSearchCreate(BaseModel):
    """The objective of a search: which trades, where, how many, reachable how."""

    trades: list[TypedTrade] = Field(..., min_length=1, max_length=6, description="Trades to search, as typed")
    country: str = Field("FR", min_length=2, max_length=2, description="ISO alpha-2 country of the search")
    cities: list[TypedCity] = Field(default_factory=list, max_length=20, description="Towns to search (empty = chosen)")
    count_per_trade: int = Field(5, ge=1, le=50, description="Prospects wanted for each trade")
    channel: ProspectSearchChannel = Field(ProspectSearchChannel.EMAIL, description="Contact the prospects must allow")
    only_without_website: bool = Field(True, description="Discard a business with a working website")
    minimum_rating: float | None = Field(None, ge=0, le=5, description="Google rating floor")
    validation_mode: ProspectSearchValidationMode = Field(
        ProspectSearchValidationMode.MANUAL,
        description="Whether the user accepts each candidate, or the search creates the prospects itself",
    )


class SearchTradeOption(BaseModel):
    """A trade the search knows how to recognise."""

    key: str
    label: str


class SearchTradeCounts(BaseModel):
    """Where the candidates of one trade stand."""

    trade: str
    label: str
    wanted: int
    kept: int
    set_aside: int
    to_confirm: int
    waiting_browser: int
    rejected: int
    unverified: int
    towns: list[str]
    stop_reason: str | None


class ProspectSearchSummary(BaseModel):
    """A search and its totals, without its candidates."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    trades: list[str]
    country: str
    cities: list[str]
    count_per_trade: int
    channel: str
    only_without_website: bool
    minimum_rating: float | None
    validation_mode: str
    status: str
    request_count: int
    judge_call_count: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    trade_counts: list[SearchTradeCounts] = Field(default_factory=list)


class CandidateEvidenceLine(BaseModel):
    """One proof of a candidate: what was read, where."""

    fact: str
    value: str
    source: str
    url: str | None = None
    snippet: str | None = None


class ProspectSearchCandidateResponse(BaseModel):
    """A business a search looked at, with its place and its proofs."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    search_id: int
    trade: str
    origin: str
    searched_city: str | None
    name: str
    address: str | None
    city: str | None
    country: str
    phone: str | None
    phone_is_mobile: bool
    email: str | None
    email_proof_level: str | None
    website: str | None
    website_status: str | None
    google_maps_url: str | None
    facebook_url: str | None
    google_rating: float | None
    google_reviews_count: int | None
    google_category: str | None
    owner_name: str | None
    registry_number: str | None
    status: str
    reject_reason: str | None
    reject_detail: str | None
    evidence: list[CandidateEvidenceLine]
    prospect_id: int | None
    is_pending: bool = Field(description="Waits for the user to accept or refuse it")
    created_at: datetime


class SearchJournalLine(BaseModel):
    """One line of a search's journal: when it was written (naive UTC) and what it says."""

    at: datetime
    message: str


class ProspectSearchDetail(ProspectSearchSummary):
    """A search with its journal and every candidate it looked at."""

    journal: list[SearchJournalLine] = Field(default_factory=list)
    candidates: list[ProspectSearchCandidateResponse] = Field(default_factory=list)


class SearchBrowserTask(BaseModel):
    """A Facebook page a browser on the user's machine must read for a candidate."""

    candidate_id: int
    name: str
    facebook_url: str
    country: str


class FacebookContactPayload(BaseModel):
    """What a browser read on a candidate's Facebook page."""

    is_readable: bool
    emails: list[str] = Field(default_factory=list, max_length=20)
    phone: str | None = None
    website: str | None = None


class ProspectSearchActivity(BaseModel):
    """What the user has in progress: candidates waiting for a decision, the search at work, the queued ones."""

    pending_count: int
    active_search: ProspectSearchSummary | None
    queued_searches: list[ProspectSearchSummary] = Field(
        default_factory=list, description="Searches waiting for their turn, in the order they will run"
    )


class CandidateDecisions(BaseModel):
    """Candidates the user accepts and candidates the user refuses, in one request."""

    accept: list[int] = Field(default_factory=list, description="Candidates that become prospects")
    reject: list[int] = Field(default_factory=list, description="Candidates discarded for good")

    @model_validator(mode="after")
    def check_the_decisions_are_few_and_distinct(self) -> CandidateDecisions:
        """Refuse a request deciding too many candidates, or accepting and refusing the same one."""
        if len(self.accept) + len(self.reject) > _MAX_DECISIONS_PER_REQUEST:
            raise ValueError(f"Pas plus de {_MAX_DECISIONS_PER_REQUEST} décisions à la fois.")
        if set(self.accept) & set(self.reject):
            raise ValueError("Un même candidat ne peut pas être accepté et refusé.")
        return self


class RefusedCandidateDecision(BaseModel):
    """A decision that could not be applied, with the reason in the user's words."""

    candidate_id: int
    detail: str


class CandidateDecisionsOutcome(BaseModel):
    """How many decisions were applied, and the ones that were not."""

    accepted: int
    rejected: int
    refused: list[RefusedCandidateDecision] = Field(default_factory=list)
