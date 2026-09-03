from contextlib import suppress
import hashlib
import logging
import os
import secrets
import subprocess
import sys
from threading import Thread
import time
from typing import Optional
from urllib.request import urlopen

from scraper import find_chromium

from ..context import ctx
from ..distribution import DISTRIBUTION
from ..enums import UserRole
from ..startup_diagnostics import (
    StartupLogCapture,
    record_startup_failure,
    show_startup_failure,
)
from ..utils.platforms import Screen
from ..utils.sockets import free_port
from .lifecycle import (
    closing_requested,
    configure_session,
    heartbeat_age,
    heartbeat_recent,
    ready_received,
)

logger = logging.getLogger(__name__)

APP_NAME = DISTRIBUTION.display_name

# How long we allow the server to finish first-run work (migrations, seeding,
# source loading) before giving up and showing the error to the user.
READY_TIMEOUT = 120.0

# If the browser process dies within this window after launch, the window
# never actually opened; a launcher that hands off to a child process also
# exits within it, so this is a grace period, not a hard failure.
LAUNCH_GRACE = 10.0

HEARTBEAT_CLOSE_AFTER = 10.0
HEARTBEAT_LOST_AFTER = 15.0
RESUME_GRACE = 8.0
SERVER_STOP_TIMEOUT = 5.0
POLL_INTERVAL = 0.25
PROFILE_PID_REFRESH = 1.0

_SPINNER = "|/-\\"

_profile_pid_cache_at = 0.0
_profile_pid_cache: set[int] = set()


class FallbackException(Exception):
    """Raised when the app-mode window can't be used and we should fall back
    to opening the URL in the user's default browser."""


# ---------------------------------------------------------------------------
# Single-instance guard (Windows frozen desktop path only)
# ---------------------------------------------------------------------------


def _instance_digest() -> str:
    return hashlib.sha1(
        str(ctx.config.app.app_dir.resolve()).strip("\\/").lower().encode("utf-8")
    ).hexdigest()[:16]


def _instance_object_name(kind: str) -> str:
    return f"Global\\XiaoXiongNovel-{_instance_digest()}-{kind}"


class _InstanceSignals:
    """One-way second-launch request plus an acknowledgement for activation."""

    def __init__(self) -> None:
        self.request = None
        self.accepted = None
        if sys.platform != "win32":
            return
        import ctypes

        ctypes.windll.kernel32.CreateEventW.restype = ctypes.c_void_p
        self.request = ctypes.windll.kernel32.CreateEventW(
            None, False, False, _instance_object_name("activate")
        )
        self.accepted = ctypes.windll.kernel32.CreateEventW(
            None, False, False, _instance_object_name("activated")
        )

    def requested(self) -> bool:
        if self.request is None:
            return False
        import ctypes

        return ctypes.windll.kernel32.WaitForSingleObject(self.request, 0) == 0

    def acknowledge(self) -> None:
        if self.accepted is None:
            return
        import ctypes

        ctypes.windll.kernel32.SetEvent(self.accepted)


def _notify_existing_instance() -> bool:
    """Ask the old launcher to focus its live page or accelerate shutdown."""
    if sys.platform != "win32":
        return False
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.OpenEventW.restype = ctypes.c_void_p
    event_modify_state = 0x0002
    synchronize = 0x00100000
    request = kernel32.OpenEventW(event_modify_state, False, _instance_object_name("activate"))
    accepted = kernel32.OpenEventW(
        event_modify_state | synchronize, False, _instance_object_name("activated")
    )
    if not request or not accepted:
        if request:
            kernel32.CloseHandle(request)
        if accepted:
            kernel32.CloseHandle(accepted)
        return False
    try:
        kernel32.ResetEvent(accepted)
        kernel32.SetEvent(request)
        return kernel32.WaitForSingleObject(accepted, 1500) == 0
    finally:
        kernel32.CloseHandle(request)
        kernel32.CloseHandle(accepted)


