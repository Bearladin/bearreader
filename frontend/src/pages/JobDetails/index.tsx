import { ArtifactListCard } from '@/components/ArtifactList/ArtifactListCard';
import { ErrorState } from '@/components/Loading/ErrorState';
import { LoadingState } from '@/components/Loading/LoadingState';
import {
  type Artifact,
  type Chapter,
  type Job,
  type Novel,
  type Volume,
} from '@/types';
import { stringifyError } from '@/utils/errors';
import { DeploymentUnitOutlined, LeftOutlined } from '@ant-design/icons';
import { Divider, Grid, Space, Typography } from 'antd';
import axios from 'axios';
import { LRUCache } from 'lru-cache';
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { JobListPage } from '../JobList';
import { ChapterDetailsCard } from '../NovelDetails/ChapterDetailsCard';
import { NovelDetailsCard } from '../NovelDetails/NovelDetailsCard';
import { VolumeDetailsCard } from '../NovelDetails/VolumeDetailsCard';
import { JobDetailsCard } from './JobDetailsCard';
import { SearchResultsCard } from './SearchResultsCard';

const _cache = new LRUCache<string, any>({
  max: 1000,
  ttl: 30000,
});

async function handleFetch<T>(
  name: string,
  id: string | null | undefined,
  setValue: (value: T | undefined) => any,
  refreshCache?: boolean,
  signal?: AbortSignal
) {
  if (!id) {
    setValue(undefined);
    return;
  }
  const url = `/api/${name}/${id}`;
  if (refreshCache || !_cache.has(url)) {
    try {
      const res = await axios.get<T>(url, { signal });
      _cache.set(url, res.data);
    } catch (err) {
      // a cancelled request must neither cache nor overwrite state
      if (axios.isCancel(err)) return;
      _cache.delete(url);
    }
  }
  setValue(_cache.get(url));
}

export const JobDetailsPage: React.FC<any> = () => {
  const { lg } = Grid.useBreakpoint();
  const { id } = useParams<{ id: string }>();

  const [refreshId, setRefreshId] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const [job, setJob] = useState<Job>();
  const [novel, setNovel] = useState<Novel | undefined>();
  const [volume, setVolume] = useState<Volume | undefined>();
  const [chapter, setChapter] = useState<Chapter | undefined>();
  const [artifact, setArtifact] = useState<Artifact | undefined>();

  useEffect(() => {
    // AbortController + generation flag: switching jobs quickly cancels the
    // old request and stale responses can never overwrite the current one.
    const aborter = new AbortController();
    const fetchJob = async (jobId: string) => {
      setError(undefined);
      try {
        const { data: job } = await axios.get<Job>(`/api/job/${jobId}`, {
          signal: aborter.signal,
        });
        if (aborter.signal.aborted) return;
        setJob(job);
      } catch (err: any) {
        if (axios.isCancel(err)) return;
        if (aborter.signal.aborted) return;
        setError(stringifyError(err));
      } finally {
        if (!aborter.signal.aborted) setLoading(false);
      }
    };
    if (id) {
      fetchJob(id);
    }
    return () => aborter.abort();
  }, [id, refreshId]);

  useEffect(() => {
    const aborter = new AbortController();
    void handleFetch('novel', job?.extra.novel_id, setNovel, job?.is_done, aborter.signal);
    return () => aborter.abort();
  }, [job?.extra.novel_id, job?.is_done]);

  useEffect(() => {
    const aborter = new AbortController();
    void handleFetch('volume', job?.extra.volume_id, setVolume, job?.is_done, aborter.signal);
    return () => aborter.abort();
  }, [job?.extra.volume_id, job?.is_done]);

  useEffect(() => {
    const aborter = new AbortController();
    void handleFetch('chapter', job?.extra.chapter_id, setChapter, job?.is_done, aborter.signal);
    return () => aborter.abort();
  }, [job?.extra.chapter_id, job?.is_done]);

  useEffect(() => {
    const aborter = new AbortController();
    void handleFetch('artifact', job?.extra.artifact_id, setArtifact, job?.is_done, aborter.signal);
    return () => aborter.abort();
  }, [job?.extra.artifact_id, job?.is_done]);

  useEffect(() => {
    if (job && !job.is_done) {
      let stopped = false;
      let tid: ReturnType<typeof setTimeout>;
      const schedule = () => {
        if (stopped) return;
        // chained setTimeout (not setInterval): the next refresh is only
        // scheduled after the previous cycle finished, so a slow response
        // can never stack requests; slow down while the window is hidden
        tid = setTimeout(() => {
          if (stopped) return;
          setRefreshId((v) => v + 1);
          schedule();
        }, document.hidden ? 5000 : 2000);
      };
      schedule();
      return () => {
        stopped = true;
        clearTimeout(tid);
      };
    }
  }, [job]);

  if (loading) {
    return <LoadingState />;
  }

  if (!job) {
    return (
      <ErrorState
        error={error}
        title="加载任务请求数据失败"
        onRetry={() => {
          setLoading(true);
          setRefreshId((v) => v + 1);
        }}
      />
    );
  }

  return (
    <Space vertical size={lg ? 'middle' : 'small'}>
      {job.parent_job_id ? (
        <Link to={`/job/${job.parent_job_id}`}>
          <LeftOutlined /> 上级任务请求
        </Link>
      ) : (
        <Link to={`/jobs`}>
          <LeftOutlined /> 全部任务请求
        </Link>
      )}

      <JobDetailsCard job={job} />
      {/* 单用户本地应用：不显示任务发起人卡片 */}
      {novel && <NovelDetailsCard novel={novel} withPageLink />}
      {volume && <VolumeDetailsCard volume={volume} hideChapters />}
      {chapter && <ChapterDetailsCard chapter={chapter} />}
      {artifact && <ArtifactListCard artifacts={[artifact]} />}

      <SearchResultsCard job={job} />

      <JobListPage
        key={job.id + job.is_done}
        parentJobId={job.id}
        autoRefresh={!job.is_done}
        hideIfEmpty
        title={
          <>
            <Divider style={{ margin: 0 }} />
            <Typography.Title level={3}>
              <DeploymentUnitOutlined /> 关联任务请求
            </Typography.Title>
          </>
        }
      />
    </Space>
  );
};
