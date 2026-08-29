import { useState } from 'react';
import { APP_VERSION } from '@/version';
import { Divider, Flex, Pagination, Typography } from 'antd';
import type { ReactNode } from 'react';

const { Title, Paragraph, Text } = Typography;

interface ChangeEntry {
  version: string;
  date: string;
  items: ReactNode[];
}

const entries: ChangeEntry[] = [
  {
    version: '1.2.4',
    date: '2026-08-29',
    items: [
      <span key="backendtool-icon">
        后台工具改用独立的深灰「&gt;_」终端图标，与 BearReader 熊头像清晰区分；BearReader 品牌图标继续严格使用已确认的原始素材，不做任何修改。
      </span>,
      <span key="job-diagnostics">
        任务失败诊断和任务标题完整中文化：网络超时、站点防护、缺少参数及内部异常等提示不再显示英文；旧数据库中的结构化英文错误也会自动转换，批量分卷任务标题改为「N 个分卷」。
      </span>,
    ],
  },
  {
    version: '1.2.3',
    date: '2026-08-29',
    items: [
      <span key="redesign">
        界面全面升级为克制的暖纸质感设计：重构导航、任务、小说、书架、书源、更新日志、教程与阅读器外壳，统一排版、卡片层级和列表/网格浏览方式；侧边栏改为 BearReader 品牌区，不再显示旧的本地管理员头像卡片。
      </span>,
      <span key="source-tags">
        书源能力提示改为中性灰普通标签，「支持书名搜索」与「到这里搜索具体书获取 URL」使用一致样式，减少不必要的高亮。
      </span>,
      <span key="reader-default">
        新用户及尚未保存阅读设置的用户默认使用纯白阅读主题；已有用户保存的阅读主题保持不变。
      </span>,
      <span key="cancel-message">
        任务取消原因改为清晰的中文提示，并兼容显示旧版本已经保存的英文取消记录。
      </span>,
      <span key="novel-pagination">
        修复「全部小说」只能翻阅前一部分藏书的问题，分页现在可以访问全部已收录小说，后端仍按页加载。
      </span>,
      <span key="library-list-default">
        书架中的小说列表默认使用列表视图；已保存过视图选择的用户保持原有选择。
      </span>,
    ],
  },
  {
    version: '1.2.2',
    date: '2026-08-29',
    items: [
      <span key="logo">
        品牌图标使用最终确认的北极熊原始素材统一生成，覆盖应用界面、favicon、PWA、任务栏与可执行文件；完成过渡后，发行包只保留 BearReader.exe 和 backendtool.exe。
      </span>,
    ],
  },
  {
    version: '1.2.1',
    date: '2026-08-27',
    items: [
      <span key="brand">
        应用更名 BearReader：窗口、任务栏、快捷方式与安装器统一新品牌与黑底小熊标识；主程序为 BearReader.exe，后台工具为 backendtool.exe，旧名称文件保留一个版本周期作为兼容入口。
      </span>,
    ],
  },
  {
    version: '1.2.0',
    date: '2026-08-25',
    items: [
      <span key="reader-fonts">
        阅读字体：默认使用系统微软雅黑，新增离线自托管的「小熊楷体」和「小熊宋体」；两款内置字体覆盖完整 GBK
        汉字范围，旧版本保存的无效英文字体会自动恢复为微软雅黑。
      </span>,
      <span key="toc-source-cleanup">
        界面细节：阅读目录改为固定序号列与左对齐标题，整行可点击并提供悬停反馈；书源页面隐藏容易引起误解的代码提交次数及对应排序项。
      </span>,
    ],
  },
  {
    version: '1.1.10',
    date: '2026-08-24',
    items: [
      <span key="single-instance">
        稳定性：新增 Windows 单实例保护——重复启动会在上一个实例退出后自动接管，或提示"程序已经在运行"；关闭客户端后进程快速退出（页面关闭通知 + 关窗判定提速）。
      </span>,
      <span key="job-delete">
        任务管理：已结束的任务可单独删除记录、也可一键清空全部已结束任务（小说与导出文件不受影响），运行中的任务不可删除；移除必现报错的「重试失败项」按钮；界面不再显示任务发起人信息，首页只保留「全部任务请求」。
      </span>,
      <span key="job-ux">
        任务页面体验：状态与类型标签补全（已暂停、检查更新并补全等）；搜索任务标题改为中文（搜索「书名」· 全部书源/域名）；时间格式统一为 2026/8/24 22:55；快速切换任务不再显示旧数据；任务轮询不再堆积请求（窗口隐藏时自动放慢）。
      </span>,
      <span key="reader">
        阅读与小说详情：新增「继续阅读」（回到最近打开的章节）与「检查更新并补全」（检查目录新增章节、补全缺失正文并重建 EPUB）；章节切换不再被旧响应覆盖；目录弹窗每页 100 章；停止朗读后迟到的语音资源立即释放。
      </span>,
      <span key="backend">
        后端修复：任务筛选的完成状态按实际条件过滤；调度器停止后旧线程不再复活；静态资源令牌过期返回 401 而非 500；朗读语音合成增加预热，点击朗读几乎立即出声。
      </span>,
      <span key="sources">
        书源：修复 xbanxia 分卷边界（第 101 章正确进入第二卷），卷名使用中文「第 N 卷」。
      </span>,
    ],
  },
  {
    version: '1.1.9',
    date: '2026-08-23',
    items: [
      <span key="tts-legacy-voice">
        修复：第一次点击朗读报错（请求 404）——旧版本保存的系统语音名不在新音色列表内，朗读请求被拒绝。现在旧值自动归一为默认晓晓，非法音色由服务端静默回退，首次点击即可正常朗读。
      </span>,
    ],
  },
  {
    version: '1.1.8',
    date: '2026-08-23',
    items: [
      <span key="tts-engine">
        朗读引擎升级为在线神经语音（Edge-TTS）：9 个中文音色可选（普通话 6 + 台湾国语 3），默认晓晓；语速范围调整为 0.5x–1.5x；新增句间停顿设置（默认 300 毫秒）。朗读需要联网，断网时有明确提示。
      </span>,
      <span key="tts-voices">
        语音列表不再显示系统自带的其他语种语音（原 23 个系统/在线语音仅保留中文音色）。
      </span>,
    ],
  },
  {
    version: '1.1.7',
    date: '2026-08-23',
    items: [
      <span key="tts-voice-fallback">
        修复：系统语音列表加载为空时点击朗读无反应——回退到系统默认语音，点击即朗读且不重复。
      </span>,
    ],
  },
  {
    version: '1.1.6',
    date: '2026-08-22',
    items: [
      <span key="webview-keepalive">
        修复：浏览器启动较慢时应用被误判「窗口未打开」而自动退出的问题。
      </span>,
      <span key="tts">
        修复：阅读器朗读每段重复读两遍的问题。
      </span>,
      <span key="search-filter">
        修复：书名搜索漏掉「完整包含搜索词的长书名」的问题。
      </span>,
      <span key="misc">
        修复：阅读器章节自动获取失败后失效、部分书源解析失败静默产出残书、书源崩溃隐患、闲置账号清理失效。
      </span>,
    ],
  },
  {
    version: '1.1.5',
    date: '2026-08-22',
    items: [
      <span key="theme-unify">
        界面风格统一：清除旧主题残留色（阅读器外壳、图标、favicon 统一为品牌蓝），状态色与设计令牌对齐；启动画面与标题栏颜色改为深灰（消除绿色/白色闪屏）；封面占位渐变改为深色系。
      </span>,
      <span key="fonts-clean">
        移除未加载的字体引用（Roboto Slab 幽灵字体、Google Fonts 网络请求），离线启动更快。
      </span>,
      <span key="details">
        细节打磨：错误提示黄色块改为主题警告色并消除注入漏洞；选中文本与键盘焦点环纳入主题；小说列表加载改为骨架屏；搜索结果空态提示补齐。
      </span>,
    ],
  },
  {
    version: '1.1.4',
    date: '2026-08-18',
    items: [
      <span key="avatar-svg">
        小熊头像升级为 SVG 矢量格式（任意尺寸清晰不模糊），蓝色与品牌色统一。
      </span>,
      <span key="library-owner">
        书架详情页不再显示「书架所有者」信息（默认本地管理员登录，无需展示）。
      </span>,
      <span key="fonts">
        界面字体升级：标题 Cabinet Grotesk、正文 Switzer、代码 Geist Mono（自托管，离线可用）。
      </span>,
    ],
  },
  {
    version: '1.1.3',
    date: '2026-08-18',
    items: [
      <span key="cover-align">
        修复：小说/书架页封面高度不一致导致网格错位（1.1.0 重构时封面比例约束丢失所致）。封面区改用固定竖版比例（3:4），横版/竖版/无封面卡片高度完全一致。
      </span>,
    ],
  },
  {
    version: '1.1.2',
    date: '2026-08-18',
    items: [
      <span key="avatar">
        修复：小熊头像显示比例（小熊放大至充满蓝色圆，与参考图构图一致）；小说列表封面严格等高（标题区连同内边距固定高度，单行/两行/无标题卡片完全一致）。
      </span>,
    ],
  },
  {
    version: '1.1.1',
    date: '2026-08-18',
    items: [
      <span key="fixes">
        修复：本地管理员小熊头像不显示（头像组件参数覆盖顺序错误）；小说列表封面高度不对齐（标题区固定高度）；更新日志改为每个版本一张卡片；书源页移除「已停用书源」入口。
      </span>,
    ],
  },
  {
    version: '1.1.0',
    date: '2026-08-18',
    items: [
      <span key="v21">
        界面升级为「深灰低白」方案：深灰背景 + 中灰卡片 + 低饱和状态色 + 克制品牌蓝，白色只用于输入区等少量强调；书架/小说卡片去掉渐变与黑色标题条；本地管理员头像换成小熊形象。
      </span>,
    ],
  },
  {
    version: '1.0.10',
    date: '2026-08-16',
    items: [
      <span key="sidebar">
        侧边栏深色化：深炭灰导航栏 + 品牌蓝选中态（白字白图标），与浅色内容区形成清晰对比；卡片边框加深，层次更分明。
      </span>,
    ],
  },
  {
    version: '1.0.9',
    date: '2026-08-16',
    items: [
      <span key="readability">
        输入框/搜索框/下拉框占位文字与边框加深，不再看不清；卡片阴影增强，任务、书源、更新日志、教程卡片层次更清晰；修复小说页域名下拉框残留已删除书源的问题（旧书源不再出现在筛选中）。
      </span>,
    ],
  },
  {
    version: '1.0.8',
    date: '2026-08-16',
    items: [
      <span key="theme2">
        浅色主题第二轮调整：改为「灰画布 + 白卡片」双层结构，卡片带极淡阴影与清晰边框；任务列表、更新日志每条记录独立卡片化；次级文字统一加深保证可读性。
      </span>,
    ],
  },
  {
    version: '1.0.7',
    date: '2026-08-16',
    items: [
      <span key="refine">
        浅色主题细节优化：内容卡片与侧边栏降低纯白刺眼感（带灰调白 + 极淡阴影），次级文字加深保证可读性，窗口标题栏统一为浅色外观，本地管理员头像改为浅蓝色。
      </span>,
    ],
  },
  {
    version: '1.0.6',
    date: '2026-08-16',
    items: [
      <span key="theme">
        界面改为 iOS 扁平化浅色主题：蓝白配色、浅色卡片与圆角、任务状态使用 iOS 系统色（进行中/选中为绿色，完成/警告/失败/中性各有专属颜色）。
      </span>,
    ],
  },
  {
    version: '1.0.5',
    date: '2026-08-16',
    items: [
      <span key="encoding">
        修复非中文系统（英文 Windows）启动崩溃：程序输出改为 UTF-8 编码兜底，任何语言系统均可正常启动。
      </span>,
    ],
  },
  {
    version: '1.0.4',
    date: '2026-08-16',
    items: [
      <span key="search">
        书名搜索优化：只保留与书名相近的结果（实测「青山」从 50 条减到 10 条），完全匹配的书排在最前。
      </span>,
      <span key="novel-limit">
        全部小说列表最多显示 100 本，避免搜索结果堆积。
      </span>,
      <span key="source-hint">
        书源页面：<Text code>dushulai.com</Text>、<Text code>shuquta.com</Text>、<Text code>nieba.net</Text>{' '}
        增加金色提示「到这里搜索具体书获取 URL」。
      </span>,
      <span key="changelog">
        更新日志每页显示 10 条（最多 5 页）。
      </span>,
    ],
  },
  {
    version: '1.0.3',
    date: '2026-08-16',
    items: [
      <span key="search-hint">
        任务请求界面明确提示：仅 <Text code>www.mayiwsk.com</Text> 支持书名搜索（加粗显示）。
      </span>,
      <span key="sources">
        书源页面：支持书名搜索的书源置顶显示并带金色「支持书名搜索」标识；移除语言筛选与漫画/机器翻译/登录过滤按钮。
      </span>,
      <span key="export">
        导出格式只保留 EPUB 和 TXT（其他格式需要额外转换工具，暂不提供）。
      </span>,
      <span key="ui">
        界面精简：左侧导航移除「管理后台」；书架页移除「公开」开关与公开书架入口。
      </span>,
      <span key="changelog">
        更新日志分页优化：一页显示不下时才分页，最多支持 5 页，最新的更新始终在第一页。
      </span>,
    ],
  },
  {
    version: '1.0.2',
    date: '2026-08-16',
    items: [
      <span key="fullnovel">
        修复「获取此小说」无法下载全部章节的问题：任务繁忙时正文批量下载任务会被误取消，现已修复，点击即可完整下载全书正文。
      </span>,
      <span key="tutorial">
        使用教程精简为一页：按「创建任务请求 → 搜索书 → 获取书 → 导出 EPUB」四步说明核心用法。
      </span>,
      <span key="changelog">
        更新日志改为分页展示（最多 3 页），最新的更新始终显示在第一页。
      </span>,
    ],
  },
  {
    version: '1.0.1',
    date: '2026-08-15',
    items: [
      <span key="jobs">
        任务记录精简：根任务只保留 7 天、子任务只保留 3 天，历史任务列表更清爽；已下载的小说和导出的文件不受影响。
      </span>,
    ],
  },
  {
    version: '1.0.0',
    date: '2026-08-15',
    items: [
      <span key="sources">
        新增书源：<Text code>dushulai.com</Text>（来读小说）、
        <Text code>shuquta.com</Text>（说说520）；既有书源{' '}
        <Text code>nieba.net</Text> 同样仅支持粘贴 URL 抓取；书名搜索目前仅{' '}
        <Text code>mayiwsk.com</Text> 支持。
      </span>,
      <span key="search">
        新增书名搜索：任务请求中可直接输入书名搜索，无需复制小说页面 URL。
      </span>,
      <span key="ui">
        界面优化：精简左侧导航与用户卡片，完善使用教程，默认本地管理员登录。
      </span>,
      <span key="console">修复启动时出现黑色命令行窗口的问题。</span>,
      <span key="portable">新增绿色版免安装包（解压即用）。</span>,
    ],
  },
];

