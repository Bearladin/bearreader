import type { Job } from '@/types';
import { stringifyError } from '@/utils/errors';
import { DownloadOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Empty, List, Space, Typography } from 'antd';
import axios from 'axios';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getSearchOutcome } from './searchOutcome';

interface SearchResultItem {
  title: string;
  url: string;
  info?: string;
}

function getDomain(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}

export const SearchResultsCard: React.FC<{ job: Job }> = ({ job }) => {
  const navigate = useNavigate();
  const [error, setError] = useState<string>();
  const [submittingUrl, setSubmittingUrl] = useState<string>();

  const results = job.extra.search_results ?? [];
  const outcome = getSearchOutcome(job);
  const sourceSummary = outcome.sourceTotal > 0 && (
    <Typography.Text type="secondary">
      已完成 {outcome.sourceCompleted + outcome.sourceFailed} /{' '}
      {outcome.sourceTotal} 个书源
      {outcome.sourceFailed > 0 && `，其中 ${outcome.sourceFailed} 个失败`}
      。
    </Typography.Text>
  );

  if (outcome.kind === 'running') {
    return (
      <Card variant="outlined">
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          搜索结果
        </Typography.Title>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="正在搜索书源，请稍候…"
        />
      </Card>
    );
  }

  if (results.length === 0) {
    const messages = {
      'not-found': {
        type: 'info' as const,
        title: '未找到匹配的小说',
        description:
          '已完成全部支持书名搜索的书源搜索，但没有找到匹配结果。你也可以前往其他书源网站搜索这本书，复制小说目录页 URL 后提交下载。',
      },
      'not-found-partial': {
        type: 'warning' as const,
        title: '暂未找到匹配的小说',
        description:
          '部分书源搜索失败，本次搜索结果可能不完整。你也可以前往其他书源网站搜索这本书，复制小说目录页 URL 后提交下载。',
      },
      failed: {
        type: 'error' as const,
        title: '书名搜索失败',
        description:
          '支持书名搜索的书源本次均未能返回结果。你仍可以前往其他书源网站搜索这本书，复制小说目录页 URL 后提交下载。',
      },
      canceled: {
        type: 'info' as const,
        title: '搜索已取消',
        description:
          '本次搜索在完成前被取消。你可以重新执行搜索，或前往其他书源网站找到小说目录页 URL 后提交下载。',
      },
    };
    const message = messages[
      outcome.kind as
        | 'not-found'
        | 'not-found-partial'
        | 'failed'
        | 'canceled'
    ];
    return (
      <Card variant="outlined">
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          搜索结果
        </Typography.Title>
        <Alert
          showIcon
          type={message.type}
          title={message.title}
          description={
            <Space direction="vertical" size={4}>
              <Typography.Text>{message.description}</Typography.Text>
              {sourceSummary}
            </Space>
          }
          style={{ borderRadius: 2 }}
        />
      </Card>
    );
  }

  const fetchNovel = async (item: SearchResultItem) => {
    setError(undefined);
    setSubmittingUrl(item.url);
    try {
      const result = await axios.post<Job>(`/api/job/create/fetch-novels`, {
        urls: [item.url],
        full: true,
      });
      navigate(`/job/${result.data.id}`);
    } catch (err) {
      setError(stringifyError(err, '获取小说失败，请稍后重试。'));
    } finally {
      setSubmittingUrl(undefined);
    }
  };

  return (
    <Card variant="outlined">
      <Typography.Title level={3} style={{ marginTop: 0 }}>
        搜索结果
      </Typography.Title>

      <Typography.Paragraph type="secondary">
        找到 {outcome.resultCount} 个匹配结果。搜索只负责查找小说，点击「获取此小说」后才会下载并加入书库。
      </Typography.Paragraph>

      {outcome.kind === 'found-partial' && (
        <Alert
          type="warning"
          showIcon
          title="搜索结果可能不完整"
          description={
            <Space direction="vertical" size={4}>
              <Typography.Text>
                已显示找到的小说，但有部分书源搜索失败。
              </Typography.Text>
              {sourceSummary}
            </Space>
          }
          style={{ marginBottom: 15, borderRadius: 2 }}
        />
      )}

      {Boolean(error) && (
        <Alert
          type="warning"
          showIcon
          title={error}
          style={{ marginBottom: 15 }}
          closable={{ onClose: () => setError('') }}
        />
      )}

      <List
        dataSource={results}
        renderItem={(item) => (
          <List.Item
            actions={[
              <Button
                key="fetch"
                type="primary"
                size="small"
                icon={<DownloadOutlined />}
                loading={submittingUrl === item.url}
                onClick={() => fetchNovel(item)}
              >
                获取此小说
              </Button>,
            ]}
          >
            <List.Item.Meta
              title={item.title}
              description={
                <>
                  <Typography.Text type="secondary">
                    {getDomain(item.url)}
                  </Typography.Text>
                  {item.info && (
                    <Typography.Text type="secondary">
                      {' · '}
                      {item.info}
                    </Typography.Text>
                  )}
                </>
              }
            />
          </List.Item>
        )}
      />
    </Card>
  );
};
