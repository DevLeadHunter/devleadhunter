"""Status of the generated prospection video attached to a demo site."""

from enum import Enum


class DemoVideoStatus(str, Enum):
    """
    Lifecycle of a demo site's prospection video.

    The column is NULL until the owner's PC publishes the video or gives it up.
    """

    READY = "ready"
    FAILED = "failed"
