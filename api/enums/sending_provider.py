"""
Sending provider enumeration — the transport a user sends outreach through.

There are exactly two real transports (see ``EmailSendingService``):

- ``RESEND``: send via the Resend HTTP API using the user's ``resend_config``
  (own API key + verified ``from`` address). ``custom_domain`` email accounts
  also route through Resend, so they are covered by this provider.
- ``GMAIL``: send via the Gmail API using a connected Gmail OAuth account.

A user has exactly ONE active sending identity at a time, stored on
``users.sending_provider``.
"""
from enum import Enum


class SendingProvider(str, Enum):
    """The active email-sending transport for a user."""

    RESEND = "resend"
    GMAIL = "gmail"
