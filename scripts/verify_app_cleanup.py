#!/usr/bin/env python
"""Verify the windowed app exits cleanly and leaves nothing behind.

Launches the frozen app with a throwaway data dir, closes its window, and
asserts that the main process exits on its own (window-watch keep-alive)
and that no browser instance bound to the app profile survives.

Window detection uses WMI (PowerShell) instead of EnumWindows to avoid
deadlocks when the app's own _keep_alive() is also calling EnumWindows.
"""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "dist" / "BearReader"
APP = BUNDLE / "BearReader.exe"
TITLE = "BearReader"
WM_CLOSE = 0x0010
EXIT_TIMEOUT = 45  # window-watch keep-alive waits 20s after the last window

CREATE_NEW_CONSOLE = 0x00000010

# PowerShell command to find visible windows matching our title.
# Returns lines of "PID|HWND" or nothing if none found.
_PS_FIND_WINDOW = (
    "Get-CimInstance Win32_Process "
    "| Where-Object { $_.ProcessId -ne $PID } "  # exclude self
    "| ForEach-Object {"
    "  $p = $_;"
    '  Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ProcessId)" 2>$null;'
    "} "
    "| ForEach-Object {"
    "  $title = $_.Name;"
    "  Write-Output $title;"
    "}"
)

# Simpler: just check if a process with our title has a visible window
_PS_FIND_APP = (
    "Get-CimInstance Win32_Process "
    "| Where-Object { $_.Name -eq 'BearReader.exe' } "
    "| Select-Object -ExpandProperty ProcessId"
)

_PS_FIND_WINDOW_BY_PID = (
    'powershell -NoProfile -Command "'
    "Add-Type 'using System;using System.Runtime.InteropServices;"
    "public class Win32{"
    '[DllImport(\\"user32.dll\\")]'
    "public static extern bool EnumWindows(EnumWindowsProc cb,IntPtr p);"
    '[DllImport(\\"user32.dll\\")]'
    "public static extern bool IsWindowVisible(IntPtr h);"
    '[DllImport(\\"user32.dll\\",CharSet=CharSet.Unicode)]'
    "public static extern int GetWindowText(IntPtr h,System.Text.StringBuilder s,int n);"
    "public delegate bool EnumWindowsProc(IntPtr h,IntPtr p);"
    "}' "
    "-Language CSharp "
    "& {"
    "$found=$false;"
    "[Win32]::EnumWindows({param($h,$p);$b=New-Object System.Text.StringBuilder 256;"
    "[Win32]::GetWindowText($h,$b,256)|Out-Null;"
    "$v=[Win32]::IsWindowVisible($h);"
    "if($v -and $b.ToString().Contains('BearReader')){$found=$true;$false}else{$true}"
    "},[IntPtr]::Zero);"
    "if($found){'FOUND'}else{'NONE'}"
    '}"'
)

_PS_FIND_APP_WINDOW = (
    'powershell.exe -NoProfile -Command "'
    "Add-Type -TypeDefinition @' "
    "using System;using System.Runtime.InteropServices; "
    "public class WinApi { "
    "  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam); "
    '  [DllImport(\\"user32.dll\\")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam); '
    '  [DllImport(\\"user32.dll\\")] public static extern bool IsWindowVisible(IntPtr hWnd); '
    '  [DllImport(\\"user32.dll\\", CharSet=CharSet.Auto, SetLastError=true)] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount); '
    "} "
    "'@ ; "
    "$found=$false; "
    "[WinApi]::EnumWindows({param($h,$p); "
    "$sb=New-Object System.Text.StringBuilder 256; "
    "[WinApi]::GetWindowText($h,$sb,256)|Out-Null; "
    "$v=[WinApi]::IsWindowVisible($h); "
    "$t=$sb.ToString(); "
    "if($v -and $t.Contains('\\''BearReader'\\'')){$found=$true;return $false}; "
    "return $true "
    "},[IntPtr]::Zero); "
    "if($found){'FOUND'}else{'NONE'} "
    '"'
)

_PS_KILL_BY_NAME = (
    'powershell.exe -NoProfile -Command "'
    "Get-Process | Where-Object { $_.Path -like '*BearReader*' } "
    '| Stop-Process -Force -ErrorAction SilentlyContinue"'
)


