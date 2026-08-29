import argparse
import json
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Callable, List, Tuple
import uuid
import warnings

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import build_distribution_sources, sync_localized_frontend  # noqa: E402


def _fixture_root(name: str) -> Path:
    root = PROJECT_ROOT / "build" / f"{name}-{uuid.uuid4().hex}"
    root.mkdir(parents=True)
    return root


def _retry_readonly_removal(
    operation: Callable[..., object],
    path: str,
    _exception: object,
) -> None:
    Path(path).chmod(stat.S_IREAD | stat.S_IWRITE)
    operation(path)


def _remove_fixture(root: Path) -> None:
    error: OSError = OSError("Fixture cleanup did not run")
    for _ in range(3):
        try:
            shutil.rmtree(root, onerror=_retry_readonly_removal)
        except FileNotFoundError:
            return
        except OSError as cleanup_error:
            error = cleanup_error
            time.sleep(0.1)
        else:
            return
    raise AssertionError(f"Could not remove regression fixture {root}: {error}")


def _run(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        list(args),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        message = result.stderr.strip() or result.stdout.strip()
        raise AssertionError(f"Fixture command failed: {' '.join(args)}\n{message}")
    return result.stdout.strip()


def _make_source_fixture(root: Path) -> Path:
    source_root = root / "sources"
    source_root.mkdir(parents=True)
    (source_root / "zh").mkdir()
    for relative in (
        Path("__init__.py"),
        Path("_index.json"),
        Path("_rejected.json"),
        Path("zh") / "mayiwsk.py",
    ):
        source = PROJECT_ROOT / "sources" / relative
        destination = source_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return source_root


def _expect_rejected_before_mutation(
    source_root: Path,
    output_root: Path,
    metadata_index: Path,
    sentinels: List[Path],
) -> None:
    try:
        build_distribution_sources.build_sources(source_root, output_root, metadata_index)
    except ValueError:
        pass
    except Exception as error:
        raise AssertionError(
            "Dangerous source/output paths must be rejected before the builder mutates files"
        ) from error
    else:
        raise AssertionError("Dangerous source/output paths were accepted")

    for sentinel in sentinels:
        if not sentinel.is_file():
            raise AssertionError(f"Dangerous build mutated sentinel: {sentinel}")


def verify_source_overlap_protection() -> None:
    root = _fixture_root("distribution-source-overlap")
    try:
        ancestor_source = _make_source_fixture(root / "ancestor")
        ancestor_output = ancestor_source.parent
        ancestor_sentinel = ancestor_output / "output-ancestor-sentinel.txt"
        ancestor_sentinel.write_text("preserve me\n", encoding="utf-8")
        _expect_rejected_before_mutation(
            ancestor_source,
            ancestor_output,
            ancestor_source / "_index.json",
            [ancestor_sentinel, ancestor_source / "zh" / "mayiwsk.py"],
        )

        descendant_source = _make_source_fixture(root / "descendant")
        descendant_output = descendant_source / "distribution-output"
        descendant_sentinel = descendant_source / "output-descendant-sentinel.txt"
        descendant_sentinel.write_text("preserve me\n", encoding="utf-8")
        _expect_rejected_before_mutation(
            descendant_source,
            descendant_output,
            descendant_source / "_index.json",
            [descendant_sentinel, descendant_source / "zh" / "mayiwsk.py"],
        )
        if descendant_output.exists():
            raise AssertionError("Rejected nested output directory was created")

        metadata_source = _make_source_fixture(root / "metadata")
        metadata_output = root / "metadata-output"
        metadata_output.mkdir()
        metadata_index = metadata_output / "metadata.json"
        shutil.copy2(metadata_source / "_index.json", metadata_index)
        _expect_rejected_before_mutation(
            metadata_source,
            metadata_output,
            metadata_index,
            [metadata_index, metadata_source / "zh" / "mayiwsk.py"],
        )
    finally:
        _remove_fixture(root)


def verify_distribution_output_ownership() -> None:
    root = _fixture_root("distribution-output-ownership")
    try:
        source = _make_source_fixture(root / "owner")
        metadata = source / "_index.json"

        outside = Path(tempfile.gettempdir()) / f"xiaoxiong-outside-{uuid.uuid4().hex}"
        outside.mkdir()
        outside_sentinel = outside / "sentinel.txt"
        outside_sentinel.write_text("preserve\n", encoding="utf-8")
        try:
            try:
                build_distribution_sources.build_sources(source, outside, metadata)
            except ValueError:
                pass
            else:
                raise AssertionError("Output outside the build directory was accepted")
        finally:
            if not outside_sentinel.is_file():
                raise AssertionError("Outside-build output mutated a sentinel")
            shutil.rmtree(outside, ignore_errors=True)

        unmanaged = root / "unmanaged"
        unmanaged.mkdir()
        unmanaged_sentinel = unmanaged / "keep.txt"
        unmanaged_sentinel.write_text("preserve\n", encoding="utf-8")
        try:
            build_distribution_sources.build_sources(source, unmanaged, metadata)
        except ValueError:
            pass
        else:
            raise AssertionError("Existing unmanaged build output was accepted")
        if not unmanaged_sentinel.is_file():
            raise AssertionError("Unmanaged build output sentinel was deleted")

        fresh = root / "fresh"
        build_distribution_sources.build_sources(source, fresh, metadata)
        if not (fresh / build_distribution_sources.OUTPUT_MARKER).is_file():
            raise AssertionError("Fresh output did not carry the ownership marker")

        managed = root / "managed"
        build_distribution_sources.build_sources(source, managed, metadata)
        if not (managed / build_distribution_sources.OUTPUT_MARKER).is_file():
            raise AssertionError("Managed output did not carry the ownership marker")
        build_distribution_sources.build_sources(source, managed, metadata)
        if not (managed / "sources" / "_index.json").is_file():
            raise AssertionError("Managed output was not rebuilt successfully")
    finally:
        _remove_fixture(root)


def _write_frontend(root: Path, marker: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir(exist_ok=True)
    (root / "index.html").write_text(
        (
            '<!doctype html><html lang="zh-CN"><head>'
            "<title>BearReader</title></head>"
            f"<body>{marker}</body></html>"
        ),
        encoding="utf-8",
    )
    (root / "manifest.webmanifest").write_text(
        json.dumps({"name": "BearReader", "lang": "zh-CN"}, ensure_ascii=False),
        encoding="utf-8",
    )
    for document in ("PRIVACY_POLICY.html", "TERMS_OF_SERVICE.html"):
        (root / document).write_text(f"BearReader {marker} 中文法律页", encoding="utf-8")
    (root / "assets" / "app.txt").write_text(marker, encoding="utf-8")


def _write_source_map(root: Path, source: str) -> None:
    (root / "sw.js.map").write_text(
        json.dumps(
            {
                "version": 3,
                "file": "sw.js",
                "sources": [source],
                "names": [],
                "mappings": "",
            }
        ),
        encoding="utf-8",
    )


def verify_frontend_source_map_provenance() -> None:
    root = _fixture_root("frontend-source-map-provenance")
    try:
        first = root / "first"
        second = root / "second"
        _write_frontend(first, "same")
        _write_frontend(second, "same")
        _write_source_map(
            first,
            "C:/Users/ADMINI~1/AppData/Local/Temp/7c79d558941334c9ed915b27f91c2a31/sw.js",
        )
        _write_source_map(
            second,
            "C:/Users/ADMINI~1/AppData/Local/Temp/81c35c88cc373bb19db6c529baa89bd9/sw.js",
        )
        first_digest = sync_localized_frontend.validate_frontend(first)
        second_digest = sync_localized_frontend.validate_frontend(second)
        if first_digest != second_digest:
            raise AssertionError(
                "Ephemeral source-map paths changed the frontend provenance digest"
            )
    finally:
        _remove_fixture(root)


def _make_frontend_fixture(root: Path) -> Tuple[Path, Path, str]:
    repository = root / "frontend"
    repository.mkdir()
    (repository / ".gitignore").write_text("dist/\n", encoding="utf-8")
    (repository / "package.json").write_text(
        '{"scripts":{"build":"python build.py"}}\n', encoding="utf-8"
    )
    (repository / "build.py").write_text(
        """
import json
from pathlib import Path
import shutil

dist = Path("dist")
shutil.rmtree(dist, ignore_errors=True)
dist.mkdir()
(dist / "assets").mkdir()
(dist / "index.html").write_text(
    '<!doctype html><html lang="zh-CN"><head><title>BearReader</title></head><body>built</body></html>',
    encoding="utf-8",
)
(dist / "manifest.webmanifest").write_text(
    json.dumps({"name": "BearReader", "lang": "zh-CN"}, ensure_ascii=False),
    encoding="utf-8",
)
for document in ("PRIVACY_POLICY.html", "TERMS_OF_SERVICE.html"):
    (dist / document).write_text("BearReader 隐私说明", encoding="utf-8")
(dist / "assets" / "app.txt").write_text("built", encoding="utf-8")
""".lstrip(),
        encoding="utf-8",
    )
    source = repository / "dist"
    _write_frontend(source, "tampered")
    return repository, source


def _patch_yarn_build() -> Tuple[Callable[[], bool], Callable[[], None]]:
    original_run = sync_localized_frontend.subprocess.run
    calls: List[Tuple[str, ...]] = []
    yarn = "yarn.cmd" if sys.platform == "win32" else "yarn"

    def run(command: object, *args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        if isinstance(command, (list, tuple)) and tuple(command) == (yarn, "build"):
            calls.append(tuple(command))
            return original_run(
                [sys.executable, "build.py"],
                *args,
                **kwargs,
            )
        return original_run(command, *args, **kwargs)

    sync_localized_frontend.subprocess.run = run  # type: ignore[assignment]

    def was_called() -> bool:
        return calls == [(yarn, "build")]

    def restore() -> None:
        sync_localized_frontend.subprocess.run = original_run

    return was_called, restore


def verify_frontend_build_provenance() -> None:
    root = _fixture_root("frontend-build-provenance")
    try:
        repository, source = _make_frontend_fixture(root)
        destination = root / "embedded-web"
        was_called, restore = _patch_yarn_build()
        try:
            sync_localized_frontend.sync_localized_frontend(destination, repository)
        finally:
            restore()

        if not was_called():
            raise AssertionError("Embedding did not invoke yarn build from the frontend directory")
        if "built" not in (source / "index.html").read_text(encoding="utf-8"):
            raise AssertionError("Stale dist tampering was not overwritten by the verified build")
        source_digest = sync_localized_frontend.validate_frontend(source)
        destination_digest = sync_localized_frontend.validate_frontend(destination)
        if source_digest != destination_digest:
            raise AssertionError("Embedded frontend digest differs from the fresh build")
    finally:
        _remove_fixture(root)


def verify_frontend_atomic_cleanup() -> None:
    root = _fixture_root("frontend-atomic-cleanup")
    try:
        repository, source = _make_frontend_fixture(root)
        _run(sys.executable, "build.py", cwd=repository)
        destination = root / "web"
        _write_frontend(destination, "old")

        original_rmtree = sync_localized_frontend.shutil.rmtree
        was_called, restore_run = _patch_yarn_build()

        def fail_backup_cleanup(path: object, *args: object, **kwargs: object) -> None:
            if ".web.backup-" in Path(path).name:
                raise OSError("forced backup cleanup failure")
            original_rmtree(path, *args, **kwargs)

        sync_localized_frontend.shutil.rmtree = fail_backup_cleanup  # type: ignore[assignment]
        try:
            with warnings.catch_warnings(record=True) as captured:
                warnings.simplefilter("always")
                sync_localized_frontend.sync_localized_frontend(destination, repository)
        finally:
            sync_localized_frontend.shutil.rmtree = original_rmtree
            restore_run()

        if not was_called():
            raise AssertionError("Atomic replacement did not build the verified frontend")
        sync_localized_frontend.validate_frontend(destination)
        if "built" not in (destination / "index.html").read_text(encoding="utf-8"):
            raise AssertionError("Backup cleanup failure rolled back the installed frontend")
        if not any("backup" in str(item.message).lower() for item in captured):
            raise AssertionError("Backup cleanup failure did not emit an explicit warning")
        if not list(root.glob(".web.backup-*")):
            raise AssertionError("Backup cleanup failure did not retain the backup for recovery")
    finally:
        _remove_fixture(root)


CHECKS = {
    "source-overlap": verify_source_overlap_protection,
    "output-ownership": verify_distribution_output_ownership,
    "frontend-provenance": verify_frontend_build_provenance,
    "frontend-atomicity": verify_frontend_atomic_cleanup,
    "frontend-source-map-provenance": verify_frontend_source_map_provenance,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Exercise distribution hardening regressions with isolated project fixtures"
    )
    parser.add_argument("checks", nargs="*")
    args = parser.parse_args()
    selected = args.checks or sorted(CHECKS)
    unknown = sorted(set(selected).difference(CHECKS))
    if unknown:
        parser.error(f"Unknown regression checks: {', '.join(unknown)}")
    for name in selected:
        CHECKS[name]()
        print(f"Passed distribution hardening regression: {name}")


if __name__ == "__main__":
    main()
