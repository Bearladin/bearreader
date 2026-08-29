# 第三方组件与许可证说明

更新日期：2026 年 8 月 25 日

本文件列出 BearReader 中对发行合规特别重要、随 Windows 发行包内置或直接影响应用许可边界的主要第三方组件。各组件仍由其版权持有人所有，并适用各自许可证；项目根目录的 GPL-3.0 不会替代第三方许可证。

完整依赖版本与许可证清单见 [docs/DEPENDENCY_LICENSES_PY.md](docs/DEPENDENCY_LICENSES_PY.md)（Python，176 项）与 [docs/DEPENDENCY_LICENSES_FRONTEND.md](docs/DEPENDENCY_LICENSES_FRONTEND.md)（前端）；两者由 2026-08-29 的 `uv.lock` 与 `frontend/yarn.lock` 生成。依赖更新后应重新生成。

## 上游项目

| 组件 | 用途 | 许可证与来源 |
| --- | --- | --- |
| Lightnovel Crawler | 后端、抓取引擎、CLI 与服务基础 | GPL-3.0；<https://github.com/lncrawl/lightnovel-crawler> |
| lncrawl-web | Web/PWA 客户端基础 | GPL-3.0；<https://github.com/rolandng84/lncrawl-web> |

BearReader 是独立维护的修改版。上述名称仅用于说明来源，不表示上游作者对本发行版提供支持或背书。

## 运行时组件

| 组件 | 当前用途 | 许可证与处理要求 |
| --- | --- | --- |
| EbookLib | EPUB 读取与生成 | AGPL-3.0；<https://github.com/aerkalov/ebooklib>。精确版本由 `uv.lock` 确定。对外提供包含该组件的网络应用或二进制时，应同时提供对应源码，并保留 AGPL 许可证和网络源码获取要求。 |
| edge-tts 7.2.8 | 在线神经语音合成 | LGPL-3.0；<https://github.com/rany2/edge-tts>。许可证全文见 `res/LICENSE-EDGE-TTS.txt`。发行源码和构建材料应允许使用者以修改后的兼容版本重新构建应用。 |

其他 Python 和前端依赖包括 MIT、BSD、Apache-2.0、BlueOak 等许可证组件。锁文件是版本清单，不等于许可证清单；对外二进制发行前必须根据实际锁定版本生成并随包提供完整 notices。

## 字体

| 字体 | 状态 | 许可证与来源 |
| --- | --- | --- |
| 小熊楷体（XiaoXiong Reader Kai） | LXGW WenKai GB Screen 的 GBK 子集和 WOFF2 修改版，已使用中性内部名称 | OFL-1.1；来源与修改说明见 `res/THIRD_PARTY_READER_FONTS.md`，许可证见 `res/LICENSE-XIAOXIONG-READER-KAI-OFL.txt`。 |
| 小熊宋体（XiaoXiong Reader Serif） | Noto Serif CJK SC 的 GBK 子集和 WOFF2 修改版，已使用中性内部名称 | OFL-1.1；来源与修改说明见 `res/THIRD_PARTY_READER_FONTS.md`，许可证见 `res/LICENSE-XIAOXIONG-READER-SERIF-OFL.txt`。 |
| Geist Mono | 前端代码和等宽文本显示 | OFL-1.1；Copyright 2024 The Geist Project Authors；<https://github.com/vercel/geist-font>。 |
| 小熊楷体 / 小熊宋体（阅读器） | 阅读器默认字体 | 见上表。 |

历史说明：私人版本（≤1.1.4）曾使用 Cabinet Grotesk 与 Switzer（Fontshare 服务条款字体，不允许本仓库再分发）。1.2.3 起界面改用系统字体栈，本仓库不含任何 Cabinet/Switzer 字体文件。

## 安装器资源

| 组件 | 用途 | 许可证与来源 |
| --- | --- | --- |
| Inno Setup 简体中文翻译 | 安装器中文界面 | MIT；固定来源和许可证见 `installer/languages/LICENSE-ChineseSimplified.txt`。 |
| Inno Setup | 生成 Windows 安装包 | Inno Setup License；<https://jrsoftware.org/>。编译器本身不提交到仓库，生成的安装器保留其运行时版权信息。商业环境使用时还应核对 Inno Setup 当前商业许可政策。 |

## 商标与背书

第三方名称、网站和字体名称仅用于描述来源、兼容性与许可证。除非版权持有人另有书面说明，否则不表示其与 BearReader 存在隶属、赞助、授权代理或背书关系。
