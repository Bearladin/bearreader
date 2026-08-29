import { store } from '@/store';
import { Reader } from '@/store/_reader';
import {
  FontSizeOutlined,
  MinusOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { Button, Divider, Flex, Typography } from 'antd';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

export const ReaderFontSizeSettings: ReaderSettingsItem = {
  label: '字号',
  icon: <FontSizeOutlined />,
  component: () => {
    const fontSize = useSelector(Reader.select.fontSize);

    const updateFontSize = (value: number) => {
      store.dispatch(Reader.action.setFontSize(value));
    };

    return (
      <Flex align="center" justify="space-around">
        <Button
          type="text"
          size="small"
          shape="round"
          style={{ width: '100%' }}
          onClick={() => updateFontSize(fontSize - 1)}
        >
          <MinusOutlined />
        </Button>
        <Divider orientation="vertical" />
        <Typography.Text
          style={{
            width: '100%',
            fontWeight: 600,
            textAlign: 'center',
          }}
        >
          {fontSize}px
        </Typography.Text>
        <Divider orientation="vertical" />
        <Button
          type="text"
          size="small"
          shape="round"
          style={{ width: '100%' }}
          onClick={() => updateFontSize(fontSize + 1)}
        >
          <PlusOutlined />
        </Button>
      </Flex>
    );
  },
};
