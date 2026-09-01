import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { Switch } from 'antd';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

export const ReaderConfirmOnCloseSettings: ReaderSettingsItem = {
  label: '关闭时确认',
  icon: <QuestionCircleOutlined />,
  component: () => {
    const confirmOnClose = useSelector(Reader.select.confirmOnClose);

    const updateConfirmOnClose = (value: boolean) => {
      store.dispatch(Reader.action.setConfirmOnClose(value));
    };

    return <Switch value={confirmOnClose} onChange={updateConfirmOnClose} />;
  },
};
