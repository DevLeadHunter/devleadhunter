"""What an outbound SMS is for: a prospecting touch, or a service message its recipient asked for."""

from enum import Enum


class SmsMessageKind(str, Enum):
    """Purpose of an outbound SMS, stored in ``sms_messages.kind`` (NULL: prospecting, older than the touches).

    Every kind but ``SERVICE`` is prospecting: opt-out mention, legal window, daily cap, recap.

    Attributes:
        PROSPECTING: A manual composer SMS — it ends the prospect's automated sequence.
        FIRST_CONTACT: The first prospecting message a prospect ever receives (cold SMS, first SMS campaign).
        FOLLOW_UP: The one SMS relance after a first contact (email or SMS) — it ends the sequence.
        SERVICE: An alert the recipient subscribed to (a sold assistant's owner) — none of the above.
    """

    PROSPECTING = "prospecting"
    FIRST_CONTACT = "first_contact"
    FOLLOW_UP = "follow_up"
    SERVICE = "service"
