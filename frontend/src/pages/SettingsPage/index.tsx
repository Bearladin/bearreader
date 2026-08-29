import { ReaderSettings } from '@/pages/SettingsPage/ReaderSettings';
import { SettingOutlined } from '@ant-design/icons';
import { Collapse, Typography, type CollapseProps } from 'antd';
import { NotificationSettings } from './NotificationSettings';

const items: CollapseProps['items'] = [
  {
    key: 'notifications',
    label: '通知设置',
    children: <NotificationSettings />,
  },
  {
    key: 'reader',
    label: '阅读设置',
    children: <ReaderSettings />,
  },
];

const allKeys = items.map((x) => String(x.key)).filter(Boolean);

export const SettingsPage: React.FC<any> = () => {
  return (
    <>
      <Typography.Title level={2}>
        <SettingOutlined /> 设置
      </Typography.Title>

      <Collapse defaultActiveKey={allKeys} items={items} />
    </>
  );
};
