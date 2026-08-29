import { ErrorState } from '@/components/Loading/ErrorState';
import { LoadingState } from '@/components/Loading/LoadingState';
import { Auth } from '@/store/_auth';
import type { Library } from '@/types';
import { stringifyError } from '@/utils/errors';
import { Space } from 'antd';
import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';
import { useSelector } from 'react-redux';
import { useParams } from 'react-router-dom';
import { LibraryInfoCard } from './LibraryInfoCard';
import { LibraryNovelList } from './LibraryNovelList';

export const LibraryDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const user = useSelector(Auth.select.user);

  const [loading, setLoading] = useState<boolean>(true);
  const [refresh, setRefresh] = useState<number>(0);
  const [error, setError] = useState<string>();
  const [library, setLibrary] = useState<Library>();

  const isOwner = useMemo(
    () => Boolean(library && user?.id === library.user_id),
    [user?.id, library]
  );

  useEffect(() => {
    const loadDetails = async () => {
      setLoading(true);
      setError(undefined);
      try {
        const { data } = await axios.get<Library>(`/api/library/${id}`);
        setLibrary(data);
      } catch (err) {
        setError(stringifyError(err));
      } finally {
        setLoading(false);
      }
    };
    if (id) {
      loadDetails();
    }
  }, [id, refresh]);

  const handleLibraryUpdated = (updatedLibrary: Library) => {
    setLibrary(updatedLibrary);
  };

  if (loading) {
    return <LoadingState message="正在加载书架详情…" />;
  }

  if (error || !library) {
    return (
      <ErrorState
        error={error}
        title="加载书架失败"
        onRetry={() => setRefresh((v) => v + 1)}
      />
    );
  }

  return (
    <Space vertical style={{ width: '100%' }}>
      <LibraryInfoCard
        library={library}
        isOwner={isOwner}
        onLibraryUpdated={handleLibraryUpdated}
      />

      {/* 管理员登录模式下隐藏所有者信息卡片 */}

      <LibraryNovelList library={library} isOwner={isOwner} />
    </Space>
  );
};
