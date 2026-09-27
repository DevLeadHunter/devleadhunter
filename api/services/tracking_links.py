"""Stamp outbound demo/video links with a marketing-channel attribution param.

Each channel that pushes a prospect their demo link tags it with ``?src=<channel>``
(email / sms) so PostHog can attribute the demo visit to the channel it came from
— separate from the A/B ``?v=`` variant. An untagged link (a direct visit or a
bookmark) reads as « direct » on the tracking side.

SMS links take the branded short form instead (``https://host/s/<path>``): the demo
host redirects it to the page with ``?src=sms`` appended, so the SMS shows a clean
link with no visible tracking parameter — the pattern SMS providers recommend —
while the visit still lands attributed to the SMS channel.
"""

from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

CHANNEL_EMAIL: str = "email"
CHANNEL_SMS: str = "sms"

# Path prefix the demo host redirects to the same path stamped with ``?src=sms``.
SMS_SHORT_LINK_PREFIX: str = "/s/"


def sms_tracked_link(url: str) -> str:
    """Rewrite a demo-host URL to its SMS short form, ``https://host/s/<path>``.

    Args:
        url: A demo page or video page URL on the demo host.

    Returns:
        The same URL with its path prefixed by ``/s/`` (query and fragment kept).
    """
    parts = urlsplit(url)
    return urlunsplit(
        (parts.scheme, parts.netloc, f"{SMS_SHORT_LINK_PREFIX}{parts.path.lstrip('/')}", parts.query, parts.fragment)
    )


def email_tracked_link(url: str, variant: str | None = None) -> str:
    """Stamp a demo-host URL with the email channel, and with the A/B variant when the send has one.

    Args:
        url: A demo page or video page URL on the demo host.
        variant: The send's A/B variant ('A' / 'B'), or None outside an A/B campaign.

    Returns:
        The URL with ``?src=email`` appended, then ``&v=<variant>`` when there is one.
    """
    tagged = append_query_param(url, "src", CHANNEL_EMAIL)
    return append_query_param(tagged, "v", variant) if variant else tagged


def append_query_param(url: str, key: str, value: str) -> str:
    """Append ``key=value`` to *url*, choosing ``?`` or ``&`` as needed.

    Args:
        url: The base URL (may already carry a query string).
        key: Query parameter name.
        value: Query parameter value (ASCII, no escaping needed for our channels/variants).

    Returns:
        The URL with the parameter appended.
    """
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{key}={value}"
