"""Shared rate limiter instance.

Every module decorating an endpoint with ``@limiter.limit(...)`` must import this
instance rather than build its own: slowapi enforces limits against the storage of
the instance the decorator came from, so a second ``Limiter`` would silently keep
its own counters. ``main.py`` also publishes it as ``app.state.limiter``, which the
``RateLimitExceeded`` handler reads to inject the ``Retry-After`` headers.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
