import { ErrorState } from '@/components/Loading/ErrorState';
import { type Job, type ReadHistory, type Volume } from '@/types';
import { volumeTitle } from '@/utils/format';
import { stringifyError } from '@/utils/errors';
import { DownloadOutlined } from '@ant-design/icons';
import {
  Button,
  Card,
  Collapse,
  Empty,
  Flex,
  message,
  Spin,
  Typography,
} from 'antd';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { VolumeDetailsCard } from './VolumeDetailsCard';

export const VolumeListCard: React.FC<{
  novelId: string;
  inner?: boolean;
}> = ({ novelId, inner }) => {
  const navigate = useNavigate();
  const [messageApi, contextHolder] = message.useMessage();

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>();
  const [refreshId, setRefreshId] = useState(0);
  const [volumes, setVolumes] = useState<Volume[]>([]);
  const [history, setHistory] = useState<ReadHistory>({});

  useEffect(() => {
    const fetchVolumes = async (id: string) => {
      setVolumes([]);
      setLoading(true);
      setError(undefined);
      try {
        const { data: volumes } = await axios.get<Volume[]>(
          `/api/novel/${id}/volumes`
        );
        setVolumes(volumes);
      } catch (err) {
        setError(stringifyError(err));
      } finally {
        setLoading(false);
      }
    };

    const fetchReadHistory = async (id: string) => {
      setHistory({});
      try {
        const { data: hisotry } = await axios.get<ReadHistory>(
          `/api/read-history/by-novel`,
          {
            params: {
              novel_id: id,
            },
          }
        );
        setHistory(hisotry);
      } catch (err) {
        messageApi.error(stringifyError(err));
      }
    };

    fetchVolumes(novelId);
    fetchReadHistory(novelId);
  }, [novelId, messageApi, refreshId]);

  const createVolumeJob = async (e: React.MouseEvent, volumes: string[]) => {
    try {
      e.stopPropagation();
      e.preventDefault();
      const result = await axios.post<Job>(`/api/job/create/fetch-volumes`, {
        volumes,
      });
      navigate(`/job/${result.data.id}`);
    } catch (err) {
      messageApi.error(stringifyError(err));
    }
  };

  return (
    <Card
      type={inner ? 'inner' : undefined}
      title={!inner && '目录'}
      variant={inner ? 'borderless' : 'outlined'}
      style={{ borderRadius: inner ? 0 : undefined }}
      styles={{
        body: { padding: 10 },
        title: { fontSize: 22 },
      }}
      extra={
        <Button
          shape="round"
          style={{ padding: '0 12px' }}
          icon={<DownloadOutlined />}
          onClick={(e) =>
            createVolumeJob(
              e,
              volumes.map((v) => v.id)
            )
          }
        >
          获取全部分卷
        </Button>
      }
    >
      {contextHolder}

      {loading ? (
        <Flex align="center" justify="center">
          <Spin size="large" style={{ margin: '50px 0' }} />
        </Flex>
      ) : error ? (
        <ErrorState
          error={error}
          title="加载分卷失败"
          onRetry={() => setRefreshId((value) => value + 1)}
        />
      ) : volumes.length > 0 ? (
        <Collapse
          accordion
          items={volumes.map((volume) => ({
            key: volume.id,
            label: volumeTitle(volume.title),
            children: (
              <VolumeDetailsCard inner volume={volume} history={history} />
            ),
            extra: (
              <Typography.Text
                type="secondary"
                style={{ fontSize: '12px', whiteSpace: 'nowrap' }}
              >
                {new Intl.NumberFormat('zh-CN').format(volume.chapter_count)} 章
              </Typography.Text>
            ),
            styles: {
              body: { padding: 0 },
              header: { textTransform: 'capitalize' },
            },
          }))}
        />
      ) : (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无分卷" />
      )}
    </Card>
  );
};
