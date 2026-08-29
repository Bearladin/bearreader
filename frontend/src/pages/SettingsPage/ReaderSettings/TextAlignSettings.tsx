import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { TextAlign } from '@/types';
import { AlignLeftOutlined } from '@ant-design/icons';
import { Flex, Select, Tag } from 'antd';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

const textAlignOptions = [
  { label: '左对齐', value: TextAlign.left },
  { label: '居中对齐', value: TextAlign.center },
  { label: '右对齐', value: TextAlign.right },
  { label: '两端对齐', value: TextAlign.justify },
];

export const ReaderTextAlignSettings: ReaderSettingsItem = {
  label: '文本对齐',
  icon: <AlignLeftOutlined />,
  component: () => {
    const textAlign = useSelector(Reader.select.textAlign);

    const updateTextAlign = (value: TextAlign) => {
      store.dispatch(Reader.action.setTextAlign(value));
    };

    return (
      <Flex align="center">
        <Tag style={{ fontSize: 12, userSelect: 'none' }}>对齐</Tag>
        <Select
          value={textAlign}
          onChange={updateTextAlign}
          style={{ flex: 1 }}
          options={textAlignOptions}
        />
      </Flex>
    );
  },
};