def _acquire_single_instance_lock() -> "Optional[object]":
    """Return a named-mutex handle, or None when another instance already
    holds it for the same data directory.

    Only the frozen double-click desktop path calls this (manage_console=True
    from __init__.main); CLI invocations, the background tool and the LSP
    subprocess never reach here, and a different data directory (e.g. a test
    XIAOXIONG_NOVEL_DATA_PATH) gets its own mutex name. Windows releases the
    mutex automatically when the owning process exits — no lock files.
    """
    if sys.platform != "win32":
        return object()  # no-op guard on non-Windows dev machines

    import ctypes

    name = _instance_object_name("mutex")

    # ERROR_ALREADY_EXISTS = 183
    ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, name)
    if not handle:
        return object()  # API failure: don't block the app
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.kernel32.ReleaseMutex(handle)
        ctypes.windll.kernel32.CloseHandle(handle)
        return None
    return handle


# ---------------------------------------------------------------------------
# Console output helpers
# ---------------------------------------------------------------------------


def _write(message: str = "", end: str = "\n") -> None:
    try:
        print(message, end=end, flush=True)
    except (OSError, ValueError):
        pass


def _line(message: str = "") -> None:
    _write(message)


def _status(message: str) -> None:
    _line(f"  {message}")


def _banner() -> None:
    bar = "=" * 52
    _line()
    _line(bar)
    _line(f"  {APP_NAME}")
    _line(bar)
    _line()


# ---------------------------------------------------------------------------
# Windows console show/hide
# ---------------------------------------------------------------------------

_console_hidden = False


def _console_hwnd():
    if sys.platform != "win32":
        return None
    import ctypes

    with suppress(Exception):
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        return hwnd or None
    return None


def _owns_console() -> bool:
    """True when this process is the sole owner of its console window.

    An auto-created console (a frozen double-click launch) has exactly one
    attached process — us — so hiding it is safe. A console inherited from the
    user's terminal has more attached processes and must never be hidden."""
    if sys.platform != "win32":
        return False
    import ctypes

    with suppress(Exception):
        buffer = (ctypes.c_uint * 4)()
        count = ctypes.windll.kernel32.GetConsoleProcessList(buffer, 4)
        return count == 1
    return False


def _hide_console() -> None:
    global _console_hidden
    hwnd = _console_hwnd()
    if not hwnd:
        return
    import ctypes

    ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE  # type: ignore[attr-defined]
    _console_hidden = True


def _restore_console() -> None:
    """Bring a previously hidden console back so the user can read errors."""
    global _console_hidden
    if not _console_hidden:
        return
    hwnd = _console_hwnd()
    if hwnd:
        import ctypes

        ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW  # type: ignore[attr-defined]
        ctypes.windll.user32.SetForegroundWindow(hwnd)  # type: ignore[attr-defined]
    _console_hidden = False


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


def _start_server(
    host: str,
    port: int,
    startup_log_handler: StartupLogCapture,
    server_control: dict,
) -> None:
    from ..commands.server import run_server

    ctx.setup(
        log_level=0,
        reset_db_on_failure=True,
    )
    run_server(
        host=host,
        port=port,
        watch=False,
        workers=1,
        startup_log_handler=startup_log_handler,
        on_server_created=lambda server: server_control.__setitem__("server", server),
    )


def _stop_server(server_control: dict, server_thread: Thread) -> None:
    """Cooperatively stop desktop work, then give lifespan five seconds."""
    with suppress(Exception):
        if "scheduler" in ctx.__dict__:
            ctx.scheduler.request_desktop_shutdown()
    server = server_control.get("server")
    if server is not None:
        server.should_exit = True
    server_thread.join(timeout=SERVER_STOP_TIMEOUT)
    if server_thread.is_alive():
        logger.warning(
            f"Desktop cleanup exceeded {SERVER_STOP_TIMEOUT:.0f}s; "
            "the daemon server thread will end with this BearReader process"
        )


