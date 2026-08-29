import { Divider, Flex, Typography } from 'antd';
import { JobListPage } from '../JobList';
import { RequestNovelCard } from './RequestNovelCard';

// 单用户本地应用：只保留「全部任务请求」，不再区分我的/全部。
export const HomePage: React.FC<any> = () => {
  return (
    <div className="br-page-container">
      <RequestNovelCard />

      <Divider style={{ margin: '32px 0 24px' }} />
      <Flex align="end" justify="space-between" style={{ marginBottom: 18 }}>
        <div>
          <Typography.Text className="br-section-label">任务动态</Typography.Text>
          <Typography.Title className="br-page-title" level={3}>任务记录</Typography.Title>
        </div>
      </Flex>

      <JobListPage key="all" autoRefresh />
    </div>
  );
};
