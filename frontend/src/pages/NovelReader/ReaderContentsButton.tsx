import { ErrorState } from '@/components/Loading/ErrorState';
import { Reader } from '@/store/_reader';
import type { Chapter } from '@/types';
import { stringifyError } from '@/utils/errors';
import { UnorderedListOutlined } from '@ant-design/icons';
import { Button, ConfigProvider, Empty, Grid, List, Modal, Pagination } from 'antd';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useSelector } from 'react-redux';
import styles from './ReaderContentsButton.module.scss';
import { getReaderOverlayTheme } from './readerTheme';

const PAGE_SIZE = 100;

export const ReaderContentsButton: React.FC<{
  className?: string;
  novelId: string;
}> = ({ className, novelId }) => {
  const location = useLocation();
  const { md } = Grid.useBreakpoint();
  const readerTheme = useSelector(Reader.select.theme);
  const [open, setOpen] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [page, setPage] = useState(1);

  // reset pagination when the novel changes or the modal reopens
  useEffect(() => {
    setOpen(false);
    setPage(1);
  }, [location]);

  const visibleChapters = chapters.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE
  );

  const fetchChapters = async () => {
    try {
      setOpen(true);
      if (!chapters.length) {
        setLoading(true);
        setError(undefined);
        // the endpoint returns Paginated<Chapter> and defaults to limit=20 —
        // fetch every page up to the reported total so the TOC is complete
        // (thousands of chapters in a few 500-chapter requests).
        const PAGE = 1000;
        const first = await axios.get<{ items: Chapter[]; total: number }>(
          `/api/novel/${novelId}/chapters`,
          { params: { limit: PAGE } }
        );
        const all = [...(first.data.items ?? [])];
        const total = first.data.total ?? all.length;
        for (let offset = PAGE; offset < total; offset += PAGE) {
          const next = await axios.get<{ items: Chapter[] }>(
            `/api/novel/${novelId}/chapters`,
            { params: { limit: PAGE, offset } }
          );
          all.push(...(next.data.items ?? []));
        }
        setChapters(all);
      }
    } catch (err) {
      setError(stringifyError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button
        aria-label="目录"
        className={className}
        type="text"
        style={{
          borderRadius: 0,
          background: 'transparent',
          color: 'inherit',
          boxShadow: 'none',
        }}
        icon={<UnorderedListOutlined />}
        loading={loading}
        onClick={fetchChapters}
      >
        {md && '目录'}
      </Button>

      <ConfigProvider theme={getReaderOverlayTheme(readerTheme)}>
      <Modal
        closable={{ 'aria-label': '关闭目录窗口' }}
        centered
        open={open}
        width={600}
        footer={null}
        destroyOnHidden
        loading={loading}
        title="目录"
        onCancel={() => setOpen(false)}
        style={{ padding: 15 }}
        styles={{
          mask: {
            background: readerTheme.background === '#121212' || readerTheme.background === '#000000'
              ? 'rgba(0, 0, 0, 0.56)'
              : 'rgba(23, 23, 23, 0.28)',
          },
        }}
      >
        {error ? (
          <ErrorState
            error={error}
            title="加载目录失败"
            onRetry={fetchChapters}
          />
        ) : chapters.length > 0 ? (
          <>
            <List
              size="small"
              dataSource={visibleChapters}
              renderItem={(chapter) => (
                <List.Item className={styles.chapterItem}>
                  <Link
                    className={styles.chapterLink}
                    to={`/read/${chapter.id}`}
                  >
                    <span className={styles.chapterSerial}>
                      {chapter.serial}
                    </span>
                    <span className={styles.chapterTitle}>{chapter.title}</span>
                  </Link>
                </List.Item>
              )}
            />
            <Pagination
              current={page}
              pageSize={PAGE_SIZE}
              total={chapters.length}
              onChange={setPage}
              showSizeChanger={false}
              size="small"
              style={{ textAlign: 'center', marginTop: 12 }}
              hideOnSinglePage
            />
          </>
        ) : (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无章节" />
        )}
      </Modal>
      </ConfigProvider>
    </>
  );
};
