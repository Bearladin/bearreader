#!/usr/bin/env python3
import sys


def _run() -> None:
    try:
        from lncrawl import main

        main()
    except BaseException as error:
        if getattr(sys, "frozen", False) and len(sys.argv) <= 1:
            from lncrawl.startup_diagnostics import (
                record_startup_failure,
                show_startup_failure,
            )

            path = record_startup_failure(
                "entrypoint",
                "BearReader failed before the desktop launcher completed.",
                error=error,
            )
            show_startup_failure("BearReader 启动失败。", path)
        raise


_run()
