"""
Enums for the acquisition orchestrator ("Séquences d'acquisition").

A *sequence* auto-chains the tunnel — search → enrich → generate → (review) →
campaign — for a batch of prospects.  Statuses live as plain strings in the
DB (``String`` columns), following the Order/DemoSite convention.
"""

from enum import Enum


class AcquisitionRunStatus(str, Enum):
    """Lifecycle of a whole acquisition sequence."""

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class AcquisitionRunMode(str, Enum):
    """How far the machine goes on its own."""

    #: Auto-enrich + auto-generate, then PAUSE for a human to validate the
    #: generated sites before any outreach.
    SEMI_AUTO = "semi_auto"
    #: Never pause — generate and campaign without human validation.
    FULL_AUTO = "full_auto"


class AcquisitionItemStep(str, Enum):
    """Per-prospect position in the state machine."""

    FOUND = "found"
    ENRICHING = "enriching"
    ENRICHED = "enriched"
    GENERATING = "generating"
    GENERATED = "generated"
    CAMPAIGNING = "campaigning"
    SKIPPED = "skipped"
    FAILED = "failed"


#: Steps at which an item is done and the orchestrator won't touch it again.
TERMINAL_ITEM_STEPS: tuple[str, ...] = (
    AcquisitionItemStep.CAMPAIGNING.value,
    AcquisitionItemStep.SKIPPED.value,
    AcquisitionItemStep.FAILED.value,
)

#: Ordered display of every step (drives the pipeline board columns).
STEP_ORDER: tuple[str, ...] = (
    AcquisitionItemStep.FOUND.value,
    AcquisitionItemStep.ENRICHING.value,
    AcquisitionItemStep.ENRICHED.value,
    AcquisitionItemStep.GENERATING.value,
    AcquisitionItemStep.GENERATED.value,
    AcquisitionItemStep.CAMPAIGNING.value,
    AcquisitionItemStep.SKIPPED.value,
    AcquisitionItemStep.FAILED.value,
)
