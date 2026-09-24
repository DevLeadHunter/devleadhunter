"""What an outbound SMS is for: prospecting, or a service message its recipient asked for."""

from enum import Enum


class SmsMessageKind(str, Enum):
    """Purpose of an outbound SMS (stored in ``sms_messages.kind``; NULL = prospecting).

    Attributes:
        PROSPECTING: Prospecting / relance — STOP mention, legal window, daily cap, recap.
        SERVICE: An alert the recipient subscribed to (a sold assistant's owner) — none of the above.
    """

    PROSPECTING = "prospecting"
    SERVICE = "service"
