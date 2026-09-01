from contextlib import suppress
import hashlib
import logging
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
from .lifecycle import bye_received

logger = logging.getLogger(__name__)

APP_NAME = DISTRIBUTION.display_name

# How long we allow the server to finish first-run work (migrations, seeding,
# source loading) before giving up and showing the error to the user.
READY_TIMEOUT = 120.0

# If the browser process dies within this window after launch, the window
# never actually opened; a launcher that hands off to a child process also
# exits within it, so this is a grace period, not a hard failure.
LAUNCH_GRACE = 10.0

_SPINNER = "|/-\\"


class FallbackException(Exception):
    """Raised when the app-mode window can't be used and we should fall back
    to opening the URL in the user's default browser."""


# ---------------------------------------------------------------------------
# Single-instance guard (Windows frozen desktop path only)
# ---------------------------------------------------------------------------


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

    # Normalize the data directory so different string spellings of the same
    # folder (trailing slash, case) produce the same mutex name.
    digest = hashlib.sha1(
        str(ctx.config.app.app_dir.resolve()).strip("\\/").lower().encode("utf-8")
    ).hexdigest()[:16]
    name = f"Global\\XiaoXiongNovel-{digest}"

    # ERROR_ALREADY_EXISTS = 183
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


def _build_url(host: str, port: int) -> str:
    token = ctx.users.generate_token(
        user=ctx.users.get_admin(),
        expiry_minutes=1 * 365 * 24 * 60,  # 1 year
        scopes=[UserRole.LOCAL],
    )
    return f"http://{host}:{port}/?authToken={token}"


# ---------------------------------------------------------------------------
# Window launchers
# ---------------------------------------------------------------------------


def _launch_app_window(url: str, manage_console: bool) -> None:
    # Tag the app-mode URL so the frontend can distinguish it from a plain
    # browser tab (fallback path) — only app-mode pages send the close beacon.
    url = url + "&app=1"
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
    while time.monotonic() < grace_deadline:
        code = proc.poll()
        if code is not None:
            logger.warning(f"Browser launcher exited early (code={code})")
            _keep_alive(
                url,
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

    # Primary exit signal is the browser process tree using our app profile
    # (see _keep_alive); the title match is only a fallback.
    _keep_alive(url, appeared_initial=True, proc=proc)
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


def _window_title_visible(title: str) -> bool:
    """True while any visible window or tab shows the app title.

    Hung foreign windows are skipped first: GetWindowTextW blocks on them,
    and one hung window would freeze the whole keep-alive loop (the 1.1.3
    gray-screen family of deadlocks).
    """
    import ctypes

    user32 = ctypes.windll.user32
    found = False

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _probe(hwnd, _):
        nonlocal found
        if not user32.IsWindowVisible(hwnd) or user32.IsHungAppWindow(hwnd):
            return True
        buffer = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buffer, 256)
        if title in buffer.value:
            found = True
            return False
        return True

    user32.EnumWindows(_probe, 0)
    return found


def _app_profile_running() -> bool:
    """True while any browser process still uses our app profile directory.

    Edge/Chrome app-mode windows may be hosted by a process other than the
    one we spawned (launcher handoff); every process of that window shares
    the --user-data-dir we passed, so scanning command lines for the profile
    path is a reliable "is our window's browser alive" check that never
    false-positives on unrelated windows.

    Implementation note: must NOT spawn powershell.exe — this runs every
    2 seconds and each child console flashes a black DOS window on the
    user's desktop. Pure Win32 via ctypes (NtQuerySystemInformation-style
    process snapshot) keeps it silent and cheap.
    """
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

    # We cannot read another process's command line without WMI, but we CAN
    # check the browser child(ren) of OUR process: Edge handoff keeps the
    # window inside processes that are our direct or transitive children.
    # Combine: (a) our spawned proc alive, or (b) any msedge.exe descendant.
    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if snapshot == -1 or snapshot == 0xFFFFFFFF:
        return False

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

    # BFS from our own pid looking for a browser process in the subtree
    import os

    frontier = [os.getpid()]
    seen: set[int] = set()
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        if current in edges:
            return True
        frontier.extend(children.get(current, []))
    return False


