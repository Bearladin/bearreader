import { AddToLibraryButton } from '@/components/Library/AddToLibraryButton';
import { EpubImportModal } from '@/components/EpubImportModal';
import { ErrorState } from '@/components/Loading/ErrorState';
import { AppstoreOutlined, UnorderedListOutlined, UploadOutlined } from '@ant-design/icons';
import { Button, Col, Empty, Flex, Pagination, Row, Segmented, Skeleton, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useNovelList } from './hooks';
import { NovelFilterBox } from './NovelFilterBox';
import { NovelListItemCard } from './NovelListItemCard';

// 与 NovelListItemCard 同形的骨架屏（封面 3:4 + 两行标题区），
// 加载期间占住网格布局，避免 Spin 后卡片跳动。
const NovelListSkeleton: React.FC = () => (
  <Row gutter={[16, 16]}>
    {Array.from({ length: 12 }).map((_, i) => (
      <Col key={i} xs={8} lg={6} xl={4}>
        <div
          style={{
            background: 'var(--br-surface)',
            border: '1px solid var(--br-border)',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              position: 'relative',
              width: '100%',
              paddingTop: '133.333%',
            }}
          >
            <Skeleton.Node
              active
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
              }}
            />
          </div>
          <div style={{ height: 56, padding: '8px 10px' }}>
            <Skeleton.Node active style={{ width: '80%', height: 20 }} />
          </div>
        </div>
      </Col>
    ))}
  </Row>
);

export const NovelListPage: React.FC<any> = () => {
  const [view, setView] = useState<'list' | 'grid'>(() =>
    localStorage.getItem('bearreader/novels/view') === 'grid' ? 'grid' : 'list'
  );
  const [searchParams, setSearchParams] = useSearchParams();
  const [importOpen, setImportOpen] = useState(false);
  const highlightedNovelId = searchParams.get('highlight');
  const {
    search: initialSearch,
    domain: initialDomain,
    sort: initialSort,
    currentPage,
    perPage,
    error,
    loading,
    total,
    novels,
    refresh,
    updateParams,
  } = useNovelList();

  useEffect(() => {
    if (!highlightedNovelId) return;
    const timer = window.setTimeout(() => {
      setSearchParams((current) => {
        const next = new URLSearchParams(current);
        next.delete('highlight');
        return next;
      }, { replace: true });
    }, 6000);
    return () => window.clearTimeout(timer);
  }, [highlightedNovelId, setSearchParams]);

  if (loading) {
    return <NovelListSkeleton />;
  }

  if (error) {
    return (
      <ErrorState
        error={error}
        title="加载小说列表失败"
        onRetry={refresh}
      />
    );
  }

  return (
    <div className="br-page-container">
      <Flex align="end" justify="space-between" gap={16} wrap style={{ marginBottom: 24 }}>
        <div>
          <Typography.Text className="br-section-label">小说索引</Typography.Text>
          <Typography.Title className="br-page-title" level={2}>全部小说</Typography.Title>
          <Typography.Text type="secondary">已收录 {total} 本小说</Typography.Text>
        </div>
        <Flex gap={8} wrap justify="end">
          <Button
            icon={<UploadOutlined />}
            onClick={() => setImportOpen(true)}
          >
            导入书籍
          </Button>
          <Segmented
            aria-label="切换小说显示方式"
            value={view}
            options={[
              { value: 'list', icon: <UnorderedListOutlined />, label: '列表' },
              { value: 'grid', icon: <AppstoreOutlined />, label: '网格' },
            ]}
            onChange={(value) => {
              const next = value as 'list' | 'grid';
              setView(next);
              localStorage.setItem('bearreader/novels/view', next);
            }}
          />
        </Flex>
      </Flex>

      <NovelFilterBox
        search={initialSearch}
        domain={initialDomain}
        sort={initialSort}
        updateParams={updateParams}
      />

      <Row gutter={view === 'list' ? [12, 12] : [16, 16]} style={{ marginTop: 24 }}>
        {novels.map((novel) => (
          <Col key={novel.id} xs={view === 'list' ? 24 : 12} sm={view === 'list' ? 24 : 8} lg={view === 'list' ? 12 : 6} xl={view === 'list' ? 12 : 4}>
            <div
              style={{
                position: 'relative',
                outline:
                  highlightedNovelId === novel.id
                    ? '2px solid var(--br-border-strong)'
                    : undefined,
                outlineOffset: 2,
              }}
            >
              <div
                style={{ position: 'absolute', right: 4, top: 4, zIndex: 2 }}
                onClick={(e) => e.stopPropagation()}
              >
                <AddToLibraryButton
                  novelId={novel.id}
                  buttonText="添加"
                  buttonType="primary"
                  size="small"
                />
              </div>
              <NovelListItemCard novel={novel} view={view} />
            </div>
          </Col>
        ))}
      </Row>

      {!novels.length && (
        <Flex align="center" justify="center" style={{ height: '100%' }}>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无小说" />
        </Flex>
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
      <EpubImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
      />
    </div>
  );
};
