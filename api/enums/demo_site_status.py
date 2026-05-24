"""Demo site lifecycle statuses."""
from enum import Enum


class DemoSiteStatus(str, Enum):
    """Status of a provisioned demo website."""

    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    UNAVAILABLE = "unavailable"
    EXPIRED = "expired"
    DELETED = "deleted"
    FAILED = "failed"
