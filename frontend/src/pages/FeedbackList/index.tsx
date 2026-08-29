import { ErrorState } from '@/components/Loading/ErrorState';
import { LoadingState } from '@/components/Loading/LoadingState';
import { FeedbackButton } from '@/pages/FeedbackList/FeedbackButton';
import {
  Divider,
  Empty,
  Flex,
  Input,
  Pagination,
  Select,
  Typography,
} from 'antd';
import { useNavigate } from 'react-router-dom';
import { FeedbackListItemCard } from './FeedbackListItemCard';
import { useFeedbackList } from './hooks';
import { FeedbackStatusLabels, FeedbackTypeLabels } from './utils';

export const FeedbackListPage: React.FC<any> = () => {
  const navigate = useNavigate();
  const {
    search: initialSearch,
    status: initialStatus,
    type: initialType,
    perPage,
    currentPage,
    error,
    loading,
    total,
    feedbackList,
    refresh,
    updateParams,
  } = useFeedbackList();

  if (loading) {
    return <LoadingState />;
  }

  if (error) {
    return (
      <ErrorState
        error={error}
        title="加载反馈列表失败"
        onRetry={refresh}
      />
    );
  }

  return (
    <div className="br-page-container">
      <Flex justify="space-between" align="center">
        <div>
          <Typography.Text className="br-section-label">反馈记录</Typography.Text>
          <Typography.Title level={2} className="br-page-title">反馈</Typography.Title>
        </div>
        <FeedbackButton onSubmit={refresh} />
      </Flex>

      <Divider size="small" />

      <Flex align="center" gap={7} wrap>
        <Select
          placeholder="按类型筛选"
          allowClear
          size="large"
          style={{ flex: 1, width: 150 }}
          value={initialType}
          onChange={(type) => updateParams({ type, page: 1 })}
          options={Object.entries(FeedbackTypeLabels).map(([value, label]) => ({
            value: Number(value),
            label,
          }))}
        />
        <Select
          placeholder="按状态筛选"
          allowClear
          size="large"
          style={{ flex: 1, width: 150 }}
          value={initialStatus}
          onChange={(status) => updateParams({ status, page: 1 })}
          options={Object.entries(FeedbackStatusLabels).map(
            ([value, label]) => ({
              value: Number(value),
              label,
            })
          )}
        />
        <Input.Search
          defaultValue={initialSearch}
          onSearch={(search) => updateParams({ search, page: 1 })}
          placeholder="搜索反馈"
          allowClear
          size="large"
          style={{ flex: 3, minWidth: 200 }}
        />
      </Flex>

      <Divider size="small" />

      {feedbackList.map((feedback) => (
        <FeedbackListItemCard
          key={feedback.id}
          feedback={feedback}
          onClick={() => navigate(`/feedback/${feedback.id}`)}
        />
      ))}

      {!feedbackList.length && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无反馈"
        />
      )}

      <Pagination
        current={currentPage}
        total={total}
        pageSize={perPage}
        showSizeChanger={false}
        onChange={(page) => updateParams({ page })}
        style={{ textAlign: 'center', marginTop: 32 }}
        hideOnSinglePage
      />
    </div>
  );
};

export default FeedbackListPage;