def _wait_for_ready(
    host: str,
    port: int,
    server_error: dict,
    server_thread: Thread,
) -> None:
    """Block until the server answers /health, or raise with a clear reason.

    A /health 200 is only served after the lifespan's ctx.setup() completes, so
    it doubles as the readiness signal and removes the token-generation race."""
    url = f"http://{host}:{port}/health"
    deadline = time.monotonic() + READY_TIMEOUT
    last_error: Optional[BaseException] = None
    frame = 0

    _write("  Starting the server  ", end="")
    while time.monotonic() < deadline:
        # Surface a crashed server thread immediately instead of timing out.
        error = server_error.get("error")
        if error is not None:
            _line()
            raise error

        try:
            with urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    _write("\r  Server is ready.            ")
                    return
        except Exception as e:
            last_error = e

        # The server can fail while the one-second health request is in flight.
        # Prefer its recorded exception over the connection error from this poll.
        error = server_error.get("error")
        if error is not None:
            _line()
            raise error

        # uvicorn swallows a lifespan-startup failure and returns without raising, so the
        # thread ends with no error set. Fail fast instead of polling a dead port for the
        # full timeout.
        if not server_thread.is_alive():
            _line()
            raise RuntimeError(
                "The server stopped before becoming ready; check the log above for the cause."
            ) from last_error

        _write(f"\r  Starting the server {_SPINNER[frame % len(_SPINNER)]} ", end="")
        frame += 1
        time.sleep(0.2)

    _line()
    raise TimeoutError(
        f"The server did not become ready within {int(READY_TIMEOUT)} seconds."
    ) from last_error


def _build_url(host: str, port: int, session_id: str) -> str:
    token = ctx.users.generate_token(
        user=ctx.users.get_admin(),
        expiry_minutes=1 * 365 * 24 * 60,  # 1 year
        scopes=[UserRole.LOCAL],
    )
    return f"http://{host}:{port}/?authToken={token}&app=1&appSession={session_id}"


# ---------------------------------------------------------------------------
# Window launchers
# ---------------------------------------------------------------------------


def _launch_app_window(
    url: str,
    manage_console: bool,
    instance_signals: _InstanceSignals,
) -> None:
    binaries = find_chromium()
    if not binaries:
        raise FallbackException("No Chromium-based browser found")

    storage_path = ctx.config.app.app_dir / "app-browser"
    width = min(1400, Screen.view_width - 20)
    height = min(1000, Screen.view_height - 80)

    # Try every installed Chromium in turn: one broken install (e.g. a missing
    # VC++ runtime, WinError 14001) must not block a healthy one.
    proc = None
    launched_binary = ""
    last_error: Optional[BaseException] = None
    for binary in binaries:
        args = [
            str(binary),
            f"--app={url}",
            "--new-window",
            f"--window-size={width},{height}",
            f"--user-data-dir={storage_path}",
            "--no-first-run",
            "--no-default-browser-check",
            # 标题栏跟随系统深色模式时会显示为黑色；强制浅色外观，
            # 与应用内 iOS 浅色主题观感统一（原生标题栏无法直接设为品牌蓝）。
            "--force-light-mode",
            # 应用模式窗口用不到 Edge 的旁路功能；这些组件/更新缓存在
            # --user-data-dir 里能积累到数百 MB，让应用数据目录严重虚胖。
            # 只禁旁路组件（钱包/购物/视觉搜索模型/组件更新缓存），
            # 页面渲染、Cookie、登录态、Safe Browsing 均不受影响；
            # 这些开关若被未来 Edge 版本忽略，后果只是体积回升，功能无损。
            "--disable-features=msEdgeWallet,msShoppingAssistant,msEntityExtraction,ComponentUpdates",
            "--disable-component-update",
            "--disable-background-networking",
        ]
        try:
            logger.info(f"Opening app-mode browser: {binary}")
            proc = subprocess.Popen(args)
            launched_binary = str(binary)
            break
        except OSError as error:
            last_error = error
            logger.warning(f"Failed to launch browser {binary}: {error}")
    if proc is None:
        raise FallbackException(f"No Chromium-based browser could be launched: {last_error}")
    logger.info(f"Started app (pid={proc.pid})")

    # A browser launcher may hand its window to a child process and exit; the
    # window can be open even though the launched process is gone. Do not judge
    # failure from the launcher's exit: watch for the app window instead.
    grace_deadline = time.monotonic() + LAUNCH_GRACE
    trusted_hwnd: Optional[int] = None
    while time.monotonic() < grace_deadline:
        trusted_hwnd = _find_trusted_app_window(proc)
        if trusted_hwnd is not None:
            break
        code = proc.poll()
        if code is not None:
            logger.warning(f"Browser launcher exited early (code={code})")
            _keep_alive(
                url,
                instance_signals=instance_signals,
                launch_diagnostic=f"Launcher: {launched_binary}; exit code: {code}.",
            )
            return
        time.sleep(0.1)

    _line()
    _status("The application is now open in a separate window.")
    if manage_console and _owns_console():
        _status("This console will hide. Closing the app window stops the server.")
        _hide_console()
    else:
        _status("Keep this window open. Closing it stops the server.")

    _keep_alive(
        url,
        proc=proc,
        instance_signals=instance_signals,
        initial_trusted_hwnd=trusted_hwnd,
    )
    logger.info(f"Closed app (pid={proc.pid})")


