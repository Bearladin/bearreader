import { ErrorState } from '@/components/Loading/ErrorState';
import { LoadingState } from '@/components/Loading/LoadingState';
import { Divider, Empty, Flex, Pagination, Select, Typography } from 'antd';
import { TrackedNovelCard } from './TrackedNovelCard';
import { useTrackedNovels } from './hooks';

export const TrackedNovelsPage: React.FC = () => {
  const {
    items,
    loading,
    error,
    total,
    currentPage,
    perPage,
    isActive,
    refresh,
    updateParams,
  } = useTrackedNovels();

  if (loading) {
    return <LoadingState />;
  }

  if (error) {
    return (
      <ErrorState
        error={error}
        title="加载追更小说失败"
        onRetry={refresh}
      />
    );
  }

  return (
    <div className="br-page-container">
      <Flex justify="space-between" align="center">
        <div>
          <Typography.Text className="br-section-label">追更列表</Typography.Text>
          <Typography.Title level={2} className="br-page-title">追更小说</Typography.Title>
        </div>
      </Flex>

      <Divider size="small" />

      <Flex align="center" gap={7} wrap>
        <Select
          placeholder="按状态筛选"
          allowClear
          size="large"
          style={{ width: 180 }}
          value={isActive}
          onChange={(value) => updateParams({ is_active: value, page: 1 })}
          options={[
            { value: true, label: '追更中' },
            { value: false, label: '已暂停' },
          ]}
        />
      </Flex>

      <Divider size="small" />

      {items.map((item) => (
        <TrackedNovelCard key={item.id} item={item} onRefresh={refresh} />
      ))}

      {!items.length && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无追更小说"
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

export default TrackedNovelsPage;
