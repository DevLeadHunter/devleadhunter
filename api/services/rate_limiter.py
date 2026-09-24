"""In-memory sliding-window rate limiter for public endpoints.

A single API worker serves the public assistant endpoints, so a process-local limiter is
enough to blunt abuse (a bot hammering the LLM-backed chat). It is best-effort: it resets on
restart and does not span workers — it is a cost guard, not a security boundary.
"""

from __future__ import annotations

import time
from collections import deque

# Above this many tracked keys, the oldest are dropped so memory stays bounded under a flood.
_MAX_TRACKED_KEYS = 50_000


class SlidingWindowRateLimiter:
    """Allow at most ``max_events`` per ``window_seconds`` for each key."""

    def __init__(self, max_events: int, window_seconds: float) -> None:
        self._max_events = max_events
        self._window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}

    def allow(self, key: str) -> bool:
        """
        Record a hit for ``key`` and report whether it stays within the window budget.

        Args:
            key: The bucket identity (e.g. ``"<slug>:<ip>"``).

        Returns:
            True when the hit is allowed, False when the budget is exceeded.
        """
        now = time.monotonic()
        cutoff = now - self._window_seconds
        bucket = self._hits.get(key)
        if bucket is None:
            if len(self._hits) >= _MAX_TRACKED_KEYS:
                self._hits.clear()
            bucket = deque()
            self._hits[key] = bucket
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self._max_events:
            return False
        bucket.append(now)
        return True


# 30 messages / 5 min per visitor per assistant: roomy for a real conversation, caps a bot.
assistant_chat_limiter = SlidingWindowRateLimiter(max_events=30, window_seconds=300)

# 8 leads / 5 min per visitor per assistant: a real visitor leaves one, this caps spam.
assistant_lead_limiter = SlidingWindowRateLimiter(max_events=8, window_seconds=300)

# 6 photos / 10 min per visitor per assistant: 3 per quote request, each one costs a vision call.
assistant_photo_limiter = SlidingWindowRateLimiter(max_events=6, window_seconds=600)

# 5 checkouts / 5 min per visitor per assistant: each click creates a Stripe session, this caps a bot.
assistant_subscribe_limiter = SlidingWindowRateLimiter(max_events=5, window_seconds=300)
