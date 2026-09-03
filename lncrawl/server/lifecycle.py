"""Small desktop-page lease shared by FastAPI and the native launcher.

The native window remains the primary liveness signal.  This module only
provides a session-bound fallback for Chromium launcher hand-off and the
system-browser fallback, where no trustworthy HWND may be available.
"""

from __future__ import annotations

import time

expected_session: str = ""
last_ready_session: str = ""
last_ready_at: float = 0.0
last_heartbeat_session: str = ""
last_heartbeat_at: float = 0.0
last_bye_at: float = 0.0


def configure_session(session_id: str) -> None:
    """Bind lifecycle beacons to the unpredictable launcher-issued session."""
    global expected_session, last_ready_session, last_ready_at
    global last_heartbeat_session, last_heartbeat_at, last_bye_at
    expected_session = session_id
    last_ready_session = ""
    last_ready_at = 0.0
    last_heartbeat_session = ""
    last_heartbeat_at = 0.0
    last_bye_at = 0.0


def _matches(session_id: str) -> bool:
    return bool(expected_session) and session_id == expected_session


def mark_bye(session_id: str) -> bool:
    global last_bye_at
    if not _matches(session_id):
        return False
    last_bye_at = time.monotonic()
    return True


def mark_ready(session_id: str) -> bool:
    global last_ready_session, last_ready_at
    if not _matches(session_id):
        return False
    last_ready_session = session_id
    last_ready_at = time.monotonic()
    return True


def mark_heartbeat(session_id: str) -> bool:
    global last_heartbeat_session, last_heartbeat_at, last_bye_at
    if not _matches(session_id):
        return False
    last_heartbeat_session = session_id
    last_heartbeat_at = time.monotonic()
    last_bye_at = 0.0
    return True


def heartbeat_age(now: float | None = None) -> float | None:
    if last_heartbeat_session != expected_session or last_heartbeat_at <= 0:
        return None
    return (now if now is not None else time.monotonic()) - last_heartbeat_at


def heartbeat_recent(within: float = 10.0, now: float | None = None) -> bool:
    age = heartbeat_age(now)
    return age is not None and age <= within


def ready_received() -> bool:
    return last_ready_session == expected_session and last_ready_at > 0


def closing_requested() -> bool:
    """True when bye is newer than the last beat (close, not a completed reload)."""
    return last_bye_at > 0 and last_bye_at >= last_heartbeat_at
