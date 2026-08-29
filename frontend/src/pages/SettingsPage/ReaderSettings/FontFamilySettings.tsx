import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { FontFamily } from '@/types';
import { FontColorsOutlined } from '@ant-design/icons';
import { Select } from 'antd';
import { useSelector } from 'react-redux';
import type { ReaderSettingsItem } from './types';

const fontFamilyOptions: Array<{ label: string; value: FontFamily }> = [
  { label: '微软雅黑', value: FontFamily.MicrosoftYaHei },
  { label: '小熊楷体', value: FontFamily.XiaoXiongKai },
  { label: '小熊宋体', value: FontFamily.XiaoXiongSerif },
];

export const ReaderFontFamilySettings: ReaderSettingsItem = {
  label: '字体',
  icon: <FontColorsOutlined />,
  component: () => {
    const fontFamily = useSelector(Reader.select.fontFamily);

    const updateFontFamily = (value: FontFamily) => {
      store.dispatch(Reader.action.setFontFamily(value));
    };

    const options = fontFamilyOptions.map(({ label, value }) => ({
      value,
      label: <span style={{ fontFamily: value }}>{label}</span>,
    }));

    return (
      <Select
        virtual={false}
        placeholder="选择字体"
        variant="borderless"
        style={{ width: '100%' }}
        options={options}
        value={fontFamily}
        onSelect={updateFontFamily}
      />
    );
  },
};