def _keep_alive(
    url: str,
    appeared_initial: bool = False,
    proc: "Optional[subprocess.Popen]" = None,
    launch_diagnostic: str = "",
) -> None:
    """The windowed build has no console input.

    Exit conditions, in priority order:
    1. The launched browser process (or its whole app-window process tree)
       is gone — the user closed the window. This is the PRIMARY signal; the
       global title match below is only a fallback and can false-positive on
       an unrelated window whose title happens to contain the app name
       (e.g. an Explorer window opened on the dist folder) — that false
       positive once kept a closed app "alive" and blocked relaunches.
    2. The page's closing beacon (bye) plus the title being gone — fast path
       that avoids waiting CLOSED_AFTER.
    3. The title staying unseen for CLOSED_AFTER seconds (fallback when the
       launcher process exited early but the window lives in a child).
    If nothing ever appeared, notify late and wind down after 5 minutes.
    """
    title = DISTRIBUTION.display_name
    appeared = appeared_initial
    notified = False
    started = time.monotonic()
    last_seen = started if appeared_initial else None
    # How long the title must stay unseen before we conclude the user closed
    # the window. 8s = 4 polling rounds; kept short so the single-instance
    # mutex of a relaunch doesn't block for long (was 20s).
    CLOSED_AFTER = 8.0
    # Zombie bailout: on some machines every exit signal misfires at once
    # (browser handed the window to an unrelated-looking process, title
    # probing finds a same-named foreign window, the bye beacon never
    # arrives). The loop must never hang forever holding the single-instance
    # mutex — after this long without a window sighting, wind down and let
    # the diagnostic tell the user what happened.
    ZOMBIE_AFTER = 10 * 60.0
    zombie_logged = False

    def _browser_alive() -> bool:
        # True while the browser we launched (or a descendant holding the
        # app window) is still running. Windows Popen.poll() only covers the
        # direct child; Edge hands the window to a sibling process sharing
        # the same --user-data-dir, so also scan for any process using it.
        if proc is not None and proc.poll() is None:
            return True
        return _app_profile_running()

    while True:
        if appeared and not _browser_alive():
            return  # our browser (window holder) is gone

        # Window-closing beacon: exits only when the page signalled bye AND
        # the title stays gone — a page refresh also fires beforeunload and
        # would otherwise kill a live app. Window probing is safe now
        # (IsHungAppWindow guard above), so the double check is enough.
        if appeared and bye_received() and not _window_title_visible(title):
            time.sleep(0.5)
            if bye_received() and not _window_title_visible(title):
                return

        found = _window_title_visible(title)
        now = time.monotonic()
        if found:
            appeared = True
            last_seen = now
        elif not appeared and not notified and now - started > 20:
            notified = True
            record_startup_failure(
                "browser-window",
                "The browser launcher returned, but no BearReader window appeared within "
                f"20 seconds. {launch_diagnostic}".strip(),
            )
            _notify_url(url)
        elif appeared and last_seen is not None and now - last_seen > CLOSED_AFTER:
            return  # the last window or tab was closed
        elif not appeared and now - started > 300:
            return  # never opened; wrap up
        elif (
            appeared
            and last_seen is not None
            and now - last_seen > ZOMBIE_AFTER
            and _browser_alive()
            and not zombie_logged
        ):
            # The window is long gone but the browser process tree still
            # holds our app profile: probe failure, not a live session.
            zombie_logged = True
            record_startup_failure(
                "keep-alive",
                "The app window has not been seen for "
                f"{int(ZOMBIE_AFTER / 60)} minutes while a browser process is still "
                "running with the app profile. Exiting to release the single-instance "
                "lock; if the window was actually open, it will reconnect to a "
                "restarted server.",
            )
            return
        time.sleep(2)


def _run_in_system_browser(url: str) -> None:
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
    _keep_alive(url, appeared_initial=True)


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
    if manage_console:
        # Frozen double-click path: refuse to run alongside another desktop
        # instance on the same data directory (scheduler/SQLite corruption).
        if _acquire_single_instance_lock() is None:
            # The previous instance may just have been closed and is still in
            # its ~10s wind-down — wait briefly and take over if it exits.
            _status("正在等待上一个实例退出…")
            takeover = False
            deadline = time.monotonic() + 12.0
            while time.monotonic() < deadline:
                time.sleep(1.5)
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

    def _run_server() -> None:
        try:
            _start_server(host, port, capture)
        except BaseException as e:
            server_error["error"] = e
            logger.exception("Server thread crashed")

    server_thread = Thread(daemon=True, name="server", target=_run_server)
    server_thread.start()

    try:
        _wait_for_ready(host, port, server_error, server_thread)
        url = _build_url(host, port)
    except Exception as e:
        _fatal("The server failed to start.", e, capture.text())
        capture.close()
        return
    capture.close()

    _status("Opening the application window...")
    try:
        _launch_app_window(url, manage_console)
    except FallbackException as e:
        logger.info(f"App-mode window unavailable: {e}")
        _run_in_system_browser(url)
    except Exception:
        logger.exception("App window error")
        _restore_console()
        _status("Could not open the app window; using your default browser instead.")
        _run_in_system_browser(url)
