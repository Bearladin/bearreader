import { enumLabels } from '@/locales/zh-CN';
import { FeedbackStatus, FeedbackType } from '@/types';
import type { TagProps } from 'antd';

export const FeedbackStatusLabels = enumLabels.feedbackStatus;

export const FeedbackTypeLabels = enumLabels.feedbackType;

export const getFeedbackTypeColor = (type: FeedbackType): TagProps['color'] => {
  switch (type) {
    case FeedbackType.GENERAL:
      return 'purple';
    case FeedbackType.ISSUE:
      return 'red';
    case FeedbackType.FEATURE:
      return 'orange';
  }
};

export const getFeedbackStatusColor = (
  status: FeedbackStatus
): TagProps['color'] => {
  switch (status) {
    case FeedbackStatus.PENDING:
      return 'gray';
    case FeedbackStatus.ACCEPTED:
      return 'cyan';
    case FeedbackStatus.RESOLVED:
      return 'green';
  }
};
