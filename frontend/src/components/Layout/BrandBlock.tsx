import { APP_NAME } from '@/config';
import { APP_VERSION } from '@/version';
import { Flex, Typography } from 'antd';

export const BrandBlock: React.FC<{ compact?: boolean }> = ({ compact }) => (
  <Flex
    align="center"
    gap={12}
    style={{
      minHeight: compact ? 56 : 92,
      padding: compact ? '8px 12px' : '20px 18px',
      borderBottom: '1px solid var(--br-border)',
      background: 'var(--br-surface)',
    }}
  >
    <img
      src={compact ? '/icons/bear-32.png' : '/icons/bear-64.png'}
      width={compact ? 32 : 40}
      height={compact ? 32 : 40}
      alt="BearReader"
      draggable={false}
      style={{ flex: 'none', display: 'block' }}
    />
    <div style={{ minWidth: 0 }}>
      <Typography.Title
        level={4}
        className="br-serif"
        style={{ margin: 0, fontSize: compact ? 17 : 20, lineHeight: 1.25 }}
      >
        {APP_NAME}
      </Typography.Title>
      <Typography.Text
        type="secondary"
        style={{ display: 'block', marginTop: 3, fontSize: compact ? 11 : 12 }}
      >
        {compact ? `v${APP_VERSION} · 本地运行` : '中文小说下载 · 阅读 · 导出'}
      </Typography.Text>
    </div>
  </Flex>
);
