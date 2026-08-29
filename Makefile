# =============================================================================
# BearReader — developer tasks (uv, yarn, git)
# =============================================================================

.PHONY: all \
	version clean ensure-uv setup sync install upgrade \
	major minor patch \
	lint lint-fix start dev watch \
	index-gen check-sources \
	frontend-install frontend-audit frontend-lint frontend-build frontend-sync frontend-verify web-verify \
	build-wheel build-exe build-installer build build-windows build-zh-sources verify-distribution \
	remove-tag push-tag push-tag-force \
	add-dep add-dev rm-dep rm-dev

# --- uv executable (PATH, else default install location) ---------------------
ifeq ($(OS),Windows_NT)
  PS := powershell -NoProfile -Command
  VERSION := $(shell $(PS) "(Get-Content lncrawl/VERSION).Trim()")
  UV := $(shell where.exe uv 2>NUL || echo %USERPROFILE%\.local\bin\uv.exe)
else
  VERSION := $(shell cat lncrawl/VERSION | tr -d '\n')
  UV := $(shell command -v uv 2>/dev/null || echo "$(HOME)/.local/bin/uv")
endif

# Same flags everywhere so `add-dep` / `install` / `sync` match.
UV_SYNC_FLAGS := --all-extras --all-groups

# Package name for: make add-dep <pkg>  (second goal; see %-catchall below)
ifneq ($(filter add-dep add-dev rm-dep rm-dev,$(MAKECMDGOALS)),)
  PKG := $(word 2,$(MAKECMDGOALS))
endif

# =============================================================================
# Default
# =============================================================================

all: install

# =============================================================================
# Git — info, release tags
# =============================================================================

version:
	@echo BearReader: $(VERSION)

remove-tag:
	git diff --exit-code HEAD
	git tag -d "v$(VERSION)"

push-tag:
	git diff --exit-code HEAD
	git tag "v$(VERSION)"
	@git push -f --tags

push-tag-force: remove-tag push-tag

# =============================================================================
# Cleanup
# =============================================================================

clean:
ifeq ($(OS),Windows_NT)
	@powershell -Command "try { Remove-Item -ErrorAction SilentlyContinue -Recurse -Force .venv, logs, build, dist } catch {}; exit 0"
	@powershell -Command "Get-ChildItem -ErrorAction SilentlyContinue -Recurse -Directory -Filter '*.egg-info' | Remove-Item -Recurse -Force"
	@powershell -Command "Get-ChildItem -ErrorAction SilentlyContinue -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force"
else
	@rm -rf .venv logs build dist
	@find . -depth -name '*.egg-info' -type d -exec rm -rf '{}' \; 2>/dev/null || true
	@find . -depth -name '__pycache__' -type d -exec rm -rf '{}' \; 2>/dev/null || true
endif

# =============================================================================
# uv — bootstrap & version file (X.Y.Z)
# =============================================================================

ensure-uv:
ifeq ($(OS),Windows_NT)
	@$(UV) --version || powershell -NoProfile -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
else
	@$(UV) --version || curl -LsSf https://astral.sh/uv/install.sh | sh
endif

major: ensure-uv
	@$(UV) run python ./scripts/bump.py major

minor: ensure-uv
	@$(UV) run python ./scripts/bump.py minor

patch: ensure-uv
	@$(UV) run python ./scripts/bump.py patch

setup: ensure-uv

sync:
	$(UV) sync $(UV_SYNC_FLAGS)

install: setup sync

upgrade: setup
	$(UV) lock --upgrade

# =============================================================================
# Python — lint, server, scaffolding
# =============================================================================

lint:
	@$(UV) run pyright lncrawl
	@$(UV) run ruff format --diff --check
	@$(UV) run ruff check
# 	@$(UV) run pyright sources

lint-fix:
	@$(UV) run ruff check --fix
	@$(UV) run ruff format

start:
	$(UV) run python -m lncrawl -ll server

dev:
	$(UV) run python -m lncrawl -ll server --watch

watch: dev

index-gen:
	$(UV) run python scripts/index_gen.py
	
check-sources:
	$(UV) run python scripts/check_sources.py

# =============================================================================
# Frontend — install, audit, lint, build, sync, verify (yarn)
# =============================================================================

YARN := yarn --cwd frontend

frontend-install:
	$(YARN) install --frozen-lockfile

frontend-audit:
	$(YARN) audit:zh

frontend-lint:
	$(YARN) lint

frontend-build:
	$(YARN) build

# 构建并把产物原子写入 lncrawl/server/web/，同时刷新 frontend-manifest.json
frontend-sync:
	$(UV) run python scripts/sync_localized_frontend.py

# 校验嵌入产物与 frontend/ 源码树、构建清单一致
frontend-verify:
	$(UV) run python scripts/frontend_manifest.py --verify

web-verify:
	$(UV) run python scripts/sync_localized_frontend.py --validate-only

# =============================================================================
# Build — wheel, PyInstaller
# =============================================================================

build-wheel:
	$(UV) run python -m build -w

build-exe:
	$(UV) run python setup_pyi.py

build-zh-sources:
	$(UV) run python scripts/build_distribution_sources.py --output build/distribution-sources

verify-distribution:
	$(UV) run python scripts/verify_distribution_runtime.py

build-installer:
ifeq ($(OS),Windows_NT)
	$(PS) "$$candidates = @('C:\Program Files (x86)\Inno Setup 6\ISCC.exe', (Join-Path $$env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')); $$iscc = $$candidates | Where-Object { Test-Path $$_ } | Select-Object -First 1; if (-not $$iscc) { throw 'Inno Setup 6 ISCC.exe is required' }; & $$iscc 'installer\installer.iss' '/DMyAppVersion=$(VERSION)'; if ($$LASTEXITCODE -ne 0) { exit $$LASTEXITCODE }"
else
	@echo "Skipping installer build (Windows only)"
endif

build-windows: build-exe build-installer

build: version install build-windows

# =============================================================================
# Dependencies — usage: make add-dep <package>
# =============================================================================

add-dep: setup
	@test -n "$(PKG)" || (echo >&2 "Usage: make add-dep <package>"; exit 1)
	$(UV) add $(PKG)
	$(UV) sync $(UV_SYNC_FLAGS)

add-dev: setup
	@test -n "$(PKG)" || (echo >&2 "Usage: make add-dev <package>"; exit 1)
	$(UV) add --optional dev $(PKG)
	$(UV) sync $(UV_SYNC_FLAGS)

rm-dep: setup
	@test -n "$(PKG)" || (echo >&2 "Usage: make rm-dep <package>"; exit 1)
	$(UV) remove $(PKG)
	$(UV) sync $(UV_SYNC_FLAGS)

rm-dev: setup
	@test -n "$(PKG)" || (echo >&2 "Usage: make rm-dev <package>"; exit 1)
	$(UV) remove --optional dev $(PKG)
	$(UV) sync $(UV_SYNC_FLAGS)

# Ignore the second word (package name) as a nested target
%:
	@:
