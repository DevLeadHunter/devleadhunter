"""Status of the generated prospection video attached to a demo site."""
from enum import Enum


class DemoVideoStatus(str, Enum):
    """
    Lifecycle of a demo site's prospection video.

    The column is NULL when no video was ever requested.
    """

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"