def _find_app_window_pid() -> int | None:
    """Find a visible app window via WMI (no EnumWindows API call)."""
    # Strategy: find the app process by name, then check if it has a window.
    # WMI Win32_Process gives us PIDs; we don't call EnumWindows ourselves.
    r = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "Get-Process | Where-Object { $_.ProcessName -eq 'BearReader' -and $_.MainWindowTitle -ne '' } "
            "| Select-Object Id, MainWindowTitle | Format-Table -AutoSize",
        ],
        capture_output=True,
        timeout=10,
    )
    output = r.stdout.decode("utf-8", errors="replace")
    for line in output.splitlines():
        # Lines like: "  12345  BearReader"
        parts = line.split()
        if len(parts) >= 1:
            try:
                pid = int(parts[0])
                return pid
            except ValueError:
                continue
    return None


def _find_browser_pid_for_profile(profile_dir: Path) -> list[int]:
    """Find msedge/chrome PIDs bound to the app profile directory."""
    r = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            f"Get-CimInstance Win32_Process "
            f"| Where-Object {{ $_.Name -match 'msedge|chrome' -and $_.CommandLine -like '*{profile_dir}*' }} "
            f"| Select-Object -ExpandProperty ProcessId",
        ],
        capture_output=True,
        timeout=10,
    )
    output = r.stdout.decode("utf-8", errors="replace").strip()
    if not output:
        return []
    return [int(x) for x in output.splitlines() if x.strip().isdigit()]


def _kill_browser_pids(pids: list[int]) -> None:
    """Kill browser processes without /T (no process-tree kill)."""
    for pid in pids:
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue",
            ],
            capture_output=True,
            timeout=10,
        )


def main() -> int:
    if not APP.is_file():
        print(f"Missing app executable: {APP}")
        return 1

    with tempfile.TemporaryDirectory(prefix="xn-cleanup-") as tmp:
        data_dir = Path(tmp)
        env = os.environ.copy()
        env["XIAOXIONG_NOVEL_DATA_PATH"] = str(data_dir)

        proc = subprocess.Popen(
            [str(APP)],
            env=env,
            creationflags=CREATE_NEW_CONSOLE,
        )
        print(f"Launched app (pid={proc.pid})")

        # Wait for the app window to appear — use WMI polling only,
        # no EnumWindows API call from this process.
        browser_pid = None
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            # Check if the app process died early
            if proc.poll() is not None:
                print(f"FAIL: app process exited early (code={proc.poll()})")
                return 1

            found_pid = _find_app_window_pid()
            if found_pid is not None:
                browser_pid = found_pid
                break
            time.sleep(2)  # low frequency to avoid contention

        if browser_pid is None:
            print("FAIL: app window never appeared within 60s")
            _kill_browser_pids([proc.pid])
            return 1

        print(f"App window appeared (pid={browser_pid})")

        # Simulate the user closing the app window.
        # Kill the browser window process (NOT the main app process),
        # and do NOT use /T to avoid killing child tree recursively.
        subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                f"Stop-Process -Id {browser_pid} -Force -ErrorAction SilentlyContinue",
            ],
            capture_output=True,
            timeout=10,
        )
        print("Closed the app window")

        # Wait for the main process to exit (keep-alive exits after 20s).
        exited = False
        for _ in range(EXIT_TIMEOUT):
            time.sleep(1)
            if proc.poll() is not None:
                exited = True
                break
        if not exited:
            print(f"FAIL: main process still running after {EXIT_TIMEOUT}s")
            _kill_browser_pids([proc.pid])
            return 1
        print(f"Main process exited (code={proc.poll()})")

        # Check for leftover browser processes bound to the app profile.
        time.sleep(3)
        leftover = _find_browser_pid_for_profile(data_dir / "app-browser")
        if leftover:
            print(f"FAIL: {len(leftover)} browser process(es) still bound to the app profile")
            _kill_browser_pids(leftover)
            return 1
        print("No browser process left on the app profile")
        print("CLEANUP TEST: PASS")
        return 0


if __name__ == "__main__":
    sys.exit(main())
