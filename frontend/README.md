# BearReader Web 客户端

本仓库维护 BearReader 的简体中文 Web/PWA 客户端，提供任务请求、小说获取、书架管理、在线阅读和导出文件生成等界面。客户端集成到 Windows 中文发行版；该发行版只加载和展示中文书源，并由本地 WebView 启动。

本项目基于上游 [lncrawl-web](https://github.com/rolandng84/lncrawl-web) 修改并独立维护，不代表上游项目、Microsoft、书源网站或字体作者提供官方支持或背书。项目代码采用 GPL-3.0，第三方组件和字体适用各自许可证，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 环境与启动

### 前置要求

- Node.js LTS（`.nvmrc` 使用 `lts/*`）
- Yarn 1.x
- 运行在 `http://localhost:8080` 的后端 API（开发模式）

```bash
# 按锁文件安装依赖
yarn install --frozen-lockfile

# 启动开发服务器：http://localhost:3000
yarn dev

# 中文本地化审计
yarn audit:zh

# ESLint
yarn lint

# TypeScript 检查并构建生产版本
yarn build
```

生产构建输出到 `dist/`。

## API 与后端集成

`src/config.ts` 定义 API 基地址：

- 开发模式：`http://localhost:8080`
- 生产模式：空字符串，使用与前端相同的来源

生产环境的 `API_BASE_URL` 必须保持为空字符串，不能设为 `/api`。客户端请求本身已经包含 `/api`，增加该前缀会产生 `/api/api/...`。

### Windows 本地自动登录

Windows WebView 以 `/?authToken=<JWT>` 启动。该 JWT 对应本地 ADMIN/VIP 用户，并包含 LOCAL scope。前端启动流程必须满足以下约束：

1. 从 query 读取 `authToken`，立即使用 `history.replaceState` 从地址栏删除它，同时保留 path、其他 query 和 hash。
2. 使用该 token 作为显式 Bearer Authorization 请求 `GET /api/auth/me`。响应体直接是 `User`，不是登录响应对象。
3. 若响应包含 `X-Refresh-Token`，使用刷新后的 token；否则继续使用启动 token。认证结果必须写入与普通登录兼容的 Redux Persist 状态。
4. 不得在日志、错误消息或持久 URL 中输出 token。认证失败必须明确清除当前认证并回到未登录界面，不得伪装成功或循环重试。
5. `/api/auth/me` 的刷新 token 和 401 处理必须绑定请求实际所属账号。账号切换后，旧账号的迟到响应不得更新或登出当前账号。

客户端仍保留登录和找回密码页面，供自动认证失败或服务器模式使用。

## 产品与汉化规范

### 品牌和语言

- 用户可见品牌固定为 `BearReader`。
- 界面语言、HTML `lang` 和 PWA manifest `lang` 固定为 `zh-CN`。
- 用户可见内容不得重新出现 `Lightnovel Crawler`、`LightnovelCrawler`、`LnCrawl`、`LNCrawl` 或 `lncrawl` 等旧品牌。仓库名、API、命令、文件路径等纯技术上下文不受此限制。
- Windows 中文发行版只展示中文书源。书源文案必须依据真实域名、能力和后端字段展示。
- `has_mtl` 表示书源“含机器翻译”或“包含机器翻译内容”，不能写成“支持机器翻译”等会虚构翻译功能的文案。

### 汉化范围

以下用户可见内容必须使用简体中文：

- 所有页面、组件、导航、按钮、客户端自有的提示和错误文案、确认框及占位符
- `aria-label`、`alt`、`title` 等无障碍或辅助属性
- SVG、HTML 中的可见文本
- HTML/PWA 元数据、manifest、应用名称和描述
- 使用教程及其引用的页面、菜单和操作名称

文案必须与真实 UI 和实现行为一致。不得为了“翻译完整”而描述不存在的快捷键、菜单、按钮或后端能力。

必要技术词可以保留，例如 URL、API、HTTP、PWA、EPUB、PDF、MOBI、JSON 和 VIP。后端、API 或第三方返回的必要原始诊断文本可以作为诊断内容保留，但不得替代可控的客户端 UI 文案，也不得通过宽泛白名单放行。raw enum/API key 只能存在于非 UI 技术上下文，不能借白名单作为英文界面文案。

### 统一术语

| 概念 | 中文界面用语 |
| --- | --- |
| Request / Job request | 任务请求 |
| Crawler / Source | 书源 |
| Library | 书架 |
| Fetch | 获取 |
| Artifact | 导出文件 |
| Create artifact | 生成导出文件 |
| Tracked novel | 追更小说 |
| Referrer | 邀请人 |
| `has_mtl` 筛选 | 含机器翻译 |
| `has_mtl` 详情 | 包含机器翻译内容 |

修改术语前必须搜索全部用户可见位置，并同步页面、导航、教程、错误文案和无障碍文本，不能只改单个组件。

### 中文客户端功能边界

- 不显示注册入口，直接访问 `/signup` 也不能呈现注册页。
- 不显示捐赠、隐私政策或服务条款入口；后续同步上游代码时不得恢复。
- 后端注册 API 或公开法律 Markdown/HTML 文件是否存在，与前端是否提供 UI 入口是不同层面。不要仅因静态文件仍在仓库中就恢复入口。
- 登录和找回密码是认证失败及服务器模式的回退，不属于注册入口。

## 中文本地化发布门禁

`yarn audit:zh` 是确定性的发布门禁。`scripts/audit-localization.mjs` 扫描：

- `src/`
- `public/`
- `index.html`
- `vite.config.ts`

审计覆盖旧品牌、JS/JSX/TS/TSX 字符串、模板静态片段、JSX 文本和 UI 属性、消息调用、本地对象映射，以及 HTML/SVG 可见文本和 `aria-label`、`alt`、`placeholder`、`title`。脚本自带 25 个内存回归样例，用于防止动态模板、raw key、对象属性/spread、HTML 属性和消息文案等漏检。

不得为了通过审计添加宽泛白名单。只允许完整、明确的技术词或精确技术短语；raw enum/API key 只能在明确的非 UI AST 上下文放行。

每次合入或发布至少执行：

```bash
yarn audit:zh
yarn lint
yarn build
git diff --check
```

依赖发生变化时还必须执行：

```bash
yarn install --frozen-lockfile
```

## 构建与 PWA

Vite 配置位于 `vite.config.ts`：

- `dist/` 为生产构建目录。
- `vite-plugin-pwa` 使用 `autoUpdate` 注册方式。
- manifest 名称和短名称均为 `BearReader`，语言为 `zh-CN`。
- Workbox 缓存构建后的 JS、CSS、图标、图片、SVG 和字体，并排除 `/api`、`/static`、`/docs` 的导航回退。

发布前必须核对：

```text
dist/index.html
dist/manifest.webmanifest
```

确认 `dist/index.html` 的页面标题、`lang` 和资源路径，以及 manifest 的名称、描述和语言仍为中文客户端配置。

后端集成应固定经过审查的前端 commit SHA 或对应的 `dist/` 构建产物，不得使用浮动、未审查的版本。README 不记录具体 SHA；版本固定应由后端构建配置或发布流程完成。

## 项目结构

| 路径 | 用途 |
| --- | --- |
| `src/pages/` | 路由级页面和路由定义 |
| `src/components/` | 布局、阅读器和共享组件 |
| `src/store/` | Redux Toolkit 状态及 Redux Persist 配置 |
| `src/utils/` | Axios 认证、错误处理、主题等工具 |
| `src/locales/zh-CN.ts` | 共享中文文案和枚举映射 |
| `scripts/audit-localization.mjs` | 中文本地化审计门禁 |
| `src/config.ts` | API 基地址及品牌常量 |
| `vite.config.ts` | 开发服务器、构建拆包和 PWA 配置 |

## CI

`.github/workflows/build.yml` 在 push 和 pull request 时：

1. 按 `.nvmrc` 设置 Node.js，并缓存 Yarn 依赖。
2. 使用 `yarn install --frozen-lockfile` 安装依赖。
3. 运行 `yarn lint` 和 `yarn build`。
4. `main` 分支构建会把 `dist/` 发布到 `artifacts` 分支。
5. 上游仓库的 `main` 构建会触发后端仓库的 `web-build-updated` 事件。

当前 CI 不替代 `yarn audit:zh`；发布或合入前仍必须按本 README 手动执行完整门禁。

`.github/workflows/generate-policy-html.yml` 在隐私与联网说明、使用说明或生成脚本变更时生成 `public/*.html`。这些静态文件说明本地数据、第三方联网和软件使用边界，但中文客户端当前不提供用户可见入口。

## 变更流程

1. 修改文案前，先核对真实 UI、路由、按钮名称和后端响应契约。
2. 搜索共享组件、移动端/桌面端布局、无障碍属性、教程和静态资源，保证同一行为使用同一术语。
3. 不手工绕过、删除或弱化中文审计；若确需技术词白名单，只添加精确项并补回归样例。
4. 每次改动保持单一任务，避免夹带无关重构或依赖升级。
5. 完成发布门禁和定向自审后，先接受独立审查，再提交。
6. 未获得明确批准时不提交；提交后也不要自动 push。

### 发布检查清单

- [ ] 品牌、语言和术语符合本 README
- [ ] UI 文案与真实功能、教程和无障碍文本一致
- [ ] Windows 自动登录仍安全清除 token，且账号切换无竞态
- [ ] 注册、捐赠和法律入口未被恢复
- [ ] `yarn audit:zh` 通过
- [ ] `yarn lint` 通过
- [ ] `yarn build` 通过
- [ ] `git diff --check` 通过
- [ ] 依赖变更已通过 `yarn install --frozen-lockfile`
- [ ] `dist/index.html` 与 `dist/manifest.webmanifest` 已核对

## 许可证

本项目使用 GNU General Public License v3.0，详见 `LICENSE`。第三方 JavaScript 依赖和字体不因收录在本仓库中而改用 GPL，具体来源、许可边界和公开分发注意事项见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
