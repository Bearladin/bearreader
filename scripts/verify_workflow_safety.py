import argparse
from pathlib import Path
import re
from typing import Iterable, List, Mapping, Tuple

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "release.yml"
LINT_WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "lint.yml"
WORKFLOWS = (
    RELEASE_WORKFLOW,
    PROJECT_ROOT / ".github" / "workflows" / "index-gen.yml",
    PROJECT_ROOT / ".github" / "workflows" / "web.yml",
)
ARCHIVE_DOCUMENT = PROJECT_ROOT / "BUILD_AND_RELEASE.md"
FRONTEND_CHECKOUT_PATH = "build/frontend-source"
WHEEL_GLOB = "dist/xiaoxiong_novel-*.whl"
DIRECT_NATIVE = re.compile(
    r"^\s*(?:(?:\$\w+\s*=\s*)?\(?\s*)?"
    r"(?:uv\b|yarn\b|git\b|python(?:\.exe)?\b|powershell(?:\.exe)?\b|&\s+|"
    r"\.[\\/].*\.(?:exe|ps1)\b)",
    re.IGNORECASE,
)
POWERSHELL_BLOCK = re.compile(r"```powershell\s*\r?\n(.*?)```", re.DOTALL | re.IGNORECASE)
DOCUMENTATION_NATIVE_SECTIONS = (
    "更新后端",
    "添加中文书源",
    "构建并同步前端",
    "构建 Windows 安装包",
    "GPL 源码材料",
)


def _workflow_steps(
    document: Mapping[str, object],
) -> Iterable[Tuple[str, Mapping[str, object], Mapping[str, object]]]:
    jobs = document.get("jobs")
    if not isinstance(jobs, Mapping):
        raise ValueError("Workflow has no jobs mapping")
    for job_name, job in jobs.items():
        if not isinstance(job_name, str) or not isinstance(job, Mapping):
            raise ValueError("Workflow has an invalid job")
        steps = job.get("steps")
        if not isinstance(steps, list):
            raise ValueError(f"Workflow job has no steps list: {job_name}")
        for step in steps:
            if isinstance(step, Mapping):
                yield job_name, job, step


def _is_direct_native_line(line: str) -> bool:
    return bool(DIRECT_NATIVE.match(line)) and "& $FilePath @ArgumentList" not in line


def _command_start(lines: List[str], line_number: int) -> int:
    while line_number > 0 and lines[line_number - 1].rstrip().endswith("`"):
        line_number -= 1
    return line_number


def _pwsh_violations(run: str) -> List[str]:
    violations: List[str] = []
    if "function Invoke-Native" not in run:
        violations.append("is missing the Invoke-Native helper")
    if not re.search(r"\$LASTEXITCODE\s+-ne\s+0", run):
        violations.append("does not check $LASTEXITCODE in Invoke-Native")

    lines = run.splitlines()
    for line_number, line in enumerate(lines):
        stripped = line.strip()
        command_start = _command_start(lines, line_number)
        if "Invoke-Native" in lines[command_start]:
            continue
        if _is_direct_native_line(stripped):
            violations.append(f"runs a native command without Invoke-Native: {stripped}")
    return violations


def _direct_command_violations(run: str) -> List[str]:
    violations: List[str] = []
    lines = run.splitlines()
    line_number = 0
    while line_number < len(lines):
        stripped = lines[line_number].strip()
        if not _is_direct_native_line(stripped):
            line_number += 1
            continue

        command_end = line_number
        while lines[command_end].rstrip().endswith("`") and command_end + 1 < len(lines):
            command_end += 1

        next_line = command_end + 1
        while next_line < len(lines) and not lines[next_line].strip():
            next_line += 1
        if next_line == len(lines) or not re.match(
            r"^\s*if\s*\(\s*\$LASTEXITCODE\s+-ne\s+0\s*\)", lines[next_line]
        ):
            violations.append(
                f"does not immediately check $LASTEXITCODE after native command: {stripped}"
            )
        line_number = command_end + 1
    return violations


def _documentation_native_violations(run: str) -> List[str]:
    if "Invoke-Native" in run:
        return _pwsh_violations(run)
    if any(_is_direct_native_line(line.strip()) for line in run.splitlines()):
        return _direct_command_violations(run)
    return []


