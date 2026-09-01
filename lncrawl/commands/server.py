from __future__ import annotations

from copy import deepcopy
import logging
import os
from typing import Any, Optional

import typer
from typing_extensions import Annotated

from ..context import ctx

app = typer.Typer()


def _uvicorn_log_config(handler: Optional[logging.Handler]) -> Any:
    from uvicorn.config import LOGGING_CONFIG

    config = deepcopy(LOGGING_CONFIG)
    if handler is not None:
        config["handlers"]["startup_capture"] = {"()": lambda: handler}
        config["loggers"]["uvicorn"]["handlers"].append("startup_capture")
    return config


def run_server(
    host: str,
    port: int,
    watch: bool,
    workers: int,
    startup_log_handler: Optional[logging.Handler] = None,
) -> None:
    import uvicorn

    options: dict[str, Any] = {
        "port": port,
        "host": host,
        "access_log": ctx.logger.is_debug,
        "log_level": ctx.logger.level or "error",
        "use_colors": os.getenv("NO_COLOR") != "1",
        "log_config": _uvicorn_log_config(startup_log_handler),
    }
    if watch:
        uvicorn.run(
            "lncrawl.server.app:app",
            workers=workers,
            reload=True,
            **options,
        )
    else:
        from ..server.app import app as server_app

        uvicorn.run(server_app, **options)


@app.command(help="Run web server.")
def server(
    host: Annotated[str, typer.Option("-h", "--host", help="Server host")] = "0.0.0.0",
    port: Annotated[int, typer.Option("-p", "--port", help="Server port")] = 8181,
    watch: Annotated[bool, typer.Option("-w", "--watch", help="Run server in watch mode")] = False,
    workers: Annotated[int, typer.Option("-n", "--worker", help="Number of workers to run")] = 1,
) -> None:
    run_server(host, port, watch, workers)
