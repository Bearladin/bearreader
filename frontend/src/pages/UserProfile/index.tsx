import { UserAvatar } from '@/components/Tags/UserAvatar';
import { UserTierTag } from '@/components/Tags/UserTierTag';
import { store } from '@/store';
import { Auth } from '@/store/_auth';
import { fetchCurrentUser } from '@/utils/setupAxios';
import { formatDate, formatFromNow } from '@/utils/time';
import {
  CalendarOutlined,
  CrownOutlined,
  LockOutlined,
  MailOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Descriptions, Divider, Grid, Space, Typography } from 'antd';
import { useCallback, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { ProfileNameChangeButton } from './ProfileNameChangeButton';
import { ProfilePasswordChangeButton } from './ProfilePasswordChangeButton';

export const UserProfilePage: React.FC<any> = () => {
  const { xs } = Grid.useBreakpoint();
  const user = useSelector(Auth.select.user)!;

  const updateUser = useCallback(async () => {
    const currentUser = await fetchCurrentUser(user.id);
    store.dispatch(Auth.action.setUser(currentUser));
  }, [user.id]);

  useEffect(() => {
    updateUser();
  }, [updateUser]);

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Typography.Title level={2}>
        <UserOutlined /> 个人资料
      </Typography.Title>

      <Descriptions
        bordered
        column={1}
        size="middle"
        layout={xs ? 'vertical' : 'horizontal'}
        styles={{ label: { width: 150, fontWeight: 500 } }}
      >
        <Descriptions.Item
          label={
            <Space>
              <UserOutlined /> 姓名
            </Space>
          }
        >
          <Space>
            <UserAvatar user={user} size={32} />
            <Typography.Text>{user.name}</Typography.Text>
            <Divider orientation="vertical" />
            <ProfileNameChangeButton user={user} onChange={updateUser} />
          </Space>
        </Descriptions.Item>

        <Descriptions.Item
          label={
            <Space>
              <MailOutlined /> 邮箱
            </Space>
          }
        >
          <Typography.Text copyable>{user.email}</Typography.Text>
        </Descriptions.Item>

        <Descriptions.Item
          label={
            <Space>
              <CrownOutlined /> 用户等级
            </Space>
          }
        >
          <UserTierTag value={user.tier} />
        </Descriptions.Item>

        <Descriptions.Item
          label={
            <Space>
              <LockOutlined /> 密码
            </Space>
          }
        >
          <ProfilePasswordChangeButton />
        </Descriptions.Item>

        <Descriptions.Item
          label={
            <Space>
              <CalendarOutlined /> 加入时间
            </Space>
          }
        >
          <Typography.Text>{formatDate(user.created_at)}</Typography.Text>
          <Divider orientation="vertical" />
          <Typography.Text type="secondary">
            {formatFromNow(user.created_at)}
          </Typography.Text>
        </Descriptions.Item>
      </Descriptions>
    </div>
  );
};
