import { UserAvatar } from '@/components/Tags/UserAvatar';
import { UserRoleTag } from '@/components/Tags/UserRoleTag';
import { UserStatusTag } from '@/components/Tags/UserStatusTag';
import { UserTierTag } from '@/components/Tags/UserTierTag';
import { type User } from '@/types';
import { formatDate } from '@/utils/time';
import { CalendarOutlined } from '@ant-design/icons';
import { Card, Col, Flex, Grid, Row, Space, Typography } from 'antd';
import { Link } from 'react-router-dom';
import { UserStatusActions } from './UserStatusActions';

export const UserListItemCard: React.FC<{
  user: User;
  hideActions?: boolean;
  onChange?: () => any;
  onClick?: React.MouseEventHandler<HTMLDivElement>;
}> = ({ user, hideActions, onChange, onClick }) => {
  const { lg } = Grid.useBreakpoint();

  return (
    <Card
      onClick={onClick}
      hoverable={Boolean(onClick)}
      style={{ marginBottom: 5 }}
      styles={{
        body: { padding: lg ? undefined : 15 },
      }}
    >
      <Row align="middle" gutter={[25, 16]}>
        <Col flex="auto" style={{ width: '300px' }}>
          <Space size="middle" style={{ position: 'relative' }}>
            <UserAvatar size={48} user={user} />
            {user.name ? (
              <Flex vertical>
                <Typography.Text strong>
                  {hideActions ? (
                    user.name
                  ) : (
                    <Link to={`/admin/user/${user.id}`}>{user.name}</Link>
                  )}
                </Typography.Text>
                <Typography.Text
                  type={'secondary'}
                  style={{ whiteSpace: 'pre-wrap' }}
                >
                  {user.email}
                </Typography.Text>
              </Flex>
            ) : (
              <Flex vertical>
                <Typography.Text style={{ whiteSpace: 'pre-wrap' }}>
                  <Link to={`/admin/user/${user.id}`}>{user.email}</Link>
                </Typography.Text>
              </Flex>
            )}
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
        {!hideActions && (
          <Col
            flex="auto"
            style={{ width: '120px' }}
            onClick={(e) => e.preventDefault()}
          >
            <Flex
              wrap
              gap="10px"
              align="center"
              justify="end"
              style={{ minWidth: 100 }}
            >
              <UserStatusActions user={user} onChange={onChange} />
            </Flex>
          </Col>
        )}
      </Row>
    </Card>
  );
};
