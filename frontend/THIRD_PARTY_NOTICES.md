# 第三方组件与字体说明

更新日期：2026 年 8 月 25 日

本客户端基于 [lncrawl-web](https://github.com/rolandng84/lncrawl-web) 修改，项目代码遵循仓库根目录的 GPL-3.0。npm/Yarn 依赖和字体继续适用各自许可证；`yarn.lock` 用于固定版本，但不替代许可证文本。

## 字体

| 字体 | 用途 | 许可证与来源 |
| --- | --- | --- |
| 小熊楷体（XiaoXiong Reader Kai） | 阅读器正文 | OFL-1.1；修改自 LXGW WenKai GB Screen，采用 GBK 子集、WOFF2 转换和中性内部名称。来源：<https://github.com/lxgw/LxgwWenKai-Screen>。 |
| 小熊宋体（XiaoXiong Reader Serif） | 阅读器正文 | OFL-1.1；修改自 Noto Serif CJK SC，采用 GBK 子集、WOFF2 转换和中性内部名称。来源：<https://github.com/notofonts/noto-cjk>。 |
| Geist Mono | 代码和等宽文本 | OFL-1.1；Copyright 2024 The Geist Project Authors；<https://github.com/vercel/geist-font>。 |
| Cabinet Grotesk | 标题 | Copyright 2017–2021 Indian Type Foundry；受 <https://www.fontshare.com/terms> 约束，不属于 GPL 或 OFL。 |
| Switzer | 界面正文 | Copyright 2015–2021 Indian Type Foundry；受 <https://www.fontshare.com/terms> 约束，不属于 GPL 或 OFL。 |

Cabinet Grotesk 和 Switzer 当前只用于私人、本地发行线。不得把项目的 GPL 许可证理解为允许独立或公开再分发这些字体文件；公开仓库或公开二进制发行前，应替换字体或取得明确许可。

小熊楷体、小熊宋体和 Geist Mono 的 OFL 版权声明与完整许可证必须随字体文件和最终发行包提供。前端与后端发行材料应使用同一份来源和修改记录，避免许可证说明漂移。

## JavaScript 依赖

React、Ant Design、Redux Toolkit、Axios、Lodash、Vite 等依赖按照各自 MIT、BSD、Apache-2.0、BlueOak 或其他许可证提供。对外分发构建后的前端资源时，应根据该发行提交的 `yarn.lock` 生成完整依赖 notices，并保留许可证要求的版权声明。

## 无背书声明

第三方名称只用于说明来源和许可证，不表示相关作者、组织或服务提供者对 BearReader 提供支持或背书。
