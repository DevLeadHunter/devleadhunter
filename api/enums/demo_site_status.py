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
    # Sold: the demo is taken down (demo.dibodev.fr 404) and the site is served
    # in production on the client's own domain. Excluded from TTL cleanup.
    DELIVERED = "delivered"
