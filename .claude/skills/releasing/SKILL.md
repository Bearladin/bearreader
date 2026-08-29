---
name: releasing
description: How lncrawl (lightnovel-crawler) releases work — version bump, tag-triggered release pipeline, changelog, per-OS builds, PyPI, Docker, web sync. Use when cutting a release, editing workflows, or debugging CI.
---

# Releasing lightnovel-crawler

There is **no version-bump GitHub workflow** — bumping is local and the release is triggered
by pushing a `v*` tag.

## The chain

```
make major|minor|patch        # scripts/bump.py edits lncrawl/VERSION only
<fill in CHANGELOG.md>        # add a "## [x.y.z]" section matching lncrawl/VERSION
make push-tag                 # tags v$(VERSION) and pushes → fires release.yml
```

`release.yml` builds the Windows-only XiaoXiong distribution on a `v*` tag or manual dispatch:

1. validates the embedded localized frontend, checks out its exact revision beneath ignored
   `build/frontend-source`, and fresh-builds it for a provenance comparison;
2. runs the Python, source-distribution, runtime, hardening, and workflow-safety gates;
3. creates and verifies the PyInstaller bundle and Inno installer;
4. refuses source archives from a dirty backend or frontend checkout, then uploads the Windows
   bundle and creates a draft release.

## Supporting workflows

- **`lint.yml`** — CI on push/PR touching `lncrawl/**`, `sources/**`, or dependency files:
  lint (pyright + ruff), XiaoXiong wheel build + install smoke test, `sources list`, and
  `dev migrate verify` (schema-drift gate). It is offline, including manual dispatch; live
  `mayiwsk`/`nieba` acceptance remains a Windows manual release check.
- **`web.yml`** ("Validate embedded web build") — on changes touching `frontend/**`,
  `lncrawl/server/web/**`, or the sync/manifest scripts: rebuilds the frontend from the
  same commit and compares it against the embedded copy via `--compare` plus the
  `frontend-manifest.json` verification. That directory is committed build output —
  **never hand-edit it**.
- **`index-gen.yml`** — on `dev` pushes touching `sources/**` or the index scripts: runs
  `scripts/index_gen.py` and auto-commits the regenerated `sources/_index.json`/`.zip` and
  README source tables.

## Changelog & README

- `CHANGELOG.md` sections are curated by hand; the release step extracts the section whose
  heading matches `lncrawl/VERSION` for the release notes. `scripts/changelog_gen.py` is a
  manual maintainer tool that back-fills missing sections from GitHub Releases.
- `README.md` regions between `<!-- auto generated ... -->` markers (source tables, CLI help)
  are rewritten by `scripts/index_gen.py` — never hand-edit them.

## Packaging notes

- PyInstaller via `setup_pyi.py`: `--onedir` on Windows, `--onefile` elsewhere. It bundles the
  whole `sources/` tree as data **and** force-imports every source module so dynamically
  loaded crawlers survive freezing — a new top-level data dependency may need adding there.
- Inno Setup (`installer/installer.iss`): the **AppId GUID must never change** — it identifies
  the app for upgrades/uninstalls. Install is per-user (`PrivilegesRequired=lowest`). The
  doubled `{{` in the AppId is Inno's escape for a literal brace — don't "fix" it.
