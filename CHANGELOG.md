# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **A close confirmation before the app window shuts** — Clicking X or Alt+F4 in app mode first asks the browser's leave-confirmation dialog, so an accidental click cannot kill a running reading or download session; a "关闭时确认" switch in the reader settings (on by default) turns it off. The service worker's self-reload on updates stays silent — it is lossless and must not ask.
- **The app-mode browser no longer bloats the data directory** — The window is an Edge app profile that used to accumulate hundreds of MB of wallet/shopping/visual-search components and update caches inside the app data folder; launch flags now disable those side components while keeping rendering, cookies, sessions and Safe Browsing untouched.
- **本地 EPUB 导入** — “全部小说”支持拖拽或文件选择导入单个 EPUB，导入前可预览并编辑书名/作者；有封面时提取保存，无封面时使用动态占位封面，完成后直接打开小说详情。
- **本地 TXT 导入** — 支持编码确认、章节识别和五种段落整理方式，按字节范围逐章写入现有阅读器。

### Fixed

- **本地导入过程更清晰稳定** — 禁止浏览器翻译应用界面，导入弹窗保持紧凑并显示节流后的真实分析与保存进度，EPUB 正文开头与阅读器完全重复的章节标题会被安全隐藏。
- **本地 EPUB/TXT 上传恢复正常** — 移除把文件表单错误序列化为 JSON 的全局请求头，并让参数验证错误显示具体原因。
- **本地书架界面去除多用户残留** — 新建书架不再提供公开选项，卡片不再显示公开状态或本地管理员所有者信息，小说目录也移除不符合中文阅读习惯的字符序书名排序。
- **The desktop launcher no longer lingers as a zombie process** — When every exit signal misfires at once (window handed to an untracked process, title probe hitting a foreign window, bye beacon lost), the keep-alive loop used to wait forever while holding the single-instance lock; it now winds down after 2 minutes without a window sighting and records a diagnostic, so a relaunch after an unclean close recovers quickly.
- **"Already running" is now visible instead of a silent exit** — When the single-instance lock stays held after the takeover wait, a self-dismissing message box tells the user to end the leftover processes instead of double-clicking doing nothing.
- **A damaged legacy database no longer breaks the whole source list** — The per-domain novel count is decorative; when its query fails, sources still load without counts and the failure is logged, instead of failing the entire endpoint (previously required wiping the data directory).
- **EPUB 导入失败与取消状态保持一致** — 状态更新采用条件迁移，提交目标可从中断中恢复，过期会话和孤儿文件会被清理，内部导入任务不能被通用重放或误取消。
- **An empty source registry can no longer masquerade as a healthy startup** — A damaged or quarantined source bundle now fails before replacing the active registry, reload failures keep the previous sources live, and the health endpoint reports loaded crawler and domain counts.
- **Windows startup now uses UTF-8 and preserves failure diagnostics** — Both bundled executables enable Python's UTF-8 mode before interpreter startup, while desktop launch failures and missing browser windows write a bounded UTF-8 log under the application data directory for troubleshooting paths on any Windows locale.
- **The job scrubber no longer crashes on stuck legacy jobs** — A root job left unfinished by an older version (e.g. killed mid-run) crashed the background scrubber loop forever with "Only finished jobs can be deleted", halting every cleanup duty; the delete pass now selects finished jobs only, and stuck jobs of any state are cancelled after 16 hours so they get reaped on the next pass.
- **EPUB 导入限制资源占用并拒绝媒体内容** — 上传限制为 50 MB、解压限制为 100 MB，分析阶段拒绝音视频和脚本，提交阶段只读取正文与实际引用的静态插图。
- **前端分包加载失败可以自恢复** — 首次 preload 路由错误静默刷新，重复失败显示同步中文错误页，并避免服务工作线程刷新形成循环。

## [1.3.1] - 2026-08-31

### Added

- **Quick font-size buttons in the reader navbar** — Plus/minus buttons with a 12–32 px clamp shared by the settings panel.
- **Keyboard shortcuts in the reader** — `←`/`→` turn chapters (TTS paragraphs while reading aloud), `Space` scrolls a screen and page-turns at the chapter bottom when idle, `S` toggles reading aloud, `+`/`−` adjust the font size on both main and numpad keys, and system media keys control TTS through MediaSession; a shortcuts row in the reader settings panel lists them all.
- **TTS keeps reading across chapter turns** — Reaching the end of a chapter or navigating mid-playback continues into the next chapter from its start.
- **Reading position resume** — The reader reopens a chapter at the last scroll offset per novel, so continue-reading lands where you stopped.
- **Auto-scroll and TTS-follow scrolling** — An optional steady scroll with an adjustable speed that cancels on manual input, and the view smoothly follows the paragraph being read; the navbar button shows an active highlight while scrolling, defaults to 100 px/s, ignores manual input for 300 ms after being toggled, and explains itself when opened at the chapter bottom.
- **Search and sorting for novels and libraries** — The catalog gains a sort dropdown, and library listings gain search plus five sort orders.

### Fixed

- **Reader controls no longer interfere with scrolling or TTS** — Main-keyboard and numpad font shortcuts work consistently, Space no longer reactivates a mouse-clicked toolbar action, chapter scroll saves do not reset speech, and chapter changes release old audio resources.
- **Cancelling any job of a multi-step request cancels the whole request** — Cancelling one volume of a 20-volume full-novel fetch used to leave the other 19 running; the cancel endpoint now climbs to the root job and tears down the entire tree, while standalone jobs still cancel alone.
- **The chapter header shows only the title** — The "章节 x/y · 更新于 …" meta line is removed: TTS read it aloud every chapter and its relative time rendered in English; the count and timestamp stay visible on the novel details page.
- **Novel list results stay consistent with their filters** — Library search counts use the proper join without replacing the full shelf count, and stale catalog or library requests can no longer overwrite newer results.
- **The misleading local-source reload action is no longer shown** — BearReader does not yet expose a safe custom-source workflow, so the release UI no longer presents an internal reload operation as a user feature.
- **Batch volume and chapter fetch jobs now show the novel title** — The batch creators skipped the novel-title fallback the single-item creators have, so jobs created from the novel page showed only the item count.
- **The TTS audio cache is a real LRU with a size cap** — Hits now refresh recency and a 64 MB total cap bounds memory, replacing the FIFO behavior the old comment wrongly claimed.

## [1.3.0] - 2026-08-29

### Changed

- **First release from the clean monorepo** — Frontend sources now live in `frontend/` inside this repository and the embedded build in `lncrawl/server/web/` is pinned by `frontend-manifest.json` instead of an external frontend commit SHA, so every release tag rebuilds the whole product from one checkout.
- **The interface runs on system fonts** — The UI uses the system CJK font stack (Microsoft YaHei / PingFang SC / Noto Sans CJK SC) and the reader keeps its bundled OFL fonts; the 1.1.x-era Cabinet Grotesk and Switzer files are gone, so no non-redistributable font ships with the app.
- **The Windows portable ZIP is the default release** — The release workflow rebuilds the frontend from the same tag, verifies both executables, and publishes the portable ZIP plus one full source archive with licenses, third-party notices and SHA256 checksums; installers are no longer built by default.
- **Distribution docs and CI target the public workflow** — Support, contribution, security and issue templates point to this repository in Chinese, CI validates the embedded frontend on the same platform it was built for, and the release guard refuses to overwrite a published version.

## [1.2.4] - 2026-08-29

### Changed

- **The backend tool has its own identity** — Gives `backendtool.exe` a restrained terminal icon so it cannot be confused with the BearReader application, while leaving the approved bear artwork untouched.

### Fixed

- **Job failures are Chinese from end to end** — Stores every crawler diagnosis and scheduler fallback in Chinese while the client translates structured and legacy English records already present in local databases.
- **Generated job titles no longer leak English labels** — Localizes volume, chapter, image, artifact and translation task names emitted by the server, including the batch-volume title previously shown as `Volumes`.

## [1.2.3] - 2026-08-29

### Changed

- **A quieter BearReader interface** — Reworks the navigation and main library screens around a warm-paper visual system, removes the obsolete local-admin avatar card, and adds list/grid viewing where it improves browsing.
- **Neutral source capability labels** — Gives search-capable and URL-only source hints the same restrained neutral treatment so metadata does not compete with content.
- **White is now the default reader theme** — Applies only when no reader preference has been saved, preserving every existing user's chosen theme.
- **Bookshelf novels default to the list view** — Applies only when no view preference has been saved, preserving each user's earlier grid/list choice.

### Fixed

- **Cancellation messages are Chinese and role-neutral** — New jobs store clear local wording, while the client translates cancellation reasons already saved by earlier versions.
- **The complete novel collection is pageable** — Removes the client-side 100-item total cap while keeping server-side page loading, so every stored novel remains reachable.
- **The redesigned client passes the Chinese-only gate** — Replaces decorative English section captions and uses non-sentence storage keys without changing stored user content.

## [1.2.0] - 2026-08-25

### Added

- **Offline Chinese reader fonts** — Adds checksum-pinned GBK webfont subsets for XiaoXiong Kai and Serif, while keeping system Microsoft YaHei as the zero-size default and shipping each upstream OFL notice.

### Fixed

- **Cleaner local UI metadata and table of contents** — Hides the stale source-file commit count and changes the reader contents dialog to a fixed serial column, left-aligned chapter titles and full-row hover/click feedback.
- **Versioned installer discovery** — The Windows release workflow now verifies and uploads the version-and-date installer name that Inno Setup actually produces.


## 上游历史版本

BearReader 派生自 lightnovel-crawler 与 lncrawl-web；2018–2026 年的上游原始更新日志见 [docs/UPSTREAM_CHANGELOG.md](docs/UPSTREAM_CHANGELOG.md)。
