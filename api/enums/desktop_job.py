"""
Enumerations of the desktop jobs: work a device without the desktop app hands to the owner's computer.
"""

from enum import Enum


class DesktopJobKind(str, Enum):
    """
    What the desktop app has to do.

    Attributes:
        PROSPECT_ENRICHMENT: Read a prospect's Google and Facebook pages with the computer's Chrome, then save them
    """

    PROSPECT_ENRICHMENT = "prospect_enrichment"


class DesktopJobStatus(str, Enum):
    """
    Lifecycle of a desktop job.

    Attributes:
        WAITING: Left for the desktop app, no computer has taken it
        RUNNING: A desktop app took it and works on it
        DONE: The desktop app finished and saved its result
        FAILED: The desktop app gave up, with the reason the dashboard shows
        CANCELLED: Withdrawn by the user before a computer took it
    """

    WAITING = "waiting"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
