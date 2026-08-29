#!/usr/bin/env python
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from typing import List

if sys.version_info[:2] < (3, 9):
    raise RuntimeError("This app only supports Python 3.9 and later.")
if sys.platform != "win32":
    raise RuntimeError("The XiaoXiong distribution can only be built on Windows.")

ROOT = Path(__file__).resolve().parent
DIST_DIR = ROOT / "dist"
SPEC_DIR = ROOT / "windows"
BUILD_DIR = SPEC_DIR / "build"
APP_NAME = "BearReader"
APP_ICON = ROOT / "res" / "bearreader.ico"
TOOL_ICON = ROOT / "res" / "backendtool.ico"


def _site_packages() -> Path:
    venv_dir = Path(os.getenv("VIRTUAL_ENV", ROOT / ".venv"))
    if not venv_dir.is_absolute():
        venv_dir = ROOT / venv_dir
    candidates = list(venv_dir.glob("**/site-packages"))
    if not candidates:
        raise RuntimeError(f"No site-packages found in {venv_dir}")
    return candidates[0]


SITE_PACKAGES = _site_packages()


def build_command(
    staged_sources: Path,
    name: str = APP_NAME,
    console: bool = True,
    icon: Path = APP_ICON,
) -> List[str]:
    command = [
        str(ROOT / "lncrawl" / "__main__.py"),
        "--onedir",
        "--clean",
        "--noconfirm",
        f"--name={name}",
        f"--icon={icon}",
        f"--distpath={DIST_DIR}",
        f"--specpath={SPEC_DIR}",
        f"--workpath={BUILD_DIR}",
    ]
    if not console:
        command.append("--noconsole")
    command += gather_packages()
    command += gather_data_files(staged_sources)
    command += gather_hidden_imports(staged_sources)
    command += gather_excluded_modules()
    return command


def gather_packages() -> List[str]:
    packages = [
        "pylsp",
        "translator",
        "curl_cffi",
        "websockets",
    ]
    return [f"--collect-all={package}" for package in packages]


def gather_data_files(staged_sources: Path) -> List[str]:
    file_map = {
        ROOT / "pyproject.toml": ".",
        ROOT / "lncrawl": "lncrawl",
        # PyInstaller 6 中 data 目标相对 _internal 解析："." 即落 _internal 根
        ROOT / "res" / "LICENSE-EDGE-TTS.txt": ".",
        ROOT / "res" / "LICENSE-XIAOXIONG-READER-KAI-OFL.txt": ".",
        ROOT / "res" / "LICENSE-XIAOXIONG-READER-SERIF-OFL.txt": ".",
        ROOT / "res" / "THIRD_PARTY_READER_FONTS.md": ".",
        staged_sources / "sources": "sources",
        SITE_PACKAGES / "wcwidth" / "version.json": "wcwidth",
        SITE_PACKAGES / "text_unidecode" / "data.bin": "text_unidecode",
    }

    results: List[str] = []
    for source, destination in file_map.items():
        if source.exists():
            results.extend(["--add-data", f"{source}{os.pathsep}{destination}"])
    return results


def gather_hidden_imports(staged_sources: Path) -> List[str]:
    hidden = ["passlib.handlers.argon2"]
    source_root = staged_sources / "sources"
    for source_file in sorted(source_root.joinpath("zh").glob("**/*.py")):
        parts = source_file.relative_to(source_root).with_suffix("").parts
        if all(part.isidentifier() for part in parts):
            hidden.append("sources." + ".".join(parts))
    return [f"--hidden-import={module}" for module in hidden]


def gather_excluded_modules() -> List[str]:
    excluded = [
        "pip",
        "wheel",
        "ujson",
        "altgraph",
        "macholib",
        "pyinstaller",
        "pkg_resources",
        "pyinstaller-hooks-contrib",
    ]
    return [flag for module in excluded for flag in ["--exclude-module", module]]


def package() -> None:
    from PyInstaller import __main__ as pyi  # type: ignore

    from scripts.build_backendtool_icon import verify_icon as verify_tool_icon
    from scripts.build_distribution_sources import build_sources, validate_sources
    from scripts.verify_windows_bundle import verify_bundle

    if not APP_ICON.is_file():
        raise RuntimeError(f"Missing BearReader icon: {APP_ICON}")
    verify_tool_icon(TOOL_ICON)
    if APP_ICON.read_bytes() == TOOL_ICON.read_bytes():
        raise RuntimeError("BearReader and backendtool icons must be different")

    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    for spec_file in SPEC_DIR.glob("*.spec"):
        spec_file.unlink(missing_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "build").mkdir(exist_ok=True)

    # add-data copies lncrawl verbatim, including __pycache__. A stale .pyc
    # older than a just-edited .py ships a frozen OLD module at runtime (the
    # 1.1.10 "method not allowed" incident) — purge every bytecode cache
    # under lncrawl before packaging.
    for pycache in (ROOT / "lncrawl").rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)

    with TemporaryDirectory(prefix="xiaoxiong-sources-", dir=ROOT / "build") as temporary:
        staging_root = Path(temporary) / "distribution"
        build_sources(
            source_root=ROOT / "sources",
            output_root=staging_root,
            metadata_index=ROOT / "sources" / "_index.json",
        )
        validate_sources(staging_root)

        # Two executables from the same entry point: the windowed app (double-click,
        # no console even when the default terminal is Windows Terminal) and a
        # console build for CLI use, the LSP server and bundle smoke tests.
        targets = [
            (APP_NAME, False, APP_ICON),
            ("backendtool", True, TOOL_ICON),
        ]
        for name, console, icon in targets:
            command = build_command(staging_root, name=name, console=console, icon=icon)
            print("Running PyInstaller:")
            print(" ".join(command))
            print("-" * 60)
            pyi.run(command)

    # The console tools build lands in its own onedir; move its exe into the app
    # bundle so both executables share the single _internal runtime.
    tools_dir = DIST_DIR / targets[1][0]
    tools_exe = tools_dir / f"{targets[1][0]}.exe"
    if not tools_exe.is_file():
        raise RuntimeError(f"PyInstaller output was not created: {tools_exe}")
    shutil.move(str(tools_exe), str(DIST_DIR / APP_NAME / f"{targets[1][0]}.exe"))
    shutil.rmtree(tools_dir, ignore_errors=True)

    output = DIST_DIR / APP_NAME / f"{APP_NAME}.exe"
    if not output.is_file():
        raise RuntimeError(f"PyInstaller output was not created: {output}")

    verify_bundle(output.parent, analysis_root=BUILD_DIR)
    print(f"Executables created: {output} and {DIST_DIR / APP_NAME / f'{targets[1][0]}.exe'}")


if __name__ == "__main__":
    package()
