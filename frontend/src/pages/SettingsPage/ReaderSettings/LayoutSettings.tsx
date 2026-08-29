import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { ReaderLayout } from '@/types';
import {
  ColumnHeightOutlined,
  LayoutOutlined,
  SplitCellsOutlined,
} from '@ant-design/icons';
import { Button, Flex } from 'antd';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

export const ReaderLayoutSettings: ReaderSettingsItem = {
  label: '布局',
  icon: <LayoutOutlined />,
  component: () => {
    const layout = useSelector(Reader.select.layout);

    const updateLayout = (value: ReaderLayout) => {
      store.dispatch(Reader.action.setLayout(value));
    };

    return (
      <Flex align="center" justify="space-around">
        <Button
          size="large"
          style={{ width: '100%', borderRadius: 0 }}
          onClick={() => updateLayout(ReaderLayout.horizontal)}
          type={layout === ReaderLayout.horizontal ? 'primary' : 'default'}
          title="横向布局"
          aria-label="横向布局"
        >
          <SplitCellsOutlined style={{ fontSize: 24 }} />
        </Button>
        <Button
          size="large"
          style={{ width: '100%', borderRadius: 0 }}
          onClick={() => updateLayout(ReaderLayout.vertical)}
          type={layout === ReaderLayout.vertical ? 'primary' : 'default'}
          title="纵向布局"
          aria-label="纵向布局"
        >
          <ColumnHeightOutlined style={{ fontSize: 24 }} />
        </Button>
      </Flex>
    );
  },
};
