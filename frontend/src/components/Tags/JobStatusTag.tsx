import { enumLabels } from '@/locales/zh-CN';
import { JobStatus, type Job } from '@/types';
import {
  CheckOutlined,
  CloseOutlined,
  HourglassOutlined,
  LoadingOutlined,
  PauseCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Tag } from 'antd';

export const JobStatusTag: React.FC<{ job: Job }> = ({ job }) => {
  switch (job.status) {
    case JobStatus.PENDING:
      return (
        <Tag icon={<HourglassOutlined />}>
          {enumLabels.jobStatus[job.status]}
        </Tag>
      );
    case JobStatus.RUNNING:
      return (
        <Tag icon={<LoadingOutlined spin />} color="cyan">
          {enumLabels.jobStatus[job.status]}
        </Tag>
      );
    case JobStatus.SUCCESS:
      return (
        <Tag icon={<CheckOutlined />} color="orange">
          {enumLabels.jobStatus[job.status]}
        </Tag>
      );
    case JobStatus.CANCELED:
      return (
        <Tag icon={<CloseOutlined />} color="red">
          {enumLabels.jobStatus[job.status]}
        </Tag>
      );
    case JobStatus.FAILED:
      return (
        <Tag icon={<WarningOutlined />} color="red">
          {enumLabels.jobStatus[job.status]}
        </Tag>
      );
    case JobStatus.PAUSED:
      return (
        <Tag icon={<PauseCircleOutlined />}>
          {enumLabels.jobStatus[job.status]}
        </Tag>
      );
    default:
      return <Tag>{String(job.status)}</Tag>;
  }
};
