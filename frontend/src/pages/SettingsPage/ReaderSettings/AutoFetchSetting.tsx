import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { DownloadOutlined } from '@ant-design/icons';
import { Switch } from 'antd';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

export const ReaderAutoFetchSetting: ReaderSettingsItem = {
  label: '自动获取',
  icon: <DownloadOutlined />,
  component: () => {
    const autoFetch = useSelector(Reader.select.autoFetch);

    const updateAutoFetch = (value: boolean) => {
      store.dispatch(Reader.action.setAutoFetch(value));
    };

    return <Switch value={autoFetch} onChange={updateAutoFetch} />;
  },
};
