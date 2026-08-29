import { UserAvatar } from '@/components/Tags/UserAvatar';
import { UserRoleTag } from '@/components/Tags/UserRoleTag';
import { UserStatusTag } from '@/components/Tags/UserStatusTag';
import { UserTierTag } from '@/components/Tags/UserTierTag';
import { type User } from '@/types';
import { formatDate } from '@/utils/time';
import { CalendarOutlined } from '@ant-design/icons';
import { Card, Col, Flex, Row, Space, Typography } from 'antd';
import { Link } from 'react-router-dom';

export const UserDetailsCard: React.FC<{
  user: User;
  title?: string;
}> = ({ user, title }) => {
  return (
    <Card variant="outlined">
      <Typography.Title level={4} style={{ margin: 0, marginBottom: 16 }}>
        {title ?? '用户'}
      </Typography.Title>

      <Row align="middle" gutter={[16, 16]}>
        <Col flex="auto">
          <Space size="middle">
            <UserAvatar size={56} user={user} />
            <Flex vertical>
              <Typography.Title level={5} style={{ margin: 0 }}>
                <Link to={`/admin/user/${user.id}`}>
                  {user.name || '未知用户'}
                </Link>
              </Typography.Title>
              <Typography.Text type="secondary">{user.email}</Typography.Text>
            </Flex>
          </Space>
        </Col>

        <Col flex="auto">
          <Flex wrap gap="10px" justify="space-between">
            <Flex wrap vertical gap="10px">
              <Flex gap="10px">
                <Typography.Text
                  strong
                  style={{ width: 70, textAlign: 'right' }}
                >
                  角色：
                </Typography.Text>
                <UserRoleTag value={user.role} />
              </Flex>
              <Flex gap="10px">
                <Typography.Text
                  strong
                  style={{ width: 70, textAlign: 'right' }}
                >
                  状态：
                </Typography.Text>
                <UserStatusTag value={user.is_active} />
              </Flex>
            </Flex>
            <Flex wrap vertical gap="10px">
              <Flex gap="10px">
                <Typography.Text
                  strong
                  style={{ width: 70, textAlign: 'right' }}
                >
                  等级：
                </Typography.Text>
                <UserTierTag value={user.tier} />
              </Flex>
              <Flex gap="10px">
                <Typography.Text
                  strong
                  style={{ width: 70, textAlign: 'right' }}
                >
                  加入时间：
                </Typography.Text>
                <Typography.Text>
                  <CalendarOutlined /> {formatDate(user.created_at)}
                </Typography.Text>
              </Flex>
            </Flex>
          </Flex>
        </Col>
      </Row>
    </Card>
  );
};
