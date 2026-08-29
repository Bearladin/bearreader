import { enumLabels } from '@/locales/zh-CN';
import { FeedbackType } from '@/types/enums';
import { BugOutlined, CommentOutlined, StarOutlined } from '@ant-design/icons';
import { Tag } from 'antd';

export const FeedbackTypeTag: React.FC<{ value: FeedbackType }> = ({
  value,
}) => {
  switch (value) {
    case FeedbackType.GENERAL:
      return (
        <Tag icon={<CommentOutlined />} color="purple">
          {enumLabels.feedbackType[value]}
        </Tag>
      );
    case FeedbackType.ISSUE:
      return (
        <Tag icon={<BugOutlined />} color="red">
          {enumLabels.feedbackType[value]}
        </Tag>
      );
    case FeedbackType.FEATURE:
      return (
        <Tag icon={<StarOutlined />} color="orange">
          {enumLabels.feedbackType[value]}
        </Tag>
      );
    default:
      return <Tag>{String(value)}</Tag>;
  }
};
