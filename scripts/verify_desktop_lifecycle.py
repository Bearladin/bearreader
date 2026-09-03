#!/usr/bin/env python
"""Deterministic checks for the desktop lease and external-link boundary."""

from contextlib import contextmanager
import time
from typing import Iterator

from lncrawl.server import lifecycle, webview
from lncrawl.services.desktop import validate_external_url


@contextmanager
def patched(obj: object, name: str, value: object) -> Iterator[None]:
    original = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, original)


def verify_session_binding() -> None:
    lifecycle.configure_session("expected")
    assert not lifecycle.mark_ready("stale")
    assert not lifecycle.mark_heartbeat("stale")
    assert not lifecycle.mark_bye("stale")
    assert not lifecycle.ready_received()
    assert lifecycle.heartbeat_age() is None

    assert lifecycle.mark_ready("expected")
    assert lifecycle.mark_heartbeat("expected")
    assert lifecycle.ready_received()
    assert lifecycle.heartbeat_recent()
    assert not lifecycle.closing_requested()
    assert lifecycle.mark_bye("expected")
    assert lifecycle.closing_requested()
    assert lifecycle.mark_heartbeat("expected")
    assert not lifecycle.closing_requested(), "a post-reload beat must supersede bye"


def verify_keep_alive_fallback() -> None:
    lifecycle.configure_session("lease")
    lifecycle.mark_ready("lease")
    lifecycle.mark_heartbeat("lease")
    lifecycle.last_heartbeat_at = time.monotonic() - webview.HEARTBEAT_LOST_AFTER - 1
    with (
        patched(webview, "_find_trusted_app_window", lambda *_args: None),
        patched(webview, "_trusted_browser_pids", lambda *_args: set()),
    ):
        started = time.monotonic()
        webview._keep_alive("http://localhost/?app=1")
        assert time.monotonic() - started < 1

    lifecycle.configure_session("closed")
    lifecycle.mark_heartbeat("closed")
    lifecycle.mark_bye("closed")
    with (
        patched(webview, "_find_trusted_app_window", lambda *_args: None),
        patched(webview, "_trusted_browser_pids", lambda *_args: {123}),
    ):
        started = time.monotonic()
        webview._keep_alive(
            "http://localhost/?app=1",
            initial_trusted_hwnd=123,
        )
        assert time.monotonic() - started < 1


def verify_external_url_boundary() -> None:
    assert validate_external_url("https://example.com/book") == "https://example.com/book"
    assert validate_external_url("http://127.0.0.1:8181/") == "http://127.0.0.1:8181/"
    for rejected in (
        "file:///C:/Windows/notepad.exe",
        "javascript:alert(1)",
        "https://user:secret@example.com/",
        "https://example.com/\nfile:///C:/Windows/notepad.exe",
        "not a URL",
    ):
        try:
            validate_external_url(rejected)
        except Exception:
            pass
        else:
            raise AssertionError(f"unsafe external URL accepted: {rejected}")


def main() -> None:
    verify_session_binding()
    verify_keep_alive_fallback()
    verify_external_url_boundary()
    print("DESKTOP LIFECYCLE CHECK: PASS")


if __name__ == "__main__":
    main()
