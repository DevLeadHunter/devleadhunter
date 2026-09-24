"""How the widget takes an appointment."""

from enum import Enum


class AssistantBookingMode(str, Enum):
    """Free slots booked in the connected agenda (``calendar``), or half-days to wish (``request``)."""

    CALENDAR = "calendar"
    REQUEST = "request"
