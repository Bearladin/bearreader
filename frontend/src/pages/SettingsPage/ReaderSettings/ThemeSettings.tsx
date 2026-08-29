import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { ReaderTheme } from '@/types';
import { BgColorsOutlined, CheckOutlined } from '@ant-design/icons';
import { Avatar, Flex, Popover } from 'antd';
import { isEqual } from 'lodash';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

const themeOptions = [
  { label: '深色', value: ReaderTheme.Dark },
  { label: '纯黑', value: ReaderTheme.Black },
  { label: '纯白', value: ReaderTheme.White },
  { label: '纸张', value: ReaderTheme.Paper },
  { label: '棕褐', value: ReaderTheme.Sepia },
  { label: '咖啡', value: ReaderTheme.Coffee },
  { label: '羊皮纸', value: ReaderTheme.Parchment },
];

export const ReaderThemeSettings: ReaderSettingsItem = {
  label: '主题',
  icon: <BgColorsOutlined />,
  component: () => {
    const theme = useSelector(Reader.select.theme);

    const updateTheme = (value: ReaderTheme) => {
      store.dispatch(Reader.action.setTheme(value));
    };

    return (
      <Flex wrap gap={10}>
        {themeOptions.map(({ label, value }) => (
          <Popover key={label} content={label}>
            <Avatar
              style={{
                ...value,
                cursor: 'pointer',
                border: `2px solid ${value.color}`,
              }}
              onClick={() => updateTheme(value)}
              icon={isEqual(theme, value) && <CheckOutlined />}
              aria-label={label}
            />
          </Popover>
        ))}
      </Flex>
    );
  },
};
