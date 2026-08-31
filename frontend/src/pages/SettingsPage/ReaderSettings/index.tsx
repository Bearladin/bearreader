import type { ReaderSettingsItem } from './types';

import { Descriptions, Flex, Grid } from 'antd';
import { ReaderAutoFetchSetting } from './AutoFetchSetting';
import { ReaderAutoScrollSpeedSettings } from './AutoScrollSpeedSettings';
import { ReaderFontFamilySettings } from './FontFamilySettings';
import { ReaderFontSizeSettings } from './FontSizeSettings';
import { ReaderLineHeightSettings } from './LineHeightSettings';
import { ReaderShortcutsSettings } from './ShortcutsSettings';
import { ReaderTextAlignSettings } from './TextAlignSettings';
import { ReaderThemeSettings } from './ThemeSettings';
import { ReaderVoicePauseSettings } from './VoicePause';
import { ReaderVoiceSettings } from './VoiceSettings';
import { ReaderVoiceSpeedSettings } from './VoiceSpeed';

const items: ReaderSettingsItem[] = [
  // ReaderLayoutSettings,
  ReaderThemeSettings,
  ReaderFontFamilySettings,
  ReaderFontSizeSettings,
  ReaderLineHeightSettings,
  ReaderTextAlignSettings,
  ReaderVoiceSettings,
  ReaderVoicePauseSettings,
  ReaderAutoScrollSpeedSettings,
  ReaderVoiceSpeedSettings,
  ReaderShortcutsSettings,
  ReaderAutoFetchSetting,
];

export const ReaderSettings = () => {
  const { sm } = Grid.useBreakpoint();
  return (
    <Descriptions
      bordered
      column={1}
      size="small"
      layout={sm ? 'horizontal' : 'vertical'}
      items={items.map((item) => ({
        label: (
          <Flex align="center" gap="6px">
            {item.icon} {item.label}
          </Flex>
        ),
        children: <item.component />,
      }))}
    />
  );
};
