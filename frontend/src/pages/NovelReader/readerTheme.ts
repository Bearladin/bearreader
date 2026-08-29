import type { ReaderTheme } from '@/types';
import type { ThemeConfig } from 'antd';

/** Theme tokens for reader-owned overlays without changing the seven base themes. */
export const getReaderOverlayTheme = (readerTheme: ReaderTheme): ThemeConfig => ({
  token: {
    colorPrimary: readerTheme.color,
    colorInfo: readerTheme.color,
    colorText: readerTheme.color,
    colorTextSecondary: `${readerTheme.color}a6`,
    colorTextTertiary: `${readerTheme.color}73`,
    colorBgBase: readerTheme.background,
    colorBgContainer: readerTheme.background,
    colorBgElevated: readerTheme.background,
    colorFillSecondary: `${readerTheme.color}14`,
    colorFillTertiary: `${readerTheme.color}0d`,
    colorBorder: `${readerTheme.color}66`,
    colorBorderSecondary: `${readerTheme.color}33`,
    colorTextPlaceholder: `${readerTheme.color}80`,
    borderRadius: 2,
    borderRadiusLG: 4,
    controlOutline: readerTheme.color,
    boxShadowSecondary: '0 8px 24px rgba(0, 0, 0, 0.24)',
  },
  components: {
    Modal: {
      contentBg: readerTheme.background,
      headerBg: readerTheme.background,
    },
    Drawer: { colorBgElevated: readerTheme.background },
    Descriptions: {
      labelBg: `${readerTheme.color}0d`,
    },
    Select: {
      selectorBg: readerTheme.background,
      optionSelectedBg: `${readerTheme.color}1f`,
      optionActiveBg: `${readerTheme.color}14`,
    },
    Input: { colorBgContainer: readerTheme.background },
    InputNumber: { colorBgContainer: readerTheme.background },
    Pagination: {
      itemBg: readerTheme.background,
      itemActiveBg: readerTheme.color,
    },
    Switch: {
      colorPrimary: readerTheme.color,
      colorPrimaryHover: readerTheme.color,
    },
  },
});
