import { UserTier } from '@/types';
import { CrownFilled, SmileOutlined, StarFilled } from '@ant-design/icons';
import { Tag } from 'antd';

export const UserTierTag: React.FC<{ value?: UserTier }> = ({ value }) => {
  switch (value) {
    case UserTier.BASIC:
      return <Tag icon={<SmileOutlined />}>基础版</Tag>;
    case UserTier.PREMIUM:
      return (
        <Tag color="gold" icon={<StarFilled />}>
          高级版
        </Tag>
      );
    case UserTier.VIP:
      return (
        <Tag variant="solid" color="volcano" icon={<CrownFilled />}>
          VIP
        </Tag>
      );
    default:
      return value == null ? null : <Tag>{String(value)}</Tag>;
  }
};
