"""French legal send window for marketing SMS — a HARD guardrail.

Marketing SMS in France is allowed Mon–Fri 08:00–20:00 and Sat 10:00–19:00,
and NEVER on Sunday or a public holiday. This is the law, not a user preference:
whatever an operator configures, a send outside this window is refused and
deferred to the next legal slot. Public holidays are the French national ones
(métropole).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

try:  # Timezone-aware « now » when the tz database is present (prod always is).
    from zoneinfo import ZoneInfo

    _PARIS_TZ: ZoneInfo | None = ZoneInfo("Europe/Paris")
except Exception:
    _PARIS_TZ = None


def paris_to_utc_naive(moment: datetime) -> datetime:
    """Convert a naive Europe/Paris datetime to naive UTC (identity when tzdata is unavailable).

    Args:
        moment: A naive local (Paris) datetime.

    Returns:
        The same instant as a naive UTC datetime — the API's storage convention.
    """
    if _PARIS_TZ is None:
        return moment
    return moment.replace(tzinfo=_PARIS_TZ).astimezone(UTC).replace(tzinfo=None)


def utc_to_paris_naive(moment: datetime) -> datetime:
    """Convert a naive UTC datetime to naive Europe/Paris (identity when tzdata is unavailable).

    Args:
        moment: A naive UTC datetime.

    Returns:
        The same instant as a naive local (Paris) datetime, for window checks.
    """
    if _PARIS_TZ is None:
        return moment
    return moment.replace(tzinfo=UTC).astimezone(_PARIS_TZ).replace(tzinfo=None)


def now_in_paris() -> datetime:
    """Current Europe/Paris local time, as a naive datetime for the window check.

    The window hours are French local time, but the server runs in UTC — so the
    check must be made in Paris time, not UTC.

    Returns:
        The current local (Paris) time; naive-UTC as a best-effort fallback when
        the timezone database is unavailable.
    """
    if _PARIS_TZ is not None:
        return datetime.now(_PARIS_TZ).replace(tzinfo=None)
    return datetime.now(UTC).replace(tzinfo=None)


# Weekday (0 = Monday … 6 = Sunday) → (open, close) local time; missing = closed.
_WINDOWS: dict[int, tuple[time, time]] = {
    0: (time(8, 0), time(20, 0)),
    1: (time(8, 0), time(20, 0)),
    2: (time(8, 0), time(20, 0)),
    3: (time(8, 0), time(20, 0)),
    4: (time(8, 0), time(20, 0)),
    5: (time(10, 0), time(19, 0)),  # Saturday
    # Sunday (6) intentionally absent.
}


def _easter_sunday(year: int) -> date:
    """Easter Sunday for *year* (Anonymous Gregorian algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    month, day = divmod(h + m - 7 * n + 114, 31)
    return date(year, month, day + 1)


def french_public_holidays(year: int) -> set[date]:
    """French national public holidays (métropole) for *year*.

    Args:
        year: The calendar year.

    Returns:
        The set of holiday dates.
    """
    easter = _easter_sunday(year)
    return {
        date(year, 1, 1),  # Jour de l'an
        easter + timedelta(days=1),  # Lundi de Pâques
        date(year, 5, 1),  # Fête du Travail
        date(year, 5, 8),  # Victoire 1945
        easter + timedelta(days=39),  # Ascension
        easter + timedelta(days=50),  # Lundi de Pentecôte
        date(year, 7, 14),  # Fête nationale
        date(year, 8, 15),  # Assomption
        date(year, 11, 1),  # Toussaint
        date(year, 11, 11),  # Armistice 1918
        date(year, 12, 25),  # Noël
    }


def is_within_window(moment: datetime) -> bool:
    """Whether *moment* is inside the legal marketing-SMS window.

    Args:
        moment: A local (Europe/Paris) datetime.

    Returns:
        ``True`` when a marketing SMS may legally be sent at *moment*.
    """
    if moment.date() in french_public_holidays(moment.year):
        return False
    window = _WINDOWS.get(moment.weekday())
    if window is None:
        return False
    return window[0] <= moment.time() < window[1]


def next_send_slot(moment: datetime) -> datetime:
    """The earliest legal send time at or after *moment*.

    Args:
        moment: A local (Europe/Paris) datetime.

    Returns:
        *moment* itself when already legal, else the next window's opening time.
    """
    candidate = moment
    for _ in range(14):  # at most a couple of weeks of closed days
        if candidate.date() not in french_public_holidays(candidate.year):
            window = _WINDOWS.get(candidate.weekday())
            if window is not None:
                open_dt = candidate.replace(hour=window[0].hour, minute=window[0].minute, second=0, microsecond=0)
                close_dt = candidate.replace(hour=window[1].hour, minute=window[1].minute, second=0, microsecond=0)
                if candidate < open_dt:
                    return open_dt
                if candidate < close_dt:
                    return candidate
        # Past today's window (or a closed day): jump to the start of the next day.
        candidate = (candidate + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return candidate
