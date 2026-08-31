import { CopyOutlined } from '@ant-design/icons';
import { Typography } from 'antd';
import type { ReaderSettingsItem } from './types';

// 只读键位速查：与 CHANGELOG 的完整键位说明保持一致
const SHORTCUTS: Array<[string, string]> = [
  ['← / →', '切换章节'],
  ['空格', '向下滚动一屏'],
  ['S', '开始 / 停止朗读'],
  ['+ / −', '调整字号'],
  ['媒体键', '播放 / 暂停朗读'],
];

export const ReaderShortcutsSettings: ReaderSettingsItem = {
  label: '快捷键',
  icon: <CopyOutlined />,
  component: () => (
    <div style={{ padding: '4px 0' }}>
      {SHORTCUTS.map(([key, desc]) => (
        <Typography.Text key={key} style={{ display: 'block', fontSize: 13 }}>
          <Typography.Text
            keyboard
            style={{ fontSize: 12, minWidth: 64, display: 'inline-block' }}
          >
            {key}
          </Typography.Text>
          <span style={{ marginLeft: 8 }}>{desc}</span>
        </Typography.Text>
      ))}
    </div>
  ),
};
