import { enumLabels } from '@/locales/zh-CN';
import { UserRole } from '@/types';
import { Tag } from 'antd';

export const UserRoleTag: React.FC<{ value?: UserRole }> = ({ value }) => {
  if (!value) return null;
  return (
    <Tag color={value === UserRole.ADMIN ? 'red' : 'blue'}>
      {enumLabels.userRole[value] ?? value}
    </Tag>
  );
};
