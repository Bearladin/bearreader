# BearReader 发行工作流

此分发版故意与上游 Lightnovel Crawler 的发布自动化隔离。

| 工作流 | 行为 |
| --- | --- |
| `release.yml` | 仅在 Windows 上验证、构建 `xiaoxiong-novel.exe` 和 `xiaoxiong-novel-setup.exe`，并创建包含 GPL 源码材料的草稿发行版。 |
| `web.yml` | 仅验证已提交的本地化前端元数据和 SHA；不会检出上游 artifacts 分支，也不会提交文件。 |
| `index-gen.yml` | 离线重建并验证 `sources/zh` 暂存目录；不会运行 `scripts/index_gen.py`、访问书源索引或自动提交。 |

不会从这些工作流发布 Wheel、Docker 镜像、macOS/Linux 二进制、PyPI 包或上游短链接。发布前请遵循 [BUILD_AND_RELEASE.md](../BUILD_AND_RELEASE.md) 中的手工验收和 GPL 源码归档步骤。
