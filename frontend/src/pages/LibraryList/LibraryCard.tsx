import type { Library } from '@/types';
import { BookOutlined } from '@ant-design/icons';
import { Card, Col, Flex, Space, Typography } from 'antd';
import type React from 'react';
import { useNavigate } from 'react-router-dom';

export const LibraryCard: React.FC<{ library: Library }> = ({ library }) => {
  const navigate = useNavigate();

  return (
    <Col key={library.id} xs={24} sm={12} md={24} lg={12} xl={8}>
      <Card
        hoverable
        onClick={() => navigate(`/library/${library.id}`)}
        style={{
          height: '100%',
          overflow: 'hidden',
          position: 'relative',
        }}
        styles={{
          body: {
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            padding: '16px 24px',
          },
        }}
      >
        {/* Header */}
        <Flex
          justify="space-between"
          align="flex-start"
          style={{ marginBottom: 12 }}
        >
          <Space align="center" style={{ flex: 1 }}>
            <BookOutlined style={{ fontSize: 20, color: 'var(--br-secondary)' }} />
            <Typography.Title className="br-serif" level={5} style={{ margin: 0 }} ellipsis>
              {library.name}
            </Typography.Title>
          </Space>
        </Flex>

        {/* Description */}
        <Typography.Paragraph
          ellipsis={{ rows: 3 }}
          type="secondary"
          style={{ fontSize: 13, flex: 1 }}
        >
          {library.description || '暂无描述'}
        </Typography.Paragraph>

        {/* Footer */}
        <Flex
          align="center"
          justify="flex-end"
          wrap="wrap"
          style={{
            marginTop: 8,
            paddingTop: 8,
            borderTop: '1px solid var(--br-border)',
          }}
        >
          <Space size="small">
            <BookOutlined style={{ fontSize: 14 }} />
            <Typography.Text strong style={{ fontSize: 14 }}>
              {library.extra.novel_count || 0} 本小说
            </Typography.Text>
          </Space>
        </Flex>
      </Card>
    </Col>
  );
};