def _notify_url(url: str) -> None:
    """Tell the user where the app is when no window ever appeared."""
    message = f"应用窗口未能自动打开。\n\n请在浏览器地址栏访问：\n{url}\n\n服务器会保持运行，直到你关闭本程序。"
    if sys.stdin is None:
        import ctypes

        # Non-blocking: auto-dismiss after 5 seconds so the launcher-exit
        # misjudgement can never leave a modal box stuck behind the app window.
        def _show() -> None:
            ctypes.windll.user32.MessageBoxTimeoutW(None, message, APP_NAME, 0x40, 0, 5000)

        Thread(target=_show, daemon=True).start()
    else:
        _line()
        _status(f"Open the app in your browser: {url}")


def _profile_browser_pids() -> set[int]:
    """Query app-profile owners without flashing a PowerShell window."""
    global _profile_pid_cache_at, _profile_pid_cache
    now = time.monotonic()
    if now - _profile_pid_cache_at < PROFILE_PID_REFRESH:
        return set(_profile_pid_cache)
    _profile_pid_cache_at = now

    profile = str((ctx.config.app.app_dir / "app-browser").resolve()).replace("'", "''")
    script = (
        f"$profile = '{profile}'; "
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -match '^(msedge|chrome|msedgeproxy)\\.exe$' -and "
        "$_.CommandLine -like ('*' + $profile + '*') "
        "} | Select-Object -ExpandProperty ProcessId"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            capture_output=True,
            timeout=3,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode == 0:
            output = result.stdout.decode("utf-8", errors="replace")
            _profile_pid_cache = {
                int(line) for line in output.splitlines() if line.strip().isdigit()
            }
    except (OSError, subprocess.SubprocessError):
        logger.debug("Could not refresh app-profile browser PIDs", exc_info=True)
    return set(_profile_pid_cache)


def _trusted_browser_pids(proc: "Optional[subprocess.Popen]" = None) -> set[int]:
    """Return Chromium processes in this BearReader launcher's process tree."""
    if sys.platform != "win32":
        return {proc.pid} if proc is not None and proc.poll() is None else set()
    import ctypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_uint32),
            ("cntUsage", ctypes.c_uint32),
            ("th32ProcessID", ctypes.c_uint32),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", ctypes.c_uint32),
            ("cntThreads", ctypes.c_uint32),
            ("th32ParentProcessID", ctypes.c_uint32),
            ("pcPriClassBase", ctypes.c_int32),
            ("dwFlags", ctypes.c_uint32),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if snapshot in (-1, 0, 0xFFFFFFFF, ctypes.c_void_p(-1).value):
        return set()

    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)

    children: dict[int, list[int]] = {}
    edges: set[int] = set()
    ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
    while ok:
        pid = entry.th32ProcessID
        exe = entry.szExeFile.lower()
        if exe in ("msedge.exe", "chrome.exe", "msedgeproxy.exe"):
            edges.add(pid)
        children.setdefault(entry.th32ParentProcessID, []).append(pid)
        ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    kernel32.CloseHandle(snapshot)

    # Seed the launched PID even after it exits: Windows keeps that PID as the
    # parent id on surviving Chromium children, which is the common launcher
    # hand-off case this function must follow.
    frontier = [os.getpid()]
    if proc is not None:
        frontier.append(proc.pid)
    seen: set[int] = set()
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        frontier.extend(children.get(current, []))
    trusted = seen & edges
    if proc is not None and proc.poll() is None:
        trusted.add(proc.pid)
    trusted.update(_profile_browser_pids())
    return trusted


