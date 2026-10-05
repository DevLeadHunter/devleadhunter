"""
Desktop app presence — whether a user's desktop app is on to read the Facebook pages their searches wait for.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from core.clock import naive_utc_now

# The desktop app looks at the activity every 30 seconds, about once a minute when its window is
# hidden in the tray: three minutes without a look means the computer is off or the app is closed.
_ONLINE_WINDOW: timedelta = timedelta(minutes=3)


class DesktopAppPresence:
    """Remembers when each user's desktop app last looked at the search activity."""

    def __init__(self, online_window: timedelta = _ONLINE_WINDOW) -> None:
        self._online_window = online_window
        # Kept in the memory of the API process: it runs a single worker, the same one that runs the
        # searches. A restart forgets every app until its next look, half a minute later.
        self._last_seen_at: dict[int, datetime] = {}

    def mark_seen(self, user_id: int) -> None:
        """Record that the user's desktop app is on right now."""
        self._last_seen_at[user_id] = naive_utc_now()

    def is_online(self, user_id: int) -> bool:
        """Whether the user's desktop app looked at the activity recently enough to be on."""
        last_seen_at = self._last_seen_at.get(user_id)
        return last_seen_at is not None and naive_utc_now() - last_seen_at <= self._online_window


desktop_app_presence = DesktopAppPresence()
