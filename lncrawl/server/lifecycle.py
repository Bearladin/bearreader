"""Process-lifetime flags shared between the FastAPI app and the desktop
launcher (webview). Kept deliberately trivial — GIL makes these reads/writes
atomic enough for our single-process desktop use.
"""

from __future__ import annotations

import time

# Set when the frontend page signals "window is being closed" via
# navigator.sendBeacon('/api/app/bye'). The keep-alive loop treats a missing
# window title after this as an immediate exit instead of polling for 8s.
last_bye_at: float = 0.0


def mark_bye() -> None:
    global last_bye_at
    last_bye_at = time.monotonic()


def bye_received(within: float = 30.0) -> bool:
    return last_bye_at > 0 and (time.monotonic() - last_bye_at) <= within


# Diagnostics-only heartbeat state (2026-09-02, step 1 of the desktop
# lifecycle rework): the app-mode page posts /api/app/heartbeat every 5s.
# Nothing consumes this yet for exit decisions — it exists so the next
# lifecycle step has real session data to build on.
last_ready_session: str = ""
last_heartbeat_session: str = ""
last_heartbeat_at: float = 0.0


def mark_ready(session_id: str) -> None:
    global last_ready_session
    last_ready_session = session_id


def mark_heartbeat(session_id: str) -> None:
    global last_heartbeat_session, last_heartbeat_at
    last_heartbeat_session = session_id
    last_heartbeat_at = time.monotonic()