def _find_trusted_app_window(
    proc: "Optional[subprocess.Popen]" = None,
    known_hwnd: "Optional[int]" = None,
) -> "Optional[int]":
    """Find the exact BearReader HWND owned by this launcher's browser tree."""
    if sys.platform != "win32":
        return None
    import ctypes

    user32 = ctypes.windll.user32

    def _pid_for(hwnd: int) -> int:
        pid = ctypes.c_uint32()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)

    if known_hwnd and user32.IsWindow(known_hwnd) and user32.IsWindowVisible(known_hwnd):
        if not user32.IsHungAppWindow(known_hwnd):
            return known_hwnd

    trusted_pids = _trusted_browser_pids(proc)
    if not trusted_pids:
        return None

    found: Optional[int] = None

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _probe(hwnd, _):
        nonlocal found
        hwnd_value = int(hwnd or 0)
        if (
            not user32.IsWindowVisible(hwnd_value)
            or user32.IsHungAppWindow(hwnd_value)
            or _pid_for(hwnd_value) not in trusted_pids
        ):
            return True
        buffer = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd_value, buffer, 256)
        title = buffer.value
        if title == APP_NAME or title.startswith(f"{APP_NAME} v"):
            found = hwnd_value
            return False
        return True

    user32.EnumWindows(_probe, 0)
    return found


def _focus_window(hwnd: int) -> None:
    if sys.platform != "win32":
        return
    import ctypes

    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)


def _keep_alive(
    url: str,
    proc: "Optional[subprocess.Popen]" = None,
    instance_signals: "Optional[_InstanceSignals]" = None,
    initial_trusted_hwnd: "Optional[int]" = None,
    launch_diagnostic: str = "",
) -> None:
    """Keep the server alive from trusted HWND evidence or a soft page lease."""
    notified = False
    started = time.monotonic()
    last_poll = started
    resume_grace_until = started
    trusted_hwnd = initial_trusted_hwnd
    trusted_window_seen = trusted_hwnd is not None
    page_seen = trusted_window_seen

    while True:
        now = time.monotonic()
        if now - last_poll > HEARTBEAT_LOST_AFTER:
            # The monitor itself was suspended (sleep/lock/RDP transition).
            # Give the page time to emit its focus/pageshow recovery beat.
            resume_grace_until = now + RESUME_GRACE
        last_poll = now

        found_hwnd = _find_trusted_app_window(proc, trusted_hwnd)
        if found_hwnd is not None:
            trusted_hwnd = found_hwnd
            trusted_window_seen = True
            page_seen = True
        browser_alive = bool(_trusted_browser_pids(proc))

        if instance_signals is not None and instance_signals.requested():
            if closing_requested():
                logger.info("Second launch accelerated a pending desktop close")
                return
            if found_hwnd is not None:
                _focus_window(found_hwnd)
                instance_signals.acknowledge()
            elif heartbeat_recent(now=now):
                # Chromium handed the window to a process outside our tree;
                # the live lease still proves an existing page owns this run.
                instance_signals.acknowledge()
            else:
                logger.info("Second launch requested takeover after the app window closed")
                return

        if trusted_window_seen and found_hwnd is None:
            if closing_requested() or not browser_alive:
                return

        age = heartbeat_age(now)
        if ready_received() or age is not None:
            page_seen = True
        if found_hwnd is None and now >= resume_grace_until and age is not None:
            if closing_requested() and age > HEARTBEAT_CLOSE_AFTER:
                return
            if age > HEARTBEAT_LOST_AFTER:
                return

        if not page_seen and not notified and now - started > 20:
            notified = True
            record_startup_failure(
                "browser-window",
                "The browser launcher returned, but no BearReader window appeared within "
                f"20 seconds. {launch_diagnostic}".strip(),
            )
            _notify_url(url)
        elif not page_seen and now - started > 300:
            return  # never opened; wrap up
        time.sleep(POLL_INTERVAL)


def _run_in_system_browser(url: str, instance_signals: _InstanceSignals) -> None:
    _restore_console()
    _line()
    _status("Opening in your default web browser:")
    _line()
    _line(f"    {url}")
    _line()

    with suppress(Exception):
        import webbrowser

        webbrowser.open(url)

    _status("The server is running. Keep this window open to keep it running.")
    if sys.stdin is not None:
        with suppress(EOFError, KeyboardInterrupt, RuntimeError):
            input("  Press Enter to stop the server... ")
        return
    # Windowed build: watch the browser tab like the app-mode path does, so
    # closing the tab shuts the server down instead of lingering forever
    # (previously `while True: sleep(3600)` left a task-manager-only zombie).
    _keep_alive(url, instance_signals=instance_signals)


