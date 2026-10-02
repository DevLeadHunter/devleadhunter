"""How a prospect of a given country opts out of our SMS.

France routes a « STOP » reply through a five-digit short code; most other countries
have no such code, so the provider inserts an unsubscribe link instead. The mode is a
fact of the country, read from its profile when the opt-out mention is built.
"""

from enum import Enum


class SmsOptOutMode(str, Enum):
    """The unsubscribe mechanism a marketing SMS must carry in a country."""

    SHORT_CODE = "short_code"
    LINK = "link"
