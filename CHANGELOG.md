# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
