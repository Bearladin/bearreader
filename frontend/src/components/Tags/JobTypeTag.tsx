import { enumLabels } from '@/locales/zh-CN';
import { JobType } from '@/types';
import {
  AppstoreOutlined,
  BookOutlined,
  CloudDownloadOutlined,
  CloudUploadOutlined,
  FileTextOutlined,
  FolderOutlined,
  PictureOutlined,
  ReadOutlined,
  SearchOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { Tag } from 'antd';

export const JobTypeTag: React.FC<{ value: JobType }> = ({ value }) => {
  function single(icon: any, name: string) {
    return <Tag icon={icon}>{name}</Tag>;
  }
  function batch(icon: any, name: string) {
    return (
      <Tag color="cyan" style={{ position: 'relative', paddingLeft: 24 }}>
        <span style={{ position: 'absolute', left: 4, top: 0 }}>{icon}</span>
        <span style={{ position: 'absolute', left: 6, top: 2 }}>{icon}</span>
        {name}
      </Tag>
    );
  }

  switch (value) {
    case JobType.NOVEL:
      return single(<BookOutlined />, enumLabels.jobType[value]);
    case JobType.NOVEL_BATCH:
      return batch(<BookOutlined />, enumLabels.jobType[value]);
    case JobType.FULL_NOVEL:
      return single(<ReadOutlined />, enumLabels.jobType[value]);
    case JobType.FULL_NOVEL_BATCH:
      return batch(<ReadOutlined />, enumLabels.jobType[value]);
    case JobType.CHAPTER:
      return single(<FileTextOutlined />, enumLabels.jobType[value]);
    case JobType.CHAPTER_BATCH:
      return batch(<FileTextOutlined />, enumLabels.jobType[value]);
    case JobType.VOLUME:
      return single(<FolderOutlined />, enumLabels.jobType[value]);
    case JobType.VOLUME_BATCH:
      return batch(<FolderOutlined />, enumLabels.jobType[value]);
    case JobType.IMAGE:
      return single(<PictureOutlined />, enumLabels.jobType[value]);
    case JobType.IMAGE_BATCH:
      return batch(<PictureOutlined />, enumLabels.jobType[value]);
    case JobType.ARTIFACT:
      return single(<AppstoreOutlined />, enumLabels.jobType[value]);
    case JobType.ARTIFACT_BATCH:
      return batch(<AppstoreOutlined />, enumLabels.jobType[value]);
    case JobType.SEARCH_SOURCE:
      return single(<SearchOutlined />, enumLabels.jobType[value]);
    case JobType.SEARCH_ALL_SOURCES:
      return batch(<SearchOutlined />, enumLabels.jobType[value]);
    case JobType.FETCH_MISSING:
      return single(<CloudDownloadOutlined />, enumLabels.jobType[value]);
    case JobType.FETCH_LATEST:
      return single(<SyncOutlined />, enumLabels.jobType[value]);
    case JobType.IMPORT_EPUB_ANALYZE:
      return single(<CloudUploadOutlined />, enumLabels.jobType[value]);
    case JobType.IMPORT_EPUB_COMMIT:
      return single(<CloudUploadOutlined />, enumLabels.jobType[value]);
    default:
      return <Tag>{String(value)}</Tag>;
  }
};
