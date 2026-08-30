# BearReader 发行工作流

此分发版故意与上游 Lightnovel Crawler 的发布自动化隔离。

| 工作流 | 行为 |
| --- | --- |
| `release.yml` | 仅在 Windows 上验证、构建 `BearReader-portable-*.zip`（绿色版）与 `BearReader-source-*.zip`（GPL 源码材料），并创建草稿发行版。 |
| `web.yml` | 在 Windows 上完整重建前端（含中文文案审计），并与提交的本地化构建产物比对；不会检出上游 artifacts 分支，也不会提交文件。 |
| `index-gen.yml` | 离线重建并验证分发用书源目录（`build/distribution-sources`）；不会运行 `scripts/index_gen.py`、访问书源索引或自动提交。 |
| `lint.yml` | 以 Python 3.9 / 3.11 矩阵运行 pyright 与 ruff 静态检查。 |

不会从这些工作流发布 Wheel、Docker 镜像、macOS/Linux 二进制、PyPI 包或上游短链接。发布前请遵循 [BUILD_AND_RELEASE.md](../BUILD_AND_RELEASE.md) 中的手工验收和 GPL 源码归档步骤。
