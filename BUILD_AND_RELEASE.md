# 构建与发行说明

BearReader 的本地构建、书源维护与公开发行流程。

## 版本与标签

- 版本号：`X.Y.Z`（语义化版本），记录于 `lncrawl/VERSION` 与 `CHANGELOG.md`；
- 发行标签：`vX.Y.Z`，指向构建该发行物的完整产品提交；
- 同一标签必须同时包含：`frontend/` 源码、`lncrawl/server/web/` 嵌入产物、后端与中文书源——发行 ZIP、源码归档与许可证材料全部从该标签的单一 checkout 构建；
- CI 不运行实时抓取：所有门禁只做离线验证，不访问书源网站。

## 构建并同步前端

前端源码位于 `frontend/`（React/Vite）。嵌入产物 `lncrawl/server/web/` 为生成物，**禁止手工修改**，只能由同步脚本写入。前端源码与对应嵌入产物必须在同一个提交中更新——只改一半的提交会被 CI 拒绝。

```powershell
function Invoke-Native {
  param([string] $FilePath, [string[]] $ArgumentList)
  & $FilePath @ArgumentList
  if ($LASTEXITCODE -ne 0) { throw "native failure" }
}
Push-Location frontend
Invoke-Native yarn install --frozen-lockfile
Invoke-Native yarn audit:zh
Invoke-Native yarn lint
Invoke-Native yarn build
Pop-Location
Invoke-Native uv run python scripts\sync_localized_frontend.py
Invoke-Native uv run python scripts\frontend_manifest.py --verify
```

## 更新后端

后端改动须通过完整门禁后再提交：

```powershell
function Invoke-Native {
  param([string] $FilePath, [string[]] $ArgumentList)
  & $FilePath @ArgumentList
  if ($LASTEXITCODE -ne 0) { throw "native failure" }
}
Invoke-Native uv sync --frozen --all-extras --all-groups
Invoke-Native uv run pyright lncrawl
Invoke-Native uv run ruff format --check
Invoke-Native uv run ruff check
Invoke-Native uv run python -m lncrawl dev check-sources
Invoke-Native uv run python scripts\verify_distribution_identity.py
Invoke-Native uv run python scripts\verify_distribution_runtime.py
Invoke-Native uv run python scripts\verify_distribution_hardening.py
Invoke-Native uv run python scripts\verify_workflow_safety.py
```

## 添加中文书源

- 新书源须通过空壳/反爬检查与最后 3 章 VIP 验证后再合入；
- 书源失效优先修复解析器，不轻易加入 `sources/_rejected.json`；
- 详细规范见 `sources/` 与 `.claude/skills/add-source/`；
- 添加后运行离线验证加载：

```powershell
function Invoke-Native {
  param([string] $FilePath, [string[]] $ArgumentList)
  & $FilePath @ArgumentList
  if ($LASTEXITCODE -ne 0) { throw "native failure" }
}
Invoke-Native uv run python -m lncrawl dev check-sources
```

## 构建 Windows 安装包

默认发行物是绿色 ZIP；安装器仅在明确要求时制作：

```powershell
function Invoke-Native {
  param([string] $FilePath, [string[]] $ArgumentList)
  & $FilePath @ArgumentList
  if ($LASTEXITCODE -ne 0) { throw "native failure" }
}
Invoke-Native uv run python setup_pyi.py
Invoke-Native uv run python scripts\verify_windows_bundle.py dist\BearReader
Invoke-Native .\dist\BearReader\backendtool.exe -ll sources list
Invoke-Native uv run python scripts\build_portable.py
```

## GPL 源码材料

本地自行构建不要求额外生成源码压缩包；凡向他人分发绿色包、安装包或其他二进制产物，都必须同时提供与该二进制精确对应的完整源码（同一标签的源码归档）及适用许可证材料。发行工作流在归档前会拒绝脏工作树：

```powershell
function Invoke-Native {
  param([string] $FilePath, [string[]] $ArgumentList)
  & $FilePath @ArgumentList
  if ($LASTEXITCODE -ne 0) { throw "native failure" }
}
$backendStatus = Invoke-Native git status --porcelain
if ($backendStatus) { throw "Backend checkout is dirty; refusing to create a source archive" }
```

Release 工作流用 `git archive` 从同一 checkout 生成完整 monorepo 源码归档，并附 `LICENSE`、`THIRD_PARTY_NOTICES.md` 与 SHA256 清单。
