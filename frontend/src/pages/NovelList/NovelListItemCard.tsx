import FallbackImage from '@/assets/no-image.svg';
import { Favicon } from '@/components/Favicon';
import { ImportedCover } from '@/components/ImportedCover';
import { API_BASE_URL } from '@/config';
import { Auth } from '@/store/_auth';
import type { Novel } from '@/types';
import { Card, Flex, Image, Space, Tag, Typography } from 'antd';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';

export const NovelListItemCard: React.FC<{ novel: Novel; view?: 'grid' | 'list' }> = ({
  novel,
  view = 'grid',
}) => {
  const navigate = useNavigate();
  const token = useSelector(Auth.select.authToken);

  if (view === 'list') {
    return (
      <Card
        hoverable
        onClick={() => navigate(`/novel/${novel.id}`)}
        styles={{ body: { padding: 12 } }}
        style={{ height: '100%', cursor: 'pointer', userSelect: 'none' }}
      >
        <Flex gap={16} align="center">
          {novel.extra.imported && !novel.cover_available ? (
            <ImportedCover
              novel={novel}
              style={{
                width: 64,
                height: 86,
                border: '1px solid var(--br-border)',
                flex: '0 0 auto',
                padding: 8,
              }}
            />
          ) : (
            <Image
              alt="小说封面"
              preview={false}
              src={`${API_BASE_URL}/static/${novel.cover_file}?token=${token}`}
              fallback={FallbackImage}
              width={64}
              height={86}
              style={{ objectFit: 'cover', border: '1px solid var(--br-border)' }}
            />
          )}
          <Flex vertical gap={5} style={{ minWidth: 0, flex: 1 }}>
            <Typography.Title level={5} className="br-serif" ellipsis style={{ margin: 0 }}>
              {novel.title || '未命名小说'}
            </Typography.Title>
            <Typography.Text type="secondary" ellipsis>
              {novel.authors || '作者未知'} · {novel.domain}
            </Typography.Text>
            <Typography.Paragraph
              type="secondary"
              ellipsis={{ rows: 1 }}
              style={{ margin: 0, fontSize: 13 }}
            >
              {novel.synopsis || '暂无简介'}
            </Typography.Paragraph>
            <Space size={5} wrap>
              <Tag bordered={false}>{novel.chapter_count || 0} 章</Tag>
              {novel.language && <Tag bordered={false}>{novel.language}</Tag>}
            </Space>
          </Flex>
        </Flex>
      </Card>
    );
  }

  return (
    <Card
      hoverable
      style={{
        height: '100%',
        overflow: 'hidden',
        position: 'relative',
        userSelect: 'none',
        background: 'var(--br-surface)',
      }}
      onClick={() => navigate(`/novel/${novel.id}`)}
      styles={{
        body: {
          padding: 0,
        },
      }}
    >
      {/* 用 padding-top 百分比固定 3:4 比例（比块级 div 上的
          aspect-ratio 更可靠——后者会被内部 inline-block 图片的
          自然高度撑开，导致横版/竖版/无封面卡片高度不一致） */}
      <div
        style={{
          position: 'relative',
          width: '100%',
          paddingTop: '133.333%',
          overflow: 'hidden',
        }}
      >
        {novel.extra.imported && !novel.cover_available ? (
          <ImportedCover
            novel={novel}
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
            }}
          />
        ) : (
          <>
            <Image
              alt="小说封面"
              preview={false}
              src={`${API_BASE_URL}/static/${novel.cover_file}?token=${token}`}
              fallback={FallbackImage}
              fetchPriority="low"
              style={{
                objectFit: 'cover',
                height: '100%',
                width: '100%',
              }}
              styles={{
                root: {
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                },
              }}
            />
            {!novel.extra.imported && (
              <Favicon
                size="small"
                url={novel.url}
                style={{
                  position: 'absolute',
                  top: 3,
                  left: 5,
                  backdropFilter: 'blur(10px)',
                }}
              />
            )}
          </>
        )}
      </div>
      <div
        style={{
          // 标题区固定 56px（8px 上下内边距 + 两行 20px 行高），
          // 单行/两行/无标题的卡片在网格内保持等高
          height: 56,
          overflow: 'hidden',
        }}
      >
        {novel.title && novel.title !== '...' && (
          <Typography.Paragraph
            strong
            ellipsis={{ rows: 2 }}
            style={{
              margin: 0,
              padding: '8px 10px',
              fontSize: '13px',
              lineHeight: '20px',
              color: 'var(--br-ink)',
              fontFamily: 'var(--br-serif)',
            }}
          >
            {novel.title}
          </Typography.Paragraph>
        )}
      </div>
    </Card>
  );
};
