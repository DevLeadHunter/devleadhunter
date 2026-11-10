"""The visitor's IP address as the API sees it behind nginx, for the rate limits of public routes."""

from fastapi import Request


def client_ip(request: Request) -> str:
    """
    Best-effort visitor IP for rate limiting.

    nginx appends the address it saw to ``X-Forwarded-For``, so the last entry is the one a visitor cannot
    forge; the first one is whatever the visitor sent. Without a proxy, the socket peer is used.

    Args:
        request: The incoming request.

    Returns:
        The address, or ``unknown`` without one.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.rsplit(",", 1)[-1].strip()
    return request.client.host if request.client else "unknown"
