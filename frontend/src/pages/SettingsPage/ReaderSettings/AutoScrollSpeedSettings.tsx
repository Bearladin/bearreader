import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { DownOutlined } from '@ant-design/icons';
import { Flex, Slider, Tag } from 'antd';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

// 自动滚动速度范围（像素/秒）
const MIN_SPEED = 10;
const MAX_SPEED = 300;

export const ReaderAutoScrollSpeedSettings: ReaderSettingsItem = {
  label: '自动滚动速度',
  icon: <DownOutlined />,
  component: () => {
    const autoScrollSpeed = useSelector(Reader.select.autoScrollSpeed);

    const updateAutoScrollSpeed = (value: number) => {
      store.dispatch(Reader.action.setAutoScrollSpeed(value));
    };

    return (
      <Flex align="center">
        <Tag style={{ fontSize: 12, userSelect: 'none' }}>
          {autoScrollSpeed} px/s
        </Tag>
        <Slider
          min={MIN_SPEED}
          max={MAX_SPEED}
          step={10}
          value={autoScrollSpeed}
          onChange={updateAutoScrollSpeed}
          style={{ flex: 1 }}
          marks={{ 10: '10', 150: '150', 300: '300' }}
        />
      </Flex>
    );
  },
};