// 摊平为单条记录列表（最新在前）。只有条目多到一页放不下时才分页，
// 每页固定 10 条、最多 5 页，超出 5 页的早期历史不再展示。
const PAGE_SIZE = 10;
const MAX_PAGES = 5;
const MAX_ITEMS = PAGE_SIZE * MAX_PAGES;

const flatEntries = entries.flatMap((entry) =>
  entry.items.map((item) => ({
    version: entry.version,
    date: entry.date,
    content: item,
  })),
);

export const ChangelogPage: React.FC<any> = () => {
  const [page, setPage] = useState(1);

  const visible = flatEntries.slice(
    (page - 1) * PAGE_SIZE,
    Math.min(page * PAGE_SIZE, flatEntries.length),
  );

  // 同一版本的多条更新合并为一张卡片（保持顺序）
  const groups = visible.reduce<
    { version: string; date: string; items: typeof visible }[]
  >((acc, entry) => {
    const last = acc[acc.length - 1];
    if (last && last.version === entry.version) {
      last.items.push(entry);
    } else {
      acc.push({ version: entry.version, date: entry.date, items: [entry] });
    }
    return acc;
  }, []);

  return (
    <div className="br-page-container">
      <Text className="br-section-label">版本记录</Text>
      <Title level={2} className="br-page-title">更新日志</Title>
      <Paragraph type="secondary">
        当前版本：{APP_VERSION}
      </Paragraph>

      <Divider />

      {/* 时间轴式版本记录，同版本多条更新合并展示。 */}
      <Flex vertical gap={12}>
        {groups.map((group) => (
          <div key={group.version} style={{ borderLeft: '2px solid var(--br-ink)', padding: '6px 0 14px 18px' }}>
            <Text strong>
              v{group.version} · {group.date}
            </Text>
            {group.items.map((item, index) => (
              <div key={index} style={{ marginTop: 4 }}>
                {item.content}
              </div>
            ))}
          </div>
        ))}
      </Flex>
      <Pagination
        current={page}
        pageSize={PAGE_SIZE}
        total={Math.min(flatEntries.length, MAX_ITEMS)}
        onChange={setPage}
        hideOnSinglePage
        showSizeChanger={false}
        style={{ textAlign: 'center', marginTop: 16 }}
      />
    </div>
  );
};
