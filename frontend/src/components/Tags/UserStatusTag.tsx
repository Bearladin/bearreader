import { Tag } from 'antd';

export const UserStatusTag: React.FC<{ value?: boolean }> = ({ value }) => {
  return (
    <Tag color={value ? 'green' : 'cyan'}>{value ? '启用' : '停用'}</Tag>
  );
};
