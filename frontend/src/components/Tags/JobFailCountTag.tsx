import { type Job } from '@/types';
import { WarningOutlined } from '@ant-design/icons';
import { Tag } from 'antd';

export const JobFailCountTag: React.FC<{ job: Job; short?: boolean }> = ({
  job,
  short = false,
}) => {
  if (job.failed <= 0 || job.total === 1) {
    return null;
  }
  const percent = Math.round((job.failed / job.total) * 100);
  return (
    <Tag icon={<WarningOutlined />} color="warning">
      <b>失败：</b>
      {short ? (
        <>{percent}%</>
      ) : (
        <>
          {job.failed} / {job.total} <b>({percent}%)</b>
        </>
      )}
    </Tag>
  );
};
