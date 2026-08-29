import { ErrorState } from '@/components/Loading/ErrorState';
import { LoadingState } from '@/components/Loading/LoadingState';
import type { User } from '@/types';
import { stringifyError } from '@/utils/errors';
import { DeploymentUnitOutlined, UserOutlined } from '@ant-design/icons';
import { Divider, Typography } from 'antd';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { JobListPage } from '../JobList';
import { ReferrerCard } from './ReferrerCard';
import { UserDetailsActions } from './UserDetailsActions';
import { UserDetailSection } from './UserDetailSection';

export const UserDetailsPage: React.FC<any> = () => {
  const { id } = useParams<{ id: string }>();

  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<User>();
  const [error, setError] = useState<string>();
  const [refreshId, setRefreshId] = useState(0);

  useEffect(() => {
    const fetchUser = async () => {
      setError(undefined);
      try {
        const { data } = await axios.get<User>(`/api/user/${id}`);
        setUser(data);
      } catch (err: any) {
        setError(stringifyError(err));
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, [id, refreshId]);

  if (loading) {
    return <LoadingState />;
  }

  if (error || !user) {
    return (
      <ErrorState
        error={error}
        title="用户详情加载失败"
        onRetry={() => {
          setLoading(true);
          setRefreshId((v) => v + 1);
        }}
      />
    );
  }

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Typography.Title level={2}>
        <UserOutlined /> 用户详情
      </Typography.Title>

      <UserDetailSection
        user={user}
        onChange={() => setRefreshId((v) => v + 1)}
      />
      <UserDetailsActions
        user={user}
        onChange={() => setRefreshId((v) => v + 1)}
      />

      <Divider size="large" />

      <ReferrerCard referrerId={user.referrer_id} />

      <JobListPage
        userId={id}
        autoRefresh
        title={
          <Typography.Title level={3}>
            <DeploymentUnitOutlined /> 用户的任务请求
          </Typography.Title>
        }
      />
    </div>
  );
};
