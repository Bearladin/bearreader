import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { PauseCircleOutlined } from '@ant-design/icons';
import { Select } from 'antd';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

const PAUSE_OPTIONS = [
  { value: 0, label: '无停顿' },
  { value: 200, label: '200ms' },
  { value: 300, label: '300ms' },
  { value: 500, label: '500ms' },
];

export const ReaderVoicePauseSettings: ReaderSettingsItem = {
  label: '句间停顿',
  icon: <PauseCircleOutlined />,
  component: () => {
    const voicePause = useSelector(Reader.select.voicePause);

    const updatePause = (value: number) => {
      store.dispatch(Reader.action.setVoicePause(value));
    };

    return (
      <Select
        variant="borderless"
        style={{ width: 140 }}
        value={voicePause}
        options={PAUSE_OPTIONS}
        onSelect={updatePause}
      />
    );
  },
};