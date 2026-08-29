import type { TrackedNovel } from '@/types';
import { formatFromNow } from '@/utils/time';
import { stringifyError } from '@/utils/errors';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  DeleteOutlined,
  ExclamationCircleOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import {
  Button,
  Card,
  Flex,
  Grid,
  message,
  Popconfirm,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import axios from 'axios';
import { useState } from 'react';

export const TrackedNovelCard: React.FC<{
  item: TrackedNovel;
  onRefresh: () => void;
}> = ({ item, onRefresh }) => {
  const { lg } = Grid.useBreakpoint();
  const [checking, setChecking] = useState(false);

  const handleForceCheck = async () => {
    setChecking(true);
    try {
      await axios.post(`/api/watcher/${item.id}/check`);
      message.success('检查完成。');
      onRefresh();
    } catch (err: any) {
      message.error(stringifyError(err));
    } finally {
      setChecking(false);
    }
  };

  const handleToggleActive = async () => {
    try {
      await axios.patch(`/api/watcher/${item.id}`, {
        is_active: !item.is_active,
      });
      message.success(item.is_active ? '已暂停追更。' : '已恢复追更。');
      onRefresh();
    } catch (err: any) {
      message.error(stringifyError(err));
    }
  };

  const handleDelete = async () => {
    try {
      await axios.delete(`/api/watcher/${item.id}`);
      message.success('已停止追更。');
      onRefresh();
    } catch (err: any) {
      message.error(stringifyError(err));
    }
  };

  const statusColor = item.last_error
    ? '#9A514A'
    : item.is_active
      ? '#51705A'
      : '#8A8A84';

  return (
    <Card
      style={{
        marginBottom: 8,
        borderRadius: 2,
        overflow: 'hidden',
        borderLeft: `4px solid ${statusColor}`,
      }}
      styles={{
        body: {
          padding: lg ? '12px 20px' : '10px 15px',
        },
      }}
    >
      <Flex justify="space-between" align="center" wrap gap="small">
        <Typography.Title
          level={4}
          ellipsis
          style={{ flex: 1, margin: 0 }}
        >
          {item.title || item.novel_url}
        </Typography.Title>
        <Space size="small">
          {item.is_active ? (
            <Tag icon={<CheckCircleOutlined />} color="success">
              追更中
            </Tag>
          ) : (
            <Tag icon={<PauseCircleOutlined />} color="default">
              已暂停
            </Tag>
          )}
          {item.is_complete && (
            <Tag icon={<CheckCircleOutlined />} color="blue">
              已完结
            </Tag>
          )}
          <Tag>{item.output_format.toUpperCase()}</Tag>
          {item.auto_download && <Tag color="cyan">自动下载</Tag>}
        </Space>
      </Flex>

      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        {item.domain} &middot; 每 {item.check_interval_minutes} 分钟
        &middot; {item.last_known_chapters} 章
      </Typography.Text>

      {item.last_error && (
        <div style={{ marginTop: 4 }}>
          <Tooltip title={item.last_error}>
            <Tag icon={<ExclamationCircleOutlined />} color="error">
              错误：{item.last_error.slice(0, 60)}
              {item.last_error.length > 60 ? '...' : ''}
            </Tag>
          </Tooltip>
        </div>
      )}

      <Flex
        justify="space-between"
        align="center"
        style={{ marginTop: 8 }}
        wrap
        gap="small"
      >
        <Space size={0} split={<span style={{ color: 'var(--br-muted)', margin: '0 6px' }}>&middot;</span>}>
          {item.last_checked_at && (
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              <ClockCircleOutlined /> 检查于{' '}
              {formatFromNow(item.last_checked_at)}
            </Typography.Text>
          )}
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            <SyncOutlined /> 添加于 {formatFromNow(item.created_at)}
          </Typography.Text>
        </Space>

        <Space size="small">
          <Tooltip title="立即检查">
            <Button
              aria-label="立即检查追更小说"
              size="small"
              icon={<ReloadOutlined spin={checking} />}
              onClick={handleForceCheck}
              loading={checking}
            />
          </Tooltip>
          <Tooltip title={item.is_active ? '暂停追更' : '恢复追更'}>
            <Button
              aria-label={item.is_active ? '暂停追更' : '恢复追更'}
              size="small"
              icon={
                item.is_active ? (
                  <PauseCircleOutlined />
                ) : (
                  <PlayCircleOutlined />
                )
              }
              onClick={handleToggleActive}
            />
          </Tooltip>
          <Popconfirm
            title="停止追更这本小说？"
            onConfirm={handleDelete}
            okText="停止追更"
            okType="danger"
            cancelText="取消"
          >
            <Tooltip title="停止追更">
              <Button
                aria-label="停止追更"
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      </Flex>
    </Card>
  );
};
