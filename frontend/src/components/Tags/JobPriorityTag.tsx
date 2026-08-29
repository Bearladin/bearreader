import { JobPriority } from '@/types';
import { ThunderboltOutlined } from '@ant-design/icons';
import { Tag } from 'antd';

export const JobPriorityTag: React.FC<{ value: JobPriority }> = ({ value }) => {
  switch (value) {
    case JobPriority.LOW:
      return <Tag icon={<ThunderboltOutlined />}>低优先级</Tag>;
    case JobPriority.NORMAL:
      return (
        <Tag icon={<ThunderboltOutlined />} color="gold">
          普通优先级
        </Tag>
      );
    case JobPriority.HIGH:
      return (
        <Tag icon={<ThunderboltOutlined />} color="volcano">
          <b>高优先级</b>
        </Tag>
      );
    default:
      return <Tag>{String(value)}</Tag>;
  }
};
