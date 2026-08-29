import type { Job } from '@/types';
import { stringifyError } from '@/utils/errors';
import { DownloadOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Empty, List, Typography } from 'antd';
import axios from 'axios';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

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

  const results = job.extra.search_results;
  if (!results || results.length === 0) {
    return (
      <Card variant="outlined">
        <Typography.Title level={3} style={{ marginTop: 0 }}>
          搜索结果
        </Typography.Title>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="没有匹配的搜索结果"
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
        系统已自动获取匹配小说的基本信息，也可以点击「获取此小说」下载全书内容。
      </Typography.Paragraph>

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
