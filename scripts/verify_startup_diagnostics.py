import logging
import logging.config
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from lncrawl import startup_diagnostics
from lncrawl.commands.server import _uvicorn_log_config
from lncrawl.server import webview


def _verify_server_error_wins_health_race() -> None:
    root_cause = FileExistsError("真实启动失败")

    class DelayedError(dict):
        calls = 0

        def get(self, key, default=None):
            self.calls += 1
            return None if self.calls == 1 else root_cause

    class StoppedThread:
        @staticmethod
        def is_alive() -> bool:
            return False

    original_urlopen = webview.urlopen
    try:

        def fail_health(*_args, **_kwargs):
            raise TimeoutError("健康检查超时")

        webview.urlopen = fail_health
        try:
            webview._wait_for_ready("127.0.0.1", 1, DelayedError(), StoppedThread())
        except FileExistsError as error:
            assert error is root_cause
        else:
            raise AssertionError("Health polling hid the server thread's startup exception")
    finally:
        webview.urlopen = original_urlopen


def verify() -> None:
    _verify_server_error_wins_health_race()
    previous = os.environ.get(startup_diagnostics.DATA_ENV)
    try:
        with TemporaryDirectory(prefix="bearreader-启动诊断-") as temporary:
            data_dir = Path(temporary) / "中文数据目录"
            os.environ[startup_diagnostics.DATA_ENV] = str(data_dir)

            capture = startup_diagnostics.StartupLogCapture().install()
            logging.getLogger("startup-verifier").error("中文启动日志")
            captured = capture.text()
            capture.close()
            assert "中文启动日志" in captured

            uvicorn_capture = startup_diagnostics.StartupLogCapture()
            logging.config.dictConfig(_uvicorn_log_config(uvicorn_capture))
            logging.getLogger("uvicorn.error").error("Uvicorn 中文启动故障")
            assert "Uvicorn 中文启动故障" in uvicorn_capture.text()
            uvicorn_capture.close()

            try:
                raise RuntimeError("中文路径故障注入")
            except RuntimeError as error:
                path = startup_diagnostics.record_startup_failure(
                    "verification",
                    "故障注入",
                    error=error,
                    captured_logs=captured,
                )

            expected = data_dir / startup_diagnostics.LOG_NAME
            assert path == expected
            content = expected.read_text(encoding="utf-8")
            assert "utf8_mode:" in content
            assert "中文启动日志" in content
            assert "中文路径故障注入" in content
            assert str(data_dir) in content

            expected.write_bytes(b"x" * startup_diagnostics.MAX_LOG_BYTES)
            startup_diagnostics.record_startup_failure("rotation", "轮转验证")
            backup = expected.with_name(f"{expected.name}.1")
            assert backup.stat().st_size == startup_diagnostics.MAX_LOG_BYTES
            assert "轮转验证" in expected.read_text(encoding="utf-8")

            original_gettempdir = startup_diagnostics.gettempdir
            try:
                startup_diagnostics.gettempdir = lambda: temporary
                os.environ[startup_diagnostics.DATA_ENV] = "~definitely-no-such-user/startup"
                fallback = startup_diagnostics.record_startup_failure(
                    "fallback",
                    "无效主目录回退验证",
                )
                assert fallback == Path(temporary) / f"BearReader-{startup_diagnostics.LOG_NAME}"
                assert "无效主目录回退验证" in fallback.read_text(encoding="utf-8")
            finally:
                startup_diagnostics.gettempdir = original_gettempdir
    finally:
        if previous is None:
            os.environ.pop(startup_diagnostics.DATA_ENV, None)
        else:
            os.environ[startup_diagnostics.DATA_ENV] = previous


if __name__ == "__main__":
    verify()
    print("Verified UTF-8 startup diagnostics and log rotation.")
