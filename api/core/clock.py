"""The current time as the database stores it: naive UTC."""

from datetime import UTC, datetime


def naive_utc_now() -> datetime:
    """
    The current time in UTC, without its time zone, as every stored date is written.

    Returns:
        A naive datetime holding the UTC time.
    """
    return datetime.now(UTC).replace(tzinfo=None)
