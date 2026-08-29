import { ErrorState } from '@/components/Loading/ErrorState';
import { LoadingState } from '@/components/Loading/LoadingState';
import type { Library, Novel, Paginated } from '@/types';
import { stringifyError } from '@/utils/errors';
import {
  AppstoreOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons';
import {
  Col,
  Divider,
  Empty,
  Flex,
  Pagination,
  Row,
  Segmented,
  Space,
  Typography,
} from 'antd';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { NovelListItemCard } from '../NovelList/NovelListItemCard';
import { RemoveLibraryNovelButton } from './RemoveLibraryNovelButton';

const PAGE_SIZE = 12;

export const LibraryNovelList: React.FC<{
  library: Library;
  isOwner: boolean;
}> = ({ library, isOwner }) => {
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState<boolean>(true);
  const [refresh, setRefresh] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [total, setTotal] = useState<number>(0);
  const [novels, setNovels] = useState<Novel[]>([]);
  const [view, setView] = useState<'grid' | 'list'>(() =>
    localStorage.getItem('bearreader/library/view') === 'grid' ? 'grid' : 'list'
  );

  useEffect(() => {
    setLoading(true);
    setError(undefined);
    const loadNovels = async () => {
      try {
        const { data } = await axios.get<Paginated<Novel>>(
          `/api/library/${library.id}/novels`,
          {
            params: {
              limit: PAGE_SIZE,
              offset: (page - 1) * PAGE_SIZE,
            },
          }
        );
        setTotal(data.total);
        setNovels(data.items || []);
      } catch (err: any) {
        setError(stringifyError(err, '加载小说失败，请稍后重试。'));
      } finally {
        setLoading(false);
      }
    };
    loadNovels();
  }, [library.id, refresh, page]);

  if (loading) {
    return <LoadingState />;
  }

  if (error) {
    return (
      <ErrorState
        error={error}
        title="加载小说失败"
        onRetry={() => setRefresh((v) => v + 1)}
      />
    );
  }

  return (
    <>
      <Flex align="center" justify="space-between">
        <div>
          <Typography.Text className="br-section-label">书架藏书</Typography.Text>
          <Typography.Title className="br-page-title" level={4}>小说</Typography.Title>
        </div>
        <Flex gap={12} align="center">
          <Typography.Text type="secondary">共 {total || 0} 本</Typography.Text>
          <Segmented
            aria-label="切换书架小说显示方式"
            value={view}
            options={[
              { value: 'grid', icon: <AppstoreOutlined /> },
              { value: 'list', icon: <UnorderedListOutlined /> },
            ]}
            onChange={(value) => {
              const next = value as 'grid' | 'list';
              setView(next);
              localStorage.setItem('bearreader/library/view', next);
            }}
          />
        </Flex>
      </Flex>

      <Divider size="small" />

      <Space vertical style={{ width: '100%' }} size="middle">
        {novels.length ? (
          <Row gutter={[12, 12]}>
            {novels.map((novel) => (
              <Col key={novel.id} xs={view === 'list' ? 24 : 12} sm={view === 'list' ? 24 : 12} md={view === 'list' ? 24 : 8} lg={view === 'list' ? 12 : 6} xl={view === 'list' ? 12 : 4}>
                <div style={{ position: 'relative' }}>
                  {isOwner && (
                    <RemoveLibraryNovelButton
                      novel={novel}
                      library={library}
                      onRemoved={() => setRefresh((v) => v + 1)}
                    />
                  )}
                  <NovelListItemCard novel={novel} view={view} />
                </div>
              </Col>
            ))}
          </Row>
        ) : (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无小说"
          />
        )}

        <Pagination
          current={page}
          total={total || 0}
          pageSize={PAGE_SIZE}
          onChange={(p) => setPage(p)}
          hideOnSinglePage
        />
      </Space>
    </>
  );
};
