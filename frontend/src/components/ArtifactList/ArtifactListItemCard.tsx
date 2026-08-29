import { API_BASE_URL } from '@/config';
import { Auth } from '@/store/_auth';
import { type Artifact } from '@/types';
import { formatFileSize } from '@/utils/size';
import { formatDate } from '@/utils/time';
import {
  ClockCircleOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  FileZipFilled,
  TagOutlined,
} from '@ant-design/icons';
import { Button, Flex, Grid, List, Tag, Tooltip, Typography } from 'antd';
import { useSelector } from 'react-redux';

export const ArtifactListItemCard: React.FC<{ artifact: Artifact }> = ({
  artifact: item,
}) => {
  const { sm } = Grid.useBreakpoint();
  const token = useSelector(Auth.select.authToken);
  return (
    <List.Item
      actions={
        item.is_available
          ? [
              <Button
                aria-label="下载导出文件"
                type="primary"
                target="_blank"
                rel="noopener noreferrer"
                icon={<DownloadOutlined />}
                href={`${API_BASE_URL}/static/${item.output_file}?token=${token}`}
              >
                {sm ? '下载' : ''}
              </Button>,
            ]
          : [
              <Tooltip title="此文件已不可用">
                <Button
                  aria-label="导出文件不可用"
                  disabled
                  icon={<ExclamationCircleOutlined />}
                >
                  {sm ? '下载' : ''}
                </Button>
              </Tooltip>,
            ]
      }
    >
      <List.Item.Meta
        description={
          item.is_available ? item.file_name : <s>{item.file_name}</s>
        }
        title={
          <Flex wrap="wrap-reverse" gap={8} align="center">
            <Tag icon={<TagOutlined />}>{item.format}</Tag>
            {Boolean(item.file_size && item.file_size > 0) && (
              <Typography.Text
                type="warning"
                style={{
                  whiteSpace: 'nowrap',
                  fontWeight: 'normal',
                  fontSize: 12,
                }}
              >
                <FileZipFilled /> {formatFileSize(item.file_size)}
              </Typography.Text>
            )}
            <Typography.Text
              ellipsis
              style={{ fontWeight: 'normal', fontSize: 12 }}
            >
              <ClockCircleOutlined /> {formatDate(item.updated_at)}
            </Typography.Text>
          </Flex>
        }
      />
    </List.Item>
  );
};
