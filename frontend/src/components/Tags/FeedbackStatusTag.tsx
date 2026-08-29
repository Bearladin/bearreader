import { enumLabels } from '@/locales/zh-CN';
import { FeedbackStatus } from '@/types/enums';
import { Tag } from 'antd';

export const FeedbackStatusTag: React.FC<{ status: FeedbackStatus }> = ({
  status,
}) => {
  switch (status) {
    case FeedbackStatus.PENDING:
      return <Tag color="default">{enumLabels.feedbackStatus[status]}</Tag>;
    case FeedbackStatus.ACCEPTED:
      return <Tag color="cyan">{enumLabels.feedbackStatus[status]}</Tag>;
    case FeedbackStatus.RESOLVED:
      return <Tag color="green">{enumLabels.feedbackStatus[status]}</Tag>;
    default:
      return <Tag>{String(status)}</Tag>;
  }
};
