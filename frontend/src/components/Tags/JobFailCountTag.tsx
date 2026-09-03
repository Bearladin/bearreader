import { JobType, type Job } from '@/types';
import { WarningOutlined } from '@ant-design/icons';
import { Tag } from 'antd';

export const JobFailCountTag: React.FC<{ job: Job; short?: boolean }> = ({
  job,
  short = false,
}) => {
  const searchSources = Object.values(job.extra.search_sources ?? {});
  const sourceFailed = searchSources.filter(
    (source) => source.state === 'failed' || source.state === 'partial'
  ).length;
  const isAllSourceSearch = job.type === JobType.SEARCH_ALL_SOURCES;
  const failed = isAllSourceSearch ? sourceFailed : job.failed;
  const total = isAllSourceSearch
    ? (job.extra.search_source_total ?? searchSources.length)
    : job.total;
  if (failed <= 0 || total <= 1) {
    return null;
  }
  const percent = Math.round((failed / total) * 100);
  return (
    <Tag icon={<WarningOutlined />} color="warning">
      <b>{isAllSourceSearch ? '书源失败：' : '失败：'}</b>
      {short ? (
        <>{percent}%</>
      ) : (
        <>
          {failed} / {total} <b>({percent}%)</b>
        </>
      )}
    </Tag>
  );
};
