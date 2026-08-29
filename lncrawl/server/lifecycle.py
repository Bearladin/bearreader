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
