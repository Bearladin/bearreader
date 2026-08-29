import { JobStatus, type Job } from '@/types';
import { Progress, theme, type ProgressProps } from 'antd';

function getProgressStatus(job: Job): ProgressProps['status'] {
  switch (job.status) {
    case JobStatus.PENDING:
      return 'normal';
    case JobStatus.RUNNING:
      return 'active';
    case JobStatus.SUCCESS:
      return 'success';
    case JobStatus.FAILED:
    case JobStatus.CANCELED:
      return 'exception';
  }
}

export const JobProgressCircle: React.FC<
  {
    job: Job;
  } & ProgressProps
> = ({ job, ...props }) => {
  const { token } = theme.useToken();
  return (
    <Progress
      size="small"
      {...props}
      type="circle"
      percent={job.progress || 0}
      status={getProgressStatus(job)}
      strokeColor={job.failed > 0 ? token.colorError : token.colorSuccess}
    />
  );
};

export const JobProgressLine: React.FC<
  {
    job: Job;
  } & ProgressProps
> = ({ job, ...props }) => {
  const { token } = theme.useToken();
  return (
    <Progress
      size={['100%', 12]}
      {...props}
      type="line"
      status={getProgressStatus(job)}
      percent={Math.round(job.progress || 0)}
      strokeColor={job.failed > 0 ? token.colorError : job.is_done ? token.colorSuccess : token.colorInfo}
    />
  );
};
