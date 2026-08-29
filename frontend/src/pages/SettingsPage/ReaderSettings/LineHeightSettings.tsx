import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { LineHeightOutlined } from '@ant-design/icons';
import { Flex, Slider, Tag } from 'antd';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

export const ReaderLineHeightSettings: ReaderSettingsItem = {
  label: '行高',
  icon: <LineHeightOutlined />,
  component: () => {
    const lineHeight = useSelector(Reader.select.lineHeight);

    const updateLineHeight = (value: number) => {
      store.dispatch(Reader.action.setLineHeight(value));
    };

    return (
      <Flex align="center">
        <Tag style={{ fontSize: 12, userSelect: 'none' }}>{lineHeight}</Tag>
        <Slider
          min={0.5}
          max={2.5}
          step={0.05}
          value={lineHeight}
          onChange={updateLineHeight}
          style={{ flex: 1 }}
        />
      </Flex>
    );
  },
};
