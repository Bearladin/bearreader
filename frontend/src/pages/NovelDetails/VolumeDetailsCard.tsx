import { ErrorState } from '@/components/Loading/ErrorState';
import {
  type Chapter,
  type Job,
  type Paginated,
  type ReadHistory,
  type Volume,
} from '@/types';
import { volumeTitle } from '@/utils/format';
import { stringifyError } from '@/utils/errors';
import { formatDate } from '@/utils/time';
import { DownloadOutlined } from '@ant-design/icons';
import {
  Button,
  Card,
  Descriptions,
  Empty,
  Flex,
  Grid,
  message,
  Pagination,
  Spin,
} from 'antd';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChapterListCard } from './ChapterListCard';

export const VolumeDetailsCard: React.FC<{
  volume: Volume;
  inner?: boolean;
  history?: ReadHistory;
  hideChapters?: boolean;
}> = ({ volume, inner, hideChapters, history = {} }) => {
  const navigate = useNavigate();
  const { lg } = Grid.useBreakpoint();
  const [messageApi, contextHolder] = message.useMessage();

  const [page, setPage] = useState<number>(1);
  const [total, setTotal] = useState<number>(0);
  const [perPage, setPerPage] = useState<number>(10);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>();
  const [refreshId, setRefreshId] = useState(0);
  const [chapters, setChapters] = useState<Chapter[]>([]);

  useEffect(() => {
    const fetchChapters = async (id: string) => {
      try {
        setLoading(true);
        setError(undefined);
        const { data } = await axios.get<Paginated<Chapter>>(
          `/api/volume/${id}/chapters`,
          {
            params: {
              limit: perPage,
              offset: (page - 1) * perPage,
            },
          }
        );
        setTotal(data.total);
        setChapters(data.items);
      } catch (err) {
        setError(stringifyError(err));
        setChapters([]);
      } finally {
        setLoading(false);
      }
    };
    if (!hideChapters) {
      fetchChapters(volume.id);
    }
  }, [volume.id, hideChapters, page, perPage, refreshId]);

  const createVolumeJob = async (e: React.MouseEvent) => {
    try {
      e.stopPropagation();
      e.preventDefault();
      const result = await axios.post<Job>(`/api/job/create/fetch-volumes`, {
        volumes: [volume.id],
      });
      navigate(`/job/${result.data.id}`);
    } catch (err) {
      messageApi.error(stringifyError(err));
    }
  };

  return (
    <Card
      type={inner ? 'inner' : undefined}
      title={inner ? undefined : volumeTitle(volume.title)}
      variant={inner ? 'borderless' : 'outlined'}
      styles={{
        body: {
          padding: 10,
          paddingTop: 5,
        },
        title: {
          fontSize: 22,
          whiteSpace: 'wrap',
        },
      }}
    >
      {contextHolder}

      <Flex wrap vertical={!lg} align="center" justify="center" gap={10}>
        <Descriptions
          bordered
          size="small"
          layout="horizontal"
          column={lg ? 3 : 1}
          style={{ flex: 1, width: '100%' }}
          items={[
            {
              label: '序号',
              children: volume.serial,
            },
            {
              label: '章节',
              children: volume.chapter_count ?? 0,
            },
            {
              label: '最后更新',
              children: formatDate(volume.updated_at),
            },
          ]}
        />
        {!hideChapters && (
          <Button
            shape="round"
            onClick={createVolumeJob}
            icon={<DownloadOutlined />}
            style={{ padding: '0 12px' }}
          >
            获取分卷
          </Button>
        )}
      </Flex>

      {hideChapters ? null : loading ? (
        <Flex align="center" justify="center">
          <Spin size="large" style={{ margin: '50px 0' }} />
        </Flex>
      ) : error ? (
        <ErrorState
          error={error}
          title="加载章节失败"
          onRetry={() => setRefreshId((value) => value + 1)}
        />
      ) : chapters.length > 0 ? (
        <>
          <ChapterListCard chapters={chapters} history={history} />
          <Pagination
            total={total}
            current={page}
            pageSize={perPage}
            onChange={(page, perPage) => {
              setPage(page);
              setPerPage(perPage);
            }}
            hideOnSinglePage
          />
        </>
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无章节" />
      )}
    </Card>
  );
};
