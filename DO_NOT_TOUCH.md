# DO NOT TOUCH — 高风险禁改清单

> 以下内容在没有明确授权时**禁止修改**。它们是最容易被新 Agent 误改、且改错会引发全局回归的部分。
> 每项说明：位置、为什么、历史原因、改错会怎样、允许的修改、必须的验证。

---

## Rule 001 — 安装器 AppId GUID

Location: `installer/installer.iss` 中 `#define MyAppID "{{D44F8E47-8D94-4E50-A1F8-39D57C2B18E6}"`

Why: AppId 标识应用身份，用于升级/卸载。一旦发布后更改，用户将无法识别旧安装，出现双安装或卸载失败。

Historical Reason: 这是为中文版独立选定的新 GUID，与官方 LNCrawl 的旧 GUID 不同，保证两者并存。

What Can Go Wrong: 改了 AppId → 升级/卸载断裂，用户机器残留旧安装。

Allowed Modification: 无（永不变更）。

Verification Required: `scripts/verify_installer_identity.ps1` 会校验 AppId 精确值，任何改动都会失败。

---

## Rule 002 — 内嵌前端 `lncrawl/server/web/`

Location: `lncrawl/server/web/**`

Why: 这是前端 `dist` 的提交构建产物，压缩 JS/CSS 不可手工编辑。

Historical Reason: 通过 `scripts/sync_localized_frontend.py` 从同一提交的 `frontend/` 构建并整体原子替换；`frontend-manifest.json` 记录源码树与产物摘要。

What Can Go Wrong: 手改压缩文件 → 与构建清单摘要不匹配 → CI/验证失败，或引入不可审查的改动。

Allowed Modification: 只能通过 `sync_localized_frontend.py`（在 `frontend/` 构建后整体替换）变更，并同步更新 `frontend-manifest.json`；前端源码与产物必须同一提交。

Verification Required: `sync_localized_frontend.py --validate-only` 与 `frontend_manifest.py --verify` 校验源码树与产物摘要。

---

## Rule 003 — 生产 API 基地址

Location: 前端 `src/config.ts` 中 `API_BASE_URL`

Why: 客户端请求路径本身已含 `/api`，生产用空字符串表示同源。

Historical Reason: 若设为 `/api` 会产生 `/api/api/...` 双前缀（历史踩过的坑）。

What Can Go Wrong: 改回 `/api` → 所有 API 调用 404。

Allowed Modification: 生产保持空字符串；开发为 `http://localhost:8080`。

Verification Required: 前端 `yarn build` + 实际请求验证。

---

## Rule 004 — 数据目录隔离

Location: `lncrawl/config.py` 中 `APP_DIR`（`%APPDATA%\XiaoXiongNovel`）+ `lncrawl/distribution.py`

Why: 中文版与官方版数据必须完全隔离，不读取/迁移 `%APPDATA%\LNCrawl`。

Historical Reason: 中文发行版独立身份的核心约束。

What Can Go Wrong: 指向 `LNCrawl` 或共享目录 → 污染官方数据，或卸载时误删对方数据。

Allowed Modification: 无（数据目录名 `XiaoXiongNovel` 固定）。

Verification Required: `verify_distribution_identity.py` 断言 `APP_DIR.name == "XiaoXiongNovel"`。

---

## Rule 005 — 安装器禁止预删除

Location: `installer/installer.iss`

Why: 不能有 `[InstallDelete]` 预删 bundled 书源树；否则升级失败/取消会破坏现有安装。

Historical Reason: 第四轮审查发现 `[InstallDelete]` 删除在复制前，失败时旧 index 已被删。已移除。

What Can Go Wrong: 重新加回 `[InstallDelete]` → 失败升级破坏用户已有安装。

Allowed Modification: 无（保持无 `[InstallDelete]`）。旧残留文件靠运行时「内置源只按 index 引用导入」天然忽略。

Verification Required: `verify_installer_identity.ps1` 断言 `[InstallDelete]` 不存在。

---

## Rule 006 — 内置书源加载方式（不 glob）

Location: `lncrawl/services/sources/service.py` 中 `_build_local_registry()`

Why: 内置源必须只按 `index.crawlers` 引用的 `file_path` 导入，不 `glob` 目录。这样升级残留的旧 crawler 文件不会被激活。

Historical Reason: 第四轮修复（配合移除 InstallDelete）实现安全升级。

