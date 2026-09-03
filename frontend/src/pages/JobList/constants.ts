import { enumLabels } from '@/locales/zh-CN';
import { JobStatus, JobType } from '@/types';

export const JobStatusFilterParams = [
  {
    value: 'any',
    label: '全部',
  },
  {
    value: 'successful',
    label: enumLabels.jobStatus[JobStatus.SUCCESS],
    params: { status: JobStatus.SUCCESS },
  },
  {
    value: 'failed',
    label: enumLabels.jobStatus[JobStatus.FAILED],
    params: { status: JobStatus.FAILED },
  },
  {
    value: 'partial',
    label: enumLabels.jobStatus[JobStatus.PARTIAL],
    params: { status: JobStatus.PARTIAL },
  },
  {
    value: 'canceled',
    label: enumLabels.jobStatus[JobStatus.CANCELED],
    params: { status: JobStatus.CANCELED },
  },
  {
    value: 'pending',
    label: enumLabels.jobStatus[JobStatus.PENDING],
    params: { status: JobStatus.PENDING },
  },
  {
    value: 'running',
    label: enumLabels.jobStatus[JobStatus.RUNNING],
    params: { status: JobStatus.RUNNING },
  },
  {
    value: 'paused',
    label: enumLabels.jobStatus[JobStatus.PAUSED],
    params: { status: JobStatus.PAUSED },
  },
];

export const JobTypeFilterParams = [
  {
    value: -1,
    label: '全部',
  },
  {
    value: JobType.NOVEL,
    label: enumLabels.jobType[JobType.NOVEL],
  },
  {
    value: JobType.NOVEL_BATCH,
    label: enumLabels.jobType[JobType.NOVEL_BATCH],
  },
  {
    value: JobType.FULL_NOVEL,
    label: enumLabels.jobType[JobType.FULL_NOVEL],
  },
  {
    value: JobType.FULL_NOVEL_BATCH,
    label: enumLabels.jobType[JobType.FULL_NOVEL_BATCH],
  },
  {
    value: JobType.CHAPTER,
    label: enumLabels.jobType[JobType.CHAPTER],
  },
  {
    value: JobType.CHAPTER_BATCH,
    label: enumLabels.jobType[JobType.CHAPTER_BATCH],
  },
  {
    value: JobType.VOLUME,
    label: enumLabels.jobType[JobType.VOLUME],
  },
  {
    value: JobType.VOLUME_BATCH,
    label: enumLabels.jobType[JobType.VOLUME_BATCH],
  },
  {
    value: JobType.IMAGE,
    label: enumLabels.jobType[JobType.IMAGE],
  },
  {
    value: JobType.IMAGE_BATCH,
    label: enumLabels.jobType[JobType.IMAGE_BATCH],
  },
  {
    value: JobType.ARTIFACT,
    label: enumLabels.jobType[JobType.ARTIFACT],
  },
  {
    value: JobType.ARTIFACT_BATCH,
    label: enumLabels.jobType[JobType.ARTIFACT_BATCH],
  },
];
