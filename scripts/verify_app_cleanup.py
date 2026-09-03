#!/usr/bin/env python
"""Verify close, immediate relaunch, and profile cleanup in the frozen app."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "dist" / "BearReader"
APP = BUNDLE / "BearReader.exe"
CREATE_NEW_CONSOLE = 0x00000010
CREATE_NO_WINDOW = 0x08000000


def _powershell(script: str, timeout: int = 10) -> str:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        capture_output=True,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )
    return result.stdout.decode("utf-8", errors="replace").strip()


def _find_app_window() -> tuple[int, int] | None:
    output = _powershell(
        "Get-Process | Where-Object { "
        "$_.ProcessName -match '^(msedge|chrome)$' -and "
        "$_.MainWindowTitle -like 'BearReader v*' "
        "} | Select-Object -First 1 | ForEach-Object { "
        'Write-Output "$($_.Id)|$($_.MainWindowHandle)" }'
    )
    if not output:
        return None
    try:
        pid, hwnd = output.split("|", 1)
        return int(pid), int(hwnd)
    except (TypeError, ValueError):
        return None


def _close_window(hwnd: int) -> None:
    _powershell(
        "Add-Type 'using System; using System.Runtime.InteropServices; "
        "public static class NativeClose { "
        '[DllImport("user32.dll")] public static extern bool PostMessage('
        "IntPtr h, uint m, IntPtr w, IntPtr l); }'; "
        f"[NativeClose]::PostMessage([IntPtr]{hwnd}, 0x0010, [IntPtr]::Zero, "
        "[IntPtr]::Zero) | Out-Null"
    )


def _find_browser_pids_for_profile(profile_dir: Path) -> list[int]:
    escaped = str(profile_dir).replace("'", "''")
    output = _powershell(
        "Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -match '^(msedge|chrome)\\.exe$' -and "
        f"$_.CommandLine -like '*{escaped}*' "
        "} | Select-Object -ExpandProperty ProcessId"
    )
    return [int(line) for line in output.splitlines() if line.strip().isdigit()]


def _wait_for_window(timeout: float) -> tuple[int, int] | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = _find_app_window()
        if found is not None:
            return found
        time.sleep(0.25)
    return None


def _wait_for_no_window(timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _find_app_window() is None:
            return True
        time.sleep(0.1)
    return False


def _wait_for_exit(proc: subprocess.Popen, timeout: float) -> bool:
    try:
        proc.wait(timeout=timeout)
        return True
    except subprocess.TimeoutExpired:
        return False


def _wait_for_profile_exit(profile_dir: Path, timeout: float) -> list[int]:
    deadline = time.monotonic() + timeout
    leftover: list[int] = []
    while time.monotonic() < deadline:
        leftover = _find_browser_pids_for_profile(profile_dir)
        if not leftover:
            return []
        time.sleep(0.25)
    return leftover


def _terminate_exact(proc: subprocess.Popen | None, profile_dir: Path) -> None:
    if proc is not None and proc.poll() is None:
        proc.kill()
    for pid in _find_browser_pids_for_profile(profile_dir):
        _powershell(f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue")


def main() -> int:
    if not APP.is_file():
        print(f"Missing app executable: {APP}")
        return 1

    with tempfile.TemporaryDirectory(prefix="bearreader-cleanup-") as tmp:
        data_dir = Path(tmp)
        profile_dir = data_dir / "app-browser"
        env = os.environ.copy()
        env["XIAOXIONG_NOVEL_DATA_PATH"] = str(data_dir)
        first: subprocess.Popen | None = None
        duplicate: subprocess.Popen | None = None
        second: subprocess.Popen | None = None
        try:
            first = subprocess.Popen([str(APP)], env=env, creationflags=CREATE_NEW_CONSOLE)
            first_window = _wait_for_window(90)
            if first_window is None:
                print("FAIL: first app window never appeared")
                return 1
            print(f"First window appeared (browser pid={first_window[0]})")

            duplicate = subprocess.Popen([str(APP)], env=env, creationflags=CREATE_NEW_CONSOLE)
            if not _wait_for_exit(duplicate, 5) or first.poll() is not None:
                print("FAIL: duplicate launch did not preserve the running instance")
                return 1
            if _find_app_window() is None:
                print("FAIL: duplicate launch lost the existing app window")
                return 1
            print("Duplicate launch activated the existing instance")

            _close_window(first_window[1])
            if not _wait_for_no_window(5):
                print("FAIL: first window did not close")
                return 1

            # Relaunch as soon as the user-visible window has disappeared.
            second = subprocess.Popen([str(APP)], env=env, creationflags=CREATE_NEW_CONSOLE)
            if not _wait_for_exit(first, 8):
                print("FAIL: first backend did not release the mutex within 8s")
                return 1
            second_window = _wait_for_window(45)
            if second_window is None or second.poll() is not None:
                print("FAIL: immediate relaunch did not open a replacement window")
                return 1
            print(f"Immediate relaunch succeeded (browser pid={second_window[0]})")

            # The first close above is the deliberate immediate-relaunch stress
            # case. Let the replacement finish binding its trusted HWND before
            # measuring the ordinary close-to-exit budget; closing in the first
            # paint can legitimately take the 10s heartbeat fallback instead.
            time.sleep(2)
            _close_window(second_window[1])
            if not _wait_for_exit(second, 8):
                print("FAIL: second backend did not exit within 8s")
                return 1
            leftover = _wait_for_profile_exit(profile_dir, 5)
            if leftover:
                print(f"FAIL: app-profile browser processes remain: {leftover}")
                return 1
            print("CLOSE + IMMEDIATE RELAUNCH + CLEANUP: PASS")
            return 0
        finally:
            _terminate_exact(second, profile_dir)
            _terminate_exact(duplicate, profile_dir)
            _terminate_exact(first, profile_dir)


if __name__ == "__main__":
    sys.exit(main())