def _load_workflow(path: Path) -> Mapping[str, object]:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Workflow YAML does not parse: {path}") from error
    if not isinstance(document, Mapping):
        raise ValueError(f"Workflow root is not a mapping: {path}")
    return document


def _verify_static_detector() -> None:
    unsafe = yaml.safe_load(
        """
jobs:
  check:
    steps:
      - shell: pwsh
        run: |
          uv run python scripts\\check.py
          Write-Output "continued"
"""
    )
    safe = yaml.safe_load(
        """
jobs:
  check:
    steps:
      - shell: pwsh
        run: |
          function Invoke-Native {
            param([string] $FilePath, [string[]] $ArgumentList)
            & $FilePath @ArgumentList
            if ($LASTEXITCODE -ne 0) { throw "native failure" }
          }
          Invoke-Native uv run python scripts\\check.py
"""
    )
    if not isinstance(unsafe, Mapping) or not isinstance(safe, Mapping):
        raise AssertionError("Static workflow fixtures did not parse")
    unsafe_runs = [
        str(step["run"])
        for _, _, step in _workflow_steps(unsafe)
        if step.get("shell") == "pwsh" and isinstance(step.get("run"), str)
    ]
    safe_runs = [
        str(step["run"])
        for _, _, step in _workflow_steps(safe)
        if step.get("shell") == "pwsh" and isinstance(step.get("run"), str)
    ]
    if not unsafe_runs or not _pwsh_violations(unsafe_runs[0]):
        raise AssertionError("Unsafe PowerShell fixture was accepted")
    if not safe_runs or _pwsh_violations(safe_runs[0]):
        raise AssertionError("Safe PowerShell fixture was rejected")


def _section_text(documentation: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)",
        documentation,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise ValueError(f"Missing distribution documentation section: {heading}")
    return match.group(1)


def _verify_documentation_static_detector() -> None:
    unsafe = """\
```powershell
uv run python scripts\\check.py
Write-Output "continued"
```
"""
    helper_safe = """\
```powershell
function Invoke-Native {
  param([string] $FilePath, [string[]] $ArgumentList)
  & $FilePath @ArgumentList
  if ($LASTEXITCODE -ne 0) { throw "native failure" }
}
Invoke-Native uv run python scripts\\check.py
```
"""
    immediate_safe = """\
```powershell
git status --porcelain
if ($LASTEXITCODE -ne 0) { throw "native failure" }
```
"""
    unsafe_block = POWERSHELL_BLOCK.search(unsafe)
    helper_safe_block = POWERSHELL_BLOCK.search(helper_safe)
    immediate_safe_block = POWERSHELL_BLOCK.search(immediate_safe)
    if unsafe_block is None or helper_safe_block is None or immediate_safe_block is None:
        raise AssertionError("Documentation safety fixtures did not parse")
    if not _documentation_native_violations(unsafe_block.group(1)):
        raise AssertionError("Unsafe documentation fixture was accepted")
    if _documentation_native_violations(helper_safe_block.group(1)):
        raise AssertionError("Invoke-Native documentation fixture was rejected")
    if _documentation_native_violations(immediate_safe_block.group(1)):
        raise AssertionError("Immediate-check documentation fixture was rejected")


def verify_workflows() -> None:
    _verify_static_detector()
    errors: List[str] = []
    for path in WORKFLOWS:
        document = _load_workflow(path)
        for job_name, job, step in _workflow_steps(document):
            if "run" not in step:
                continue
            shell = str(step.get("shell", "")).lower()
            is_windows_default = not shell and "windows" in str(job.get("runs-on", "")).lower()
            if shell not in {"powershell", "pwsh"} and not is_windows_default:
                continue
            run = step.get("run")
            if not isinstance(run, str):
                errors.append(f"{path.name}:{job_name} has a non-string pwsh run block")
                continue
            for violation in _pwsh_violations(run):
                errors.append(f"{path.name}:{job_name} {violation}")
    if errors:
        raise ValueError("\n".join(errors))