def _fatal(
    message: str,
    error: BaseException,
    captured_logs: str = "",
) -> None:
    _restore_console()
    logger.error(message, exc_info=error)
    log_path = record_startup_failure(
        "desktop-launcher",
        message,
        error=error,
        captured_logs=captured_logs,
    )
    _line()
    _line("  " + "-" * 48)
    _status(f"[ERROR] {message}")
    _status(f"Reason: {error}")
    if log_path is not None:
        _status(f"Diagnostic log: {log_path}")
    _line("  " + "-" * 48)
    _line()
    show_startup_failure("BearReader 启动失败。", log_path)
    _status("The application could not start. Review the messages above.")
    if sys.stdin is not None:
        with suppress(EOFError, KeyboardInterrupt, RuntimeError):
            input("  Press Enter to close... ")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def start(manage_console: bool = False) -> None:
    """Launch the desktop app.

    The console is hidden as early as possible so the startup window does not
    linger on a frozen double-click launch; any failure restores it via
    _fatal. The console is hidden only when we own it — see _owns_console.
    Pass manage_console=True from the frozen double-click path; leave it False
    when invoked from a real terminal (`lncrawl app`) so the user's shell is
    never hidden."""
    capture = StartupLogCapture()
    instance_signals = _InstanceSignals()
    if manage_console:
        # Frozen double-click path: refuse to run alongside another desktop
        # instance on the same data directory (scheduler/SQLite corruption).
        if _acquire_single_instance_lock() is None:
            if _notify_existing_instance():
                capture.close()
                return
            # A closed instance was told to skip its heartbeat fallback. Poll
            # frequently so a normal five-second cleanup feels like one launch.
            _status("正在等待上一个实例退出…")
            takeover = False
            deadline = time.monotonic() + 8.0
            while time.monotonic() < deadline:
                time.sleep(POLL_INTERVAL)
                if _acquire_single_instance_lock() is not None:
                    takeover = True
                    break
            if not takeover:
                capture.close()
                _restore_console()
                _line()
                _status("程序已经在运行。")
                _line()
                # The launcher console hides quickly — a silent exit here
                # reads as "double-click does nothing" (user report: app
                # would not open after a previous unclean exit). Show a
                # modal, self-dismissing box so the user knows what to do.
                message = (
                    "BearReader 已在运行，或上次未正常退出。\n\n"
                    "请先结束所有 BearReader 进程（任务管理器中结束 BearReader.exe / "
                    "backendtool.exe），或重启电脑后再试。"
                )
                if sys.stdin is None:
                    import ctypes

                    def _show() -> None:
                        ctypes.windll.user32.MessageBoxTimeoutW(
                            None, message, APP_NAME, 0x30, 0, 15000
                        )

                    Thread(target=_show, daemon=True).start()
                    time.sleep(16)
                record_startup_failure("single-instance", message)
                return

    if manage_console and _owns_console():
        _hide_console()

    _banner()

    host = "localhost"
    port = free_port(host, 31580)

    server_error: dict = {}
    server_control: dict = {}

    def _run_server() -> None:
        try:
            _start_server(host, port, capture, server_control)
        except BaseException as e:
            server_error["error"] = e
            logger.exception("Server thread crashed")

    server_thread = Thread(daemon=True, name="server", target=_run_server)
    server_thread.start()

    try:
        _wait_for_ready(host, port, server_error, server_thread)
        session_id = secrets.token_urlsafe(24)
        configure_session(session_id)
        url = _build_url(host, port, session_id)
    except Exception as e:
        _fatal("The server failed to start.", e, capture.text())
        capture.close()
        return
    capture.close()

    _status("Opening the application window...")
    try:
        _launch_app_window(url, manage_console, instance_signals)
    except FallbackException as e:
        logger.info(f"App-mode window unavailable: {e}")
        _run_in_system_browser(url, instance_signals)
    except Exception:
        logger.exception("App window error")
        _restore_console()
        _status("Could not open the app window; using your default browser instead.")
        _run_in_system_browser(url, instance_signals)
    finally:
        _stop_server(server_control, server_thread)
