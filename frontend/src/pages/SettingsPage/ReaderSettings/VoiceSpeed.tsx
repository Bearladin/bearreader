import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { FastForwardOutlined } from '@ant-design/icons';
import { Flex, Slider, Tag } from 'antd';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

// Edge-TTS 音质推荐区间（SSML prosody rate ±50%）
const MIN_SPEED = 0.5;
const MAX_SPEED = 1.5;

export const ReaderVoiceSpeedSettings: ReaderSettingsItem = {
  label: '语速',
  icon: <FastForwardOutlined />,
  component: () => {
    const voiceSpeed = useSelector(Reader.select.voiceSpeed);

    const updateVoiceSpeed = (value: number) => {
      store.dispatch(Reader.action.setVoiceSpeed(value));
    };

    return (
      <Flex align="center">
        <Tag style={{ fontSize: 12, userSelect: 'none' }}>{voiceSpeed}</Tag>
        <Slider
          min={MIN_SPEED}
          max={MAX_SPEED}
          step={0.05}
          value={voiceSpeed}
          onChange={updateVoiceSpeed}
          style={{ flex: 1 }}
          marks={{ 0.5: '0.5x', 1: '1x', 1.5: '1.5x' }}
        />
      </Flex>
    );
  },
};