"""
Resolve a usable Storyblok editor session on the machine where the sidecar runs.

The Storyblok Visual Editor is only reachable while authenticated as the space
owner (Léo). No per-space password exists (clients self-serve via an emailed
invite), so the sidecar must borrow an existing owner session from the desktop.

Cascade (decided with Léo, 2026-08-25):
  1. Reuse a browser session already on the machine — Storyblok keeps its auth
     JWT in the ``app.storyblok.com`` localStorage (key ``token``), not in a
     cookie, so we read it from the Firefox profile on disk (read-only copy to
     dodge the file lock) and inject it into a headless browser.
  2. Fall back to a dedicated persistent profile the app owns — the GoupixDex
     pattern (Amazon/Vinted/Cardmarket): the user signs in once via a headful
     window, the profile keeps the session, and a state file records it.
  3. If neither yields a session, the caller skips the editor sequence.

This module only *reads* sessions and reports state; the actual browser probing
and the editor capture live in ``storyblok_editor_clip_service`` (it owns
Playwright). Values (tokens) are never logged.
"""

from __future__ import annotations

import base64
import binascii
import glob
import json
import logging
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

StoryblokSessionState = Literal["ready", "needs_login", "busy", "unknown"]

# Storyblok stores its auth in localStorage; only these keys are pure-ASCII and
# needed. Firefox encodes other blobs in a way that corrupts on a naive read and
# crashes Storyblok's JSON.parse, so we never inject them — the app rebuilds them.
_SAFE_LOCALSTORAGE_KEYS: tuple[str, ...] = ("token", "d0_session")

_STORYBLOK_LS_ORIGIN_DIR = "https+++app.storyblok.com"
_SESSION_STATE_FILE = "storyblok-session.json"

# A token expiring within this margin is treated as stale: better to prompt a
# reconnect than to start a capture that dies on Storyblok's login page.
_TOKEN_EXPIRY_MARGIN_SEC = 120


def _jwt_expiry(token: str) -> int | None:
    """
    Read the ``exp`` (unix seconds) claim of a JWT without verifying its signature.

    Args:
        token: The raw ``app.storyblok.com`` auth token.

    Returns:
        The expiry timestamp, or None when the token is not a decodable JWT with
        an ``exp`` claim (older/opaque tokens fall through to presence-only checks).
    """
    parts = token.split(".")
    if len(parts) < 2:
        return None
    payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    except (binascii.Error, ValueError, json.JSONDecodeError):
        return None
    exp = payload.get("exp") if isinstance(payload, dict) else None
    try:
        return int(exp) if exp is not None else None
    except (TypeError, ValueError):
        return None


def _token_is_fresh(token: str) -> bool:
    """
    True when a token is present and not (about to be) expired.

    A token whose JWT ``exp`` cannot be read is assumed usable — presence is then
    the only signal available, and the capture-time login-page detection is the
    authoritative backstop.

    Args:
        token: The raw auth token.

    Returns:
        Whether the token should be trusted for a capture attempt.
    """
    if not token:
        return False
    expiry = _jwt_expiry(token)
    if expiry is None:
        return True
    return expiry > datetime.now(UTC).timestamp() + _TOKEN_EXPIRY_MARGIN_SEC


@dataclass
class StoryblokSessionSeed:
    """Everything needed to authenticate a fresh browser context to Storyblok.

    ``local_storage`` is injected on ``app.storyblok.com`` before its SPA boots;
    ``cookies`` are the (accessory) storyblok cookies. ``source`` is a short label
    for diagnostics ("firefox:<profile>" / "dedicated-profile").
    """

    local_storage: dict[str, str]
    cookies: list[dict] = field(default_factory=list)
    source: str = ""

    @property
    def has_token(self) -> bool:
        """True when the auth token is present (necessary, not sufficient — it may be expired)."""
        return bool(self.local_storage.get("token"))

    @property
    def is_valid(self) -> bool:
        """True when the token is present AND not expired (by its JWT ``exp`` claim)."""
        return _token_is_fresh(self.local_storage.get("token", ""))


class StoryblokSessionService:
    """Read reusable Storyblok owner sessions from the desktop and track their state."""

    def __init__(self, dedicated_profile_dir: Path | None = None) -> None:
        self._dedicated_profile_dir = dedicated_profile_dir or self.default_dedicated_profile_dir()

    # ── Machine browser session (cascade step 1) ─────────────────────────────

    def resolve_machine_seed(self) -> StoryblokSessionSeed | None:
        """Best Storyblok session found in the machine's browsers, or ``None``.

        Only Firefox is read today (Léo's browser); the return shape is browser
        agnostic so Chrome/Edge can be added without touching callers.
        """
        for profile in self._firefox_profiles_with_storyblok():
            seed = self._read_firefox_seed(profile)
            if not seed or not seed.has_token:
                continue
            # A present-but-expired token used to read as "ready" and then die on
            # Storyblok's login page mid-capture: only accept a still-fresh token.
            if not seed.is_valid:
                logger.info("Storyblok machine token found but expired (source=%s) — needs reconnect", seed.source)
                continue
            logger.info("Storyblok machine session found (source=%s)", seed.source)
            return seed
        return None

    def _firefox_profiles_with_storyblok(self) -> list[Path]:
        """Firefox profile dirs that hold an ``app.storyblok.com`` localStorage store."""
        base = os.path.expandvars(r"%APPDATA%\Mozilla\Firefox\Profiles")
        if not os.path.isdir(base):
            return []
        matches: list[Path] = []
        for entry in sorted(glob.glob(os.path.join(base, "*"))):
            ls = Path(entry) / "storage" / "default" / _STORYBLOK_LS_ORIGIN_DIR / "ls" / "data.sqlite"
            if ls.is_file():
                matches.append(Path(entry))
        return matches

    def _read_firefox_seed(self, profile_dir: Path) -> StoryblokSessionSeed | None:
        """Extract the auth localStorage + storyblok cookies from one Firefox profile."""
        local_storage = self._read_firefox_localstorage(profile_dir)
        if not local_storage.get("token"):
            return None
        cookies = self._read_firefox_cookies(profile_dir)
        return StoryblokSessionSeed(
            local_storage=local_storage,
            cookies=cookies,
            source=f"firefox:{profile_dir.name}",
        )

    def _read_firefox_localstorage(self, profile_dir: Path) -> dict[str, str]:
        """Read the safe (ASCII, auth) localStorage keys for ``app.storyblok.com``."""
        ls = profile_dir / "storage" / "default" / _STORYBLOK_LS_ORIGIN_DIR / "ls" / "data.sqlite"
        items: dict[str, str] = {}
        try:
            copied = self._copy_locked(ls)
            connection = sqlite3.connect(copied)
            try:
                for key, value in connection.execute("SELECT key, value FROM data"):
                    if key not in _SAFE_LOCALSTORAGE_KEYS:
                        continue
                    text = value.decode("ascii", "ignore") if isinstance(value, bytes) else str(value)
                    if text and "�" not in text:
                        items[key] = text
            finally:
                connection.close()
        except (OSError, sqlite3.Error) as exc:
            logger.debug("Firefox localStorage read failed for %s: %s", profile_dir.name, exc)
        return items

    def _read_firefox_cookies(self, profile_dir: Path) -> list[dict]:
        """Read storyblok cookies from the profile as Playwright-ready session cookies."""
        same_site = {0: "None", 1: "Lax", 2: "Strict"}
        cookies: list[dict] = []
        try:
            copied = self._copy_locked(profile_dir / "cookies.sqlite")
            connection = sqlite3.connect(copied)
            try:
                rows = connection.execute(
                    "SELECT host, name, value, path, isSecure, isHttpOnly, sameSite "
                    "FROM moz_cookies WHERE host LIKE '%storyblok%'"
                )
                for host, name, value, path, is_secure, is_http, ss in rows:
                    cookies.append(
                        {
                            "name": name,
                            "value": value,
                            "domain": host,
                            "path": path or "/",
                            "expires": -1,
                            "httpOnly": bool(is_http),
                            "secure": bool(is_secure),
                            "sameSite": same_site.get(ss, "Lax"),
                        }
                    )
            finally:
                connection.close()
        except (OSError, sqlite3.Error) as exc:
            logger.debug("Firefox cookies read failed for %s: %s", profile_dir.name, exc)
        return cookies

    @staticmethod
    def _copy_locked(path: Path) -> str:
        """Copy a (possibly locked) SQLite file to temp so we never touch the live DB."""
        destination = os.path.join(tempfile.gettempdir(), "sb_" + path.name)
        shutil.copy2(path, destination)
        return destination

    # ── Dedicated persistent profile (cascade step 2, GoupixDex pattern) ─────

    @staticmethod
    def default_dedicated_profile_dir() -> Path:
        """App-owned Storyblok browser profile (kept between runs so login persists)."""
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return Path(base) / "DevLeadHunter" / "storyblok-profile"

    @property
    def dedicated_profile_dir(self) -> Path:
        """The persistent profile directory used by the login helper and clip capture."""
        return self._dedicated_profile_dir

    def read_persisted_state(self) -> dict | None:
        """Return the last recorded dedicated-profile session info, or ``None``."""
        path = self._dedicated_profile_dir / _SESSION_STATE_FILE
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.debug("read_persisted_state: %s", exc)
            return None
        return data if isinstance(data, dict) else None

    def write_persisted_state(
        self, *, logged_in: bool, email: str | None = None, ignore_machine_seed: bool = False
    ) -> None:
        """
        Persist the dedicated-profile login state next to the profile (best-effort).

        Args:
            logged_in: Whether the dedicated profile now holds a signed-in session.
            email: Optional account email, for display.
            ignore_machine_seed: When True, the machine browser (Firefox) session must
                not be silently reused — set on an explicit logout, cleared on sign-in.
        """
        path = self._dedicated_profile_dir / _SESSION_STATE_FILE
        payload = {
            "logged_in": logged_in,
            "email": email,
            "ignore_machine_seed": ignore_machine_seed,
            "last_seen": datetime.now(UTC).isoformat(),
        }
        try:
            self._dedicated_profile_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("write_persisted_state: %s", exc)

    def logout(self) -> None:
        """
        Forget the Storyblok session so the user can reconnect with another account.

        Wipes the dedicated profile (its cookies/localStorage) and records that the
        machine browser (Firefox) session must NOT be silently reused — otherwise a
        wrong account still signed in there would come straight back. The next in-app
        sign-in clears that flag and takes precedence again.
        """
        profile = self._dedicated_profile_dir
        if profile.is_dir():
            for entry in profile.iterdir():
                if entry.name == _SESSION_STATE_FILE:
                    continue
                try:
                    if entry.is_dir():
                        shutil.rmtree(entry, ignore_errors=True)
                    else:
                        entry.unlink(missing_ok=True)
                except OSError as exc:
                    logger.debug("logout profile wipe (%s): %s", entry.name, exc)
        self.write_persisted_state(logged_in=False, ignore_machine_seed=True)

    def read_login_state_written_at(self) -> str | None:
        """The ``last_seen`` stamp of the saved login state, or ``None`` without one."""
        persisted = self.read_persisted_state()
        written_at = persisted.get("last_seen") if persisted else None
        return str(written_at) if written_at else None

    def mark_session_expired(self, *, login_state_written_at: str | None) -> bool:
        """
        Record that Storyblok refused the session a capture used, and set the browser session aside too.

        Args:
            login_state_written_at: ``read_login_state_written_at()`` as the capture picked its session.

        Returns:
            Whether the expiry was recorded: a sign-in saved since then is kept.
        """
        if self.read_login_state_written_at() != login_state_written_at:
            return False
        self.write_persisted_state(logged_in=False, ignore_machine_seed=True)
        logger.info("Storyblok refused the capture session: saved login marked expired")
        return True

    def resolve_capture_source(self) -> tuple[StoryblokSessionSeed | None, str | None]:
        """
        Pick the session a capture should use, or ``(None, None)`` when a login is needed.

        The in-app dedicated profile wins (so signing in there chooses the account);
        the machine browser session is only a convenience fallback, and it is skipped
        after an explicit logout so a wrong account left in the browser is never reused.

        Returns:
            ``(seed, None)`` to inject a machine seed, ``(None, user_data_dir)`` to use
            the dedicated profile, or ``(None, None)`` when neither is available.
        """
        persisted = self.read_persisted_state()
        if persisted and persisted.get("logged_in"):
            return None, str(self._dedicated_profile_dir)
        if not (persisted and persisted.get("ignore_machine_seed")):
            seed = self.resolve_machine_seed()
            if seed is not None:
                return seed, None
        return None, None

    # ── State summary for the UI ─────────────────────────────────────────────

    def state(self) -> StoryblokSessionState:
        """Best-effort connection state without launching a browser.

        ``ready`` when a usable capture source exists (dedicated profile login, or a
        fresh machine token that has not been explicitly disconnected); ``needs_login``
        otherwise. A live probe (which can also return ``busy``) is done by the login
        helper when a window is open.
        """
        seed, user_data_dir = self.resolve_capture_source()
        return "ready" if (seed is not None or user_data_dir is not None) else "needs_login"


storyblok_session_service = StoryblokSessionService()
