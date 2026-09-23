"""Tests for the sliding-window rate limiter guarding the public assistant endpoints."""

import time

from services.rate_limiter import SlidingWindowRateLimiter


def test_allows_up_to_max_then_blocks() -> None:
    """The limiter allows ``max_events`` per key, then blocks further hits."""
    limiter = SlidingWindowRateLimiter(max_events=3, window_seconds=60)
    assert [limiter.allow("k") for _ in range(4)] == [True, True, True, False]


def test_keys_are_independent() -> None:
    """Each key carries its own budget."""
    limiter = SlidingWindowRateLimiter(max_events=1, window_seconds=60)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False


def test_window_expiry_frees_budget() -> None:
    """Once the window passes, a key is allowed again."""
    limiter = SlidingWindowRateLimiter(max_events=1, window_seconds=0.05)
    assert limiter.allow("k") is True
    assert limiter.allow("k") is False
    time.sleep(0.06)
    assert limiter.allow("k") is True