def verify_documentation_native_commands() -> None:
    _verify_documentation_static_detector()
    documentation = ARCHIVE_DOCUMENT.read_text(encoding="utf-8")
    errors: List[str] = []
    for heading in DOCUMENTATION_NATIVE_SECTIONS:
        section = _section_text(documentation, heading)
        if POWERSHELL_BLOCK.search(section) is None:
            errors.append(f"{heading} has no PowerShell instruction block")
    for block_number, block in enumerate(POWERSHELL_BLOCK.finditer(documentation), start=1):
        for violation in _documentation_native_violations(block.group(1)):
            errors.append(f"documentation block {block_number} {violation}")
    if errors:
        raise ValueError("\n".join(errors))


def _frontend_checkout_path_violations(document: Mapping[str, object]) -> List[str]:
    # Kept for callers that still pass workflow documents; external checkouts are
    # rejected outright by _external_checkout_violations in the monorepo layout.
    return _external_checkout_violations(document)


def _external_checkout_violations(document: Mapping[str, object]) -> List[str]:
    violations: List[str] = []
    for _, _, step in _workflow_steps(document):
        uses = str(step.get("uses", ""))
        options = step.get("with")
        if not uses.startswith("actions/checkout@") or not isinstance(options, Mapping):
            continue
        if "repository" in options:
            violations.append(
                "checks out an external repository; the monorepo must build from one checkout"
            )
    return violations


def _verify_frontend_checkout_static_detector() -> None:
    unsafe = yaml.safe_load(
        """
jobs:
  build:
    steps:
      - uses: actions/checkout@v7
        with:
          repository: owner/frontend
          path: build/frontend-source
"""
    )
    safe = yaml.safe_load(
        """
jobs:
  build:
    steps:
      - uses: actions/checkout@v7
"""
    )
    if not isinstance(unsafe, Mapping) or not isinstance(safe, Mapping):
        raise AssertionError("Frontend checkout fixtures did not parse")
    if not _external_checkout_violations(unsafe):
        raise AssertionError("External frontend checkout fixture was accepted")
    if _external_checkout_violations(safe):
        raise AssertionError("Single-checkout fixture was rejected")


def verify_frontend_checkout() -> None:
    _verify_frontend_checkout_static_detector()
    errors: List[str] = []
    for path in WORKFLOWS:
        errors.extend(
            f"{path.name} {v}" for v in _external_checkout_violations(_load_workflow(path))
        )
    if errors:
        raise ValueError("\n".join(errors))


def _require(text: str, pattern: str, description: str) -> None:
    if not re.search(pattern, text, re.MULTILINE):
        raise ValueError(f"Missing archive cleanliness guard: {description}")


def verify_archive_cleanliness() -> None:
    documentation = ARCHIVE_DOCUMENT.read_text(encoding="utf-8")
    if "git diff --quiet" in documentation:
        raise ValueError("Archive documentation uses git diff --quiet instead of porcelain status")
    _require(
        documentation,
        r"^\$backendStatus\s*=\s*Invoke-Native git status --porcelain\s*$",
        "monorepo git status --porcelain capture and exit check",
    )
    _require(
        documentation,
        r"if \(\$backendStatus\) \{\s*throw ",
        "monorepo dirty-tree rejection",
    )

    release = _load_workflow(RELEASE_WORKFLOW)
    archive_steps = [
        step
        for _, _, step in _workflow_steps(release)
        if step.get("name") == "Archive GPL source material and release metadata"
    ]
    if len(archive_steps) != 1 or not isinstance(archive_steps[0].get("run"), str):
        raise ValueError("Release workflow has no archive step")
    archive = str(archive_steps[0]["run"])
    _require(
        archive,
        r"^\$backendStatus\s*=\s*Invoke-Native git status --porcelain\s*$",
        "release monorepo porcelain capture",
    )
    _require(
        archive,
        r"if \(\$backendStatus\) \{\s*throw ",
        "release monorepo dirty-tree rejection",
    )
    _require(
        archive,
        r"git\s+archive",
        "release source archive created from the same checkout",
    )


