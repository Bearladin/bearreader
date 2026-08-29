# BearReader 项目状态

> 本文件只记录公开版本的客观状态，不包含内部开发过程。

## 当前版本

- 当前公开发布：`v1.3.0`（首个公开标签）
- 版本文件：`lncrawl/VERSION`

## 产品定位

BearReader 是单用户中文 Windows 桌面小说下载与阅读应用：

- 前端源码位于 `frontend/`（React/Vite），构建产物嵌入 `lncrawl/server/web/`（生成物，禁止手改）；
- 后端为 Python（FastAPI + 爬虫引擎），中文书源位于 `sources/`；
- 发行形态为 Windows 绿色 ZIP（`BearReader.exe` 主程序 + `backendtool.exe` 后台工具）；安装器仅在明确要求时制作；
- 发行版只加载中文内置书源和中文用户书源。

## 来源与一致性

- 派生来源见 [UPSTREAM.md](UPSTREAM.md)；
- 嵌入前端与 `frontend/` 源码树的一致性由 `frontend-manifest.json` 校验（构建清单记录源码树摘要与产物摘要）；
- 发行 ZIP、源码归档与标签必须来自同一提交。

## 品牌资产

`res/bearreader.ico` 及全部 PNG 尺寸均由唯一批准原图直接缩小生成（不逐级缩放、不裁剪、不调色）。原图暂不随仓库分发，其身份记录为：

```text
文件名：Minimalist Polar Bear App Icon.png
尺寸：1254×1254
SHA256：7C6433FDD9E467D603A5CDB922A4B792B336DAEF51B407FAA9A62D976CEE3988
```

公开分发权利确认后，原图将作为只读品牌源资产补充入库。`backendtool.exe` 的终端图标由 `scripts/build_backendtool_icon.py` 用项目自有几何图形生成，与熊头像无关，两 EXE 图标不得相同（发行门禁强制）。

## 支持平台

- Windows 10/11 x64（绿色 ZIP，无需安装）
- 界面语言：仅简体中文

## 已知限制

- TTS 音频缓存按条数限制（非按字节），长时间连续朗读可能占用较多内存，见仓库 Issue 跟踪；
- 在线朗读、书源抓取依赖对应站点的可用性。

## 下一版本方向

- TTS 缓存改为按字节限制的真实 LRU；
- 持续维护中文书源可用性。
