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
    version: '1.3.1',
    date: '2026-08-31',
    items: [
      <span key="keyboard-shortcuts">
        阅读器新增键盘快捷键：方向键切换章节（朗读中切换段落）、空格滚动一屏、S 开关朗读、+/− 调整字号，系统媒体键也可控制朗读；设置面板内新增快捷键速查。
      </span>,
      <span key="continuous-tts">
        朗读支持跨章连读：读到章尾或手动切章时，自动从新章开头继续朗读。
      </span>,
      <span key="reading-resume">
        阅读位置记忆：每本书记住最后读到的滚动位置，「继续阅读」直达原位置。
      </span>,
      <span key="auto-scroll">
        新增自动滚动：可调速度匀速滚动，手动滚动即停；朗读时视图平滑跟随正在朗读的段落。
      </span>,
      <span key="catalog-sorting">
        全库新增排序方式，书架内新增搜索与五种排序（更新、收录、章节数、书名）。
      </span>,
      <span key="cancel-whole-request">
        取消多步任务（如获取全书）的任意一步，现在会取消整个请求，不再遗留其余分卷继续执行。
      </span>,
      <span key="chapter-header">
        章节页头只保留标题：朗读不再读出章节序号与更新时间，阅读更沉浸。
      </span>,
      <span key="interaction-fixes">
        修复键盘与工具栏交互干扰、书架搜索计数、列表快速切换时的结果竞态等多项问题；批量任务标题现在显示书名。
      </span>,
    ],
  },
  {
    version: '1.3.0',
    date: '2026-08-29',
    items: [
      <span key="first-public-release">
        首个公开发布版本：前端源码与应用同仓管理，嵌入构建由构建清单校验，每个发行标签都可从源码完整重建。
      </span>,
      <span key="system-fonts">
        界面使用系统字体（微软雅黑 / 苹方 / 思源黑体），阅读器保留内置「小熊楷体」「小熊宋体」；不再附带不可再分发的字体文件。
      </span>,
      <span key="portable-default">
        默认发行物为 Windows 绿色 ZIP：同一发行标签同时提供完整源码归档、许可证与哈希校验清单。
      </span>,
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