def _lint_workflow_violations(workflow: str) -> List[str]:
    violations: List[str] = []
    if f"pip install {WHEEL_GLOB}" not in workflow:
        violations.append(f"does not install the XiaoXiong wheel with {WHEEL_GLOB}")
    if re.search(r"lightnovel[_-]crawler", workflow, re.IGNORECASE):
        violations.append("retains a legacy lightnovel-crawler package assumption")
    if "run_crawl_test" in workflow:
        violations.append("retains the live-crawl reusable-workflow input")
    if "novelfull.com" in workflow:
        violations.append("retains the forbidden English live crawl")
    if re.search(r"^\s*-\s+name:\s*.*\bcrawl\b", workflow, re.IGNORECASE | re.MULTILINE):
        violations.append("retains an official live-crawl workflow step")
    if "xiaoxiong-novel -ll sources list" not in workflow:
        violations.append("does not smoke-test the XiaoXiong executable entry point")
    if "xiaoxiong-novel -ll dev migrate verify" not in workflow:
        violations.append("does not check database drift through the XiaoXiong entry point")
    return violations


def _verify_lint_static_detector() -> None:
    unsafe = """\
- run: pip install dist/lightnovel_crawler*.whl
run_crawl_test: true
- name: Test Crawl
  run: lncrawl crawl https://novelfull.com/example
"""
    safe = """\
- run: pip install dist/xiaoxiong_novel-*.whl
- run: xiaoxiong-novel -ll sources list
- run: xiaoxiong-novel -ll dev migrate verify
"""
    if not _lint_workflow_violations(unsafe):
        raise AssertionError("Unsafe lint workflow fixture was accepted")
    if _lint_workflow_violations(safe):
        raise AssertionError("Safe lint workflow fixture was rejected")


def verify_lint_workflow() -> None:
    _verify_lint_static_detector()
    workflow = LINT_WORKFLOW.read_text(encoding="utf-8")
    errors = _lint_workflow_violations(workflow)
    documentation = ARCHIVE_DOCUMENT.read_text(encoding="utf-8")
    if "CI 不运行实时抓取" not in documentation:
        errors.append("distribution documentation does not state that CI avoids live crawls")
    if errors:
        raise ValueError("\n".join(errors))
    _load_workflow(LINT_WORKFLOW)


def _release_workflow_violations(workflow: str) -> List[str]:
    violations: List[str] = []
    if re.search(r"^\s*workflow_dispatch\s*:", workflow, re.MULTILINE):
        violations.append("retains workflow_dispatch, which cannot safely create a tag release")
    if not re.search(r"^\s*push\s*:", workflow, re.MULTILINE):
        violations.append("release is not triggered by push tags")
    if "releases/tags" not in workflow or ".draft" not in workflow:
        violations.append("does not guard against overwriting a published release")
    if "$($_.Name)" not in workflow:
        violations.append("checksums do not record portable basenames")
    return violations


def _verify_release_static_detector() -> None:
    unsafe = """\
on:
  workflow_dispatch: {}
  push:
    tags: ["v*"]
jobs:
  build:
    steps: []
"""
    safe = """\
on:
  push:
    tags: ["v*"]
jobs:
  build:
    steps:
      - run: gh api "repos/$env:GITHUB_REPOSITORY/releases/tags/$tag" --jq '.draft'
      - run: Write-Output "$($_.Name)"
"""
    if not _release_workflow_violations(unsafe):
        raise AssertionError("Unsafe release workflow fixture was accepted")
    if _release_workflow_violations(safe):
        raise AssertionError("Safe release workflow fixture was rejected")


def verify_release_workflow() -> None:
    _verify_release_static_detector()
    workflow = RELEASE_WORKFLOW.read_text(encoding="utf-8")
    errors = _release_workflow_violations(workflow)
    if errors:
        raise ValueError("\n".join(errors))
    _load_workflow(RELEASE_WORKFLOW)


CHECKS = {
    "workflows": verify_workflows,
    "documentation": verify_documentation_native_commands,
    "frontend-checkout": verify_frontend_checkout,
    "archive": verify_archive_cleanliness,
    "lint": verify_lint_workflow,
    "release": verify_release_workflow,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse distribution workflows and verify native-command/archive safety"
    )
    parser.add_argument("checks", nargs="*")
    args = parser.parse_args()
    selected = args.checks or tuple(CHECKS)
    unknown = sorted(set(selected).difference(CHECKS))
    if unknown:
        parser.error(f"Unknown workflow checks: {', '.join(unknown)}")
    for check in selected:
        CHECKS[check]()
        print(f"Passed workflow safety regression: {check}")


if __name__ == "__main__":
    main()
