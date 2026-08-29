#!/usr/bin/env python3

from contextlib import suppress
import os
import sys

# For encoding: the console build prints Chinese logs; a non-Chinese system
# defaults to cp1252 which cannot encode them. UTF-8 encodes everything, and
# errors="replace" guarantees output can never crash the app.
with suppress(Exception):
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")

# For executable bundles
is_frozen = bool(__package__ and getattr(sys, "frozen", False))
if is_frozen:
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

    with suppress(Exception):
        import multiprocessing

        multiprocessing.freeze_support()

# Remove colors from terminal (Windows frozen builds and CI environments don't support ANSI)
if os.getenv("CI") or (is_frozen and sys.platform == "win32"):
    os.environ["TERM"] = "dumb"
    os.environ["NO_COLOR"] = "1"

# The windowed frozen build has no console; give stray prints a sink instead of
# None. The sink must accept every character: without an explicit encoding the
# default follows the system locale, and a non-Chinese system (cp1252) cannot
# encode the Chinese app name, crashing launch with UnicodeEncodeError.
if is_frozen and sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
    sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")


def main():
    if os.environ.get("LNCRAWL_PYLSP") == "1":
        # Start pylsp server
        from pylsp import __main__ as _pylsp_main

        _pylsp_main.main()
    elif is_frozen and len(sys.argv) <= 1:
        # No CLI args: double-click launch — start the GUI
        from .server.webview import start

        start(manage_console=True)
    else:
        # Start main app
        from .app import app

        app()


if __name__ == "__main__":
    main()
