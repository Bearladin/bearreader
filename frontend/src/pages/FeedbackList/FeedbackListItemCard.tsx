import { FeedbackStatusTag } from '@/components/Tags/FeedbackStatusTag';
import { FeedbackTypeTag } from '@/components/Tags/FeedbackTypeTag';
import { type Feedback } from '@/types';
import { formatFromNow } from '@/utils/time';
import {
  CalendarOutlined,
  ClockCircleOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Card, Divider, Flex, Grid, Space, Typography } from 'antd';
import { getFeedbackStatusColor, getFeedbackTypeColor } from './utils';

export const FeedbackListItemCard: React.FC<{
  feedback: Feedback;
  onClick: React.MouseEventHandler<HTMLDivElement>;
}> = ({ feedback, onClick }) => {
  const { lg } = Grid.useBreakpoint();
  return (
    <Card
      hoverable
      onClick={onClick}
      style={{
        cursor: 'pointer',
        marginBottom: 8,
        borderRadius: 2,
        overflow: 'hidden',
        borderLeft: `4px solid ${getFeedbackTypeColor(feedback.type)}`,
        borderRight: `4px solid ${getFeedbackStatusColor(feedback.status)}`,
      }}
      styles={{
        body: {
          padding: lg ? '10px 20px' : '10px 15px',
        },
      }}
    >
      <Flex justify="space-between" align="center" wrap gap="small">
        <Typography.Title
          level={4}
          ellipsis
          style={{
            flex: 1,
            margin: 0,
            textTransform: 'capitalize',
          }}
        >
          {feedback.subject}
        </Typography.Title>
        <Flex gap="small">
          <FeedbackTypeTag value={feedback.type} />
          <FeedbackStatusTag status={feedback.status} />
        </Flex>
      </Flex>

      <Typography.Paragraph
        ellipsis={{ rows: 2 }}
        style={{
          margin: 0,
          color: 'var(--br-secondary)',
          whiteSpace: 'pre-wrap',
        }}
      >
        {feedback.message}
      </Typography.Paragraph>

      <Space
        wrap
        size={0}
        style={{ marginTop: 4 }}
        separator={<Divider orientation="vertical" />}
      >
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          <UserOutlined /> {feedback.extra?.user_name || '未知用户'}
        </Typography.Text>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          <CalendarOutlined /> {formatFromNow(feedback.created_at)}
        </Typography.Text>
        {feedback.updated_at !== feedback.created_at && (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            <ClockCircleOutlined /> {formatFromNow(feedback.updated_at)}
          </Typography.Text>
        )}
      </Space>
    </Card>
  );
};
