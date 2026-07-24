"""Lifecycle status for prospect enrichment data."""

from enum import Enum


class EnrichmentStatus(str, Enum):
    """Status of a prospect's rich enrichment data."""

    PENDING = "pending"
    ENRICHING = "enriching"
    COMPLETED = "completed"
    FAILED = "failed"
