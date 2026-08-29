import { ErrorState } from '@/components/Loading/ErrorState';
import { LoadingState } from '@/components/Loading/LoadingState';
import { type Artifact, type Novel } from '@/types';
import { stringifyError } from '@/utils/errors';
import { Grid, Space } from 'antd';
import axios from 'axios';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ArtifactListCard } from '../../components/ArtifactList/ArtifactListCard';
import { NovelDetailsCard } from './NovelDetailsCard';
import { VolumeListCard } from './VolumeListCard';

export const NovelDetailsPage: React.FC<any> = () => {
  const { id } = useParams<{ id: string }>();

  const { lg } = Grid.useBreakpoint();

  const [refreshId, setRefreshId] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const [novel, setNovel] = useState<Novel>();
  const [artifactRefreshId, setArtifactRefreshId] = useState(0);
  const [artifactLoading, setArtifactLoading] = useState(true);
  const [artifactError, setArtifactError] = useState<string>();
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);

  useEffect(() => {
    let isCurrent = true;

    const fetchNovel = async (novelId: string) => {
      try {
        const { data: novel } = await axios.get<Novel>(
          `/api/novel/${novelId}`
        );
        if (isCurrent) {
          setNovel(novel);
        }
      } catch (err: any) {
        if (isCurrent) {
          setError(stringifyError(err));
        }
      } finally {
        if (isCurrent) {
          setLoading(false);
        }
      }
    };

    if (id) {
      setLoading(true);
      setError(undefined);
      fetchNovel(id);
    }
    return () => {
      isCurrent = false;
    };
  }, [id, refreshId]);

  useEffect(() => {
    let isCurrent = true;

    const fetchArtifacts = async (novelId: string) => {
      try {
        const { data: artifacts } = await axios.get<Artifact[]>(
          `/api/novel/${novelId}/artifacts`
        );
        if (isCurrent) {
          setArtifacts(artifacts);
        }
      } catch (err) {
        if (isCurrent) {
          setArtifactError(stringifyError(err));
        }
      } finally {
        if (isCurrent) {
          setArtifactLoading(false);
        }
      }
    };

    setArtifacts([]);
    setArtifactError(undefined);
    setArtifactLoading(true);
    if (id && novel?.id === id) {
      fetchArtifacts(id);
    }
    return () => {
      isCurrent = false;
    };
  }, [id, novel?.id, artifactRefreshId]);

  if (loading) {
    return <LoadingState />;
  }

  if (error || !novel || !id) {
    return (
      <ErrorState
        error={error}
        title="加载小说详情失败"
        onRetry={() => {
          setLoading(true);
          setRefreshId((v) => v + 1);
        }}
      />
    );
  }

  return (
    <Space vertical size={lg ? 'large' : 'small'}>
      <NovelDetailsCard novel={novel} showActions />
      <VolumeListCard novelId={novel.id} />
      {artifactLoading ? (
        <LoadingState message="正在加载导出文件…" />
      ) : artifactError ? (
        <ErrorState
          error={artifactError}
          title="加载导出文件失败"
          onRetry={() => setArtifactRefreshId((value) => value + 1)}
        />
      ) : (
        <ArtifactListCard
          artifacts={artifacts}
          showMakeButton
          novelId={novel.id}
        />
      )}
    </Space>
  );
};
