import { UserAvatar } from '@/components/Tags/UserAvatar';
import { UserRoleTag } from '@/components/Tags/UserRoleTag';
import { UserStatusTag } from '@/components/Tags/UserStatusTag';
import { UserTierTag } from '@/components/Tags/UserTierTag';
import { Auth } from '@/store/_auth';
import type { Paginated, User } from '@/types';
import { formatDate, formatFromNow } from '@/utils/time';
import {
  CalendarOutlined,
  CrownOutlined,
  IdcardOutlined,
  MailOutlined,
  NodeIndexOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Descriptions, Divider, Grid, Space, Tag, Typography } from 'antd';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { Link } from 'react-router-dom';
import { UserStatusActions } from '../UserList/UserStatusActions';

export const UserDetailSection: React.FC<{
  user: User;
  onChange: () => any;
}> = ({ user, onChange }) => {
  const { xs } = Grid.useBreakpoint();
  const currentUser = useSelector(Auth.select.user);

  const [isVerified, setIsVerified] = useState<boolean>();
  const [referenceCount, setReferenceCount] = useState<number>(0);

  useEffect(() => {
    const fetchVerified = async () => {
      try {
        const { data } = await axios.get<boolean>(
          `/api/user/${user.id}/verified`
        );
        setIsVerified(data);
      } catch {
        setIsVerified(undefined);
      }
    };
    fetchVerified();
  }, [user.id]);

  useEffect(() => {
    const fetchReferenceCount = async () => {
      try {
        const { data } = await axios.get<Paginated<User>>(`/api/users`, {
          params: {
            limit: 0,
            referrer: user.id,
          },
        });
        setReferenceCount(data.total);
      } catch {
        setReferenceCount(0);
      }
    };
    fetchReferenceCount();
  }, [user.id]);

  return (
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
            <IdcardOutlined /> 角色
          </Space>
        }
      >
        <UserRoleTag value={user.role} />
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
            <SafetyCertificateOutlined /> 已验证
          </Space>
        }
      >
        <Tag color={isVerified ? 'success' : 'error'}>
          {isVerified ? '是' : '否'}
        </Tag>
      </Descriptions.Item>

      <Descriptions.Item
        label={
          <Space>
            <UserOutlined /> 状态
          </Space>
        }
      >
        <UserStatusTag value={user.is_active} />
        {user.id !== currentUser?.id && (
          <>
            <Divider orientation="vertical" />
            <UserStatusActions user={user} onChange={onChange} />
          </>
        )}
      </Descriptions.Item>

      <Descriptions.Item
        label={
          <Space>
            <NodeIndexOutlined /> 受邀用户
          </Space>
        }
      >
        <Typography.Text>共 {referenceCount} 位用户</Typography.Text>
        {referenceCount > 0 && (
          <>
            <Divider orientation="vertical" />
            <Link to={`/admin/users?referrer=${user.id}`}>查看受邀用户</Link>
          </>
        )}
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

      <Descriptions.Item
        label={
          <Space>
            <CalendarOutlined /> 最后更新
          </Space>
        }
      >
        <Typography.Text>{formatDate(user.updated_at)}</Typography.Text>
        <Divider orientation="vertical" />
        <Typography.Text type="secondary">
          {formatFromNow(user.updated_at)}
        </Typography.Text>
      </Descriptions.Item>
    </Descriptions>
  );
};