What Can Go Wrong: 改回 `glob` → 升级残留的失效 crawler 被加载，可能冲突或崩溃。

Allowed Modification: 用户源 `%APPDATA%\XiaoXiongNovel\sources\zh` 仍可 glob（本地新增无需重建索引）。内置源不得 glob。

Verification Required: `verify_distribution_runtime.py` 中 stale bundled 回归（额外 stale 文件不被激活）。

---

## Rule 007 — 官方书源索引

Location: `sources/_index.json`、`sources/_index.zip`

Why: 官方全量索引，由 CI `index-gen` 维护。中文发行版用独立的离线构建索引。

Historical Reason: 不运行 `make index-gen`，避免覆盖官方索引或埋入网络操作。

What Can Go Wrong: 运行 `index-gen` 或手动改官方索引 → 破坏上游一致性或引入无关改动。

Allowed Modification: 无（中文索引由 `scripts/build_distribution_sources.py` 生成到 `build/`）。

Verification Required: `git status` 确认官方索引未被改动。

---

## Rule 008 — 书源注册表原子切换 + FTS lease

Location: `lncrawl/services/sources/service.py`（`_SourceRegistry` / `_RegistryLease` / `_retire_registry_locked`）

Why: 重载时原子切换，旧 FTS store 靠 reader lease 在最后一个读者释放后关闭，避免竞态和内存泄漏。

Historical Reason: 第一轮审查发现竞态 + 泄漏，已用 lease 机制修复。

What Can Go Wrong: 简化掉 lease/快照 → KeyError、读已关闭 store、store 泄漏。

Allowed Modification: 仅在完全理解 lease 语义后谨慎调整。

Verification Required: `verify_distribution_runtime.py` 中 `_verify_registry_leases`（持有旧 reader 时 reload、释放后 store 关闭、重复 reload 不增长）。

---

## Rule 009 — 离线构建器输出安全标记

Location: `scripts/build_distribution_sources.py`（`OUTPUT_MARKER` / `_remove_managed_output` / `_validate_build_paths`）

Why: 防止输出目录删除任意非受管目录。输出必须在 `build\` 内，删除前须有 `.xiaoxiong-distribution-output` 标记。

Historical Reason: 第二/四轮审查发现路径删除安全隐患，已加 marker + 限制。

What Can Go Wrong: 移除 marker/限制 → 误删仓库或任意目录。

Allowed Modification: 无（安全约束不可放松）。

Verification Required: `verify_distribution_hardening.py` 中 `output-ownership` 与 `source-overlap`。

---

## Rule 010 — 远程同步/spec/GenericCrawler 禁用

Location: `lncrawl/services/sources/`、`lncrawl/services/github.py`、`lncrawl/distribution.py`

Why: 中文发行版只加载本地中文源，不请求官方在线索引、不加载外部 spec、不使用 GenericCrawler。

Historical Reason: 发行版「中文 only + 离线」核心约束。

What Can Go Wrong: 恢复远程同步/spec/generic → 中文边界被突破。

Allowed Modification: 无。

Verification Required: `verify_distribution_runtime.py` 断言无远程 fetch、外语域 no-crawler、无 generic fallback。

---

## Rule 011 — BearReader 与 backendtool 图标必须分离

Location: `res/bearreader.ico`、`res/backendtool.ico`、`scripts/build_backendtool_icon.py`、`setup_pyi.py`

Why: `BearReader.exe` 是普通用户入口，`backendtool.exe` 是命令行/LSP 工具。共用熊头像会让用户误把后台工具当成第二个主程序。

Historical Reason: 1.2.3 后续检查发现 `setup_pyi.py` 在公共构建命令中硬编码 `APP_ICON`，导致两个 PyInstaller 目标使用同一图标，现已改为逐目标传入。

What Can Go Wrong: 重新共用图标会恢复资源管理器中的入口混淆；修改熊头像来制作“工具版”又会违反批准 LOGO 不得派生修改的硬性要求。

Allowed Modification: `BearReader.exe` 和安装器只使用批准的 `res/bearreader.ico`；`backendtool.exe` 只使用由 `scripts/build_backendtool_icon.py` 生成的独立 `>_` 图标。工具图标变化也必须获得当轮明确授权。

Verification Required: `scripts/build_backendtool_icon.py --check` 验证 ICO 尺寸；`scripts/verify_windows_bundle.py` 从两个 EXE 提取实际图标并断言摘要不同。
