import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { SoundOutlined } from '@ant-design/icons';
import axios from 'axios';
import { Select } from 'antd';
import { useEffect, useMemo, useState } from 'react';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

const DEFAULT_VOICE = 'zh-CN-XiaoxiaoNeural';

interface TtsVoice {
  id: string;
  name: string;
  locale: string;
  gender: string;
  style: string;
}

export const ReaderVoiceSettings: ReaderSettingsItem = {
  label: '语音',
  icon: <SoundOutlined />,
  component: () => {
    const voice = useSelector(Reader.select.voice);

    const [loading, setLoading] = useState<boolean>(true);
    const [ttsVoices, setTtsVoices] = useState<TtsVoice[]>([]);

    useEffect(() => {
      axios
        .get<{ voices: TtsVoice[] }>('/api/tts/voices')
        .then((res) => setTtsVoices(res.data.voices))
        .finally(() => setLoading(false));
    }, []);

    // 未选择过时默认晓晓（与后端 DEFAULT_VOICE 一致）
    const effectiveVoice = voice ?? DEFAULT_VOICE;

    const options = useMemo(
      () =>
        ttsVoices.map((item) => ({
          label: `${item.name}（${item.locale}·${item.gender}）`,
          value: item.id,
        })),
      [ttsVoices]
    );

    const updateVoice = (value: string) => {
      store.dispatch(Reader.action.setVoice(value));
    };

    // 归一化旧持久化值：1.1.7 及更早的系统语音名不在 9 音色白名单内，
    // 检测到后回退为默认晓晓，避免朗读请求携带非法音色。
    useEffect(() => {
      if (!ttsVoices.length) return;
      if (voice && !ttsVoices.some((v) => v.id === voice)) {
        store.dispatch(Reader.action.setVoice(undefined));
      }
    }, [ttsVoices, voice]);

    const selected = ttsVoices.find((v) => v.id === effectiveVoice);

    return (
      <Select
        virtual={false}
        loading={loading}
        disabled={!ttsVoices.length}
        variant="borderless"
        style={{ width: '100%' }}
        placeholder="选择语音"
        value={effectiveVoice}
        options={options}
        onSelect={updateVoice}
        title={
          ttsVoices.length
            ? selected
              ? `${selected.name}：${selected.style}`
              : undefined
            : '在线语音列表加载失败（需要联网）'
        }
      />
    );
  },
};