import type { LibraryItem } from '@/types';
import { BookOutlined } from '@ant-design/icons';
import { Card, Flex, Tag, Typography } from 'antd';

export const LibraryItemCard: React.FC<{
  library: LibraryItem;
  onClick: () => void;
}> = ({ library, onClick }) => {
  return (
    <Card
      hoverable
      size="small"
      onClick={onClick}
      style={{ width: '100%', marginBottom: 2 }}
      styles={{ body: { padding: '8px 12px' } }}
    >
      <Flex gap={12} align="flex-start">
        <BookOutlined
          style={{
            color: 'var(--br-secondary)',
            fontSize: 16,
            marginTop: 2,
          }}
        />

        <Flex vertical style={{ flex: 1, minWidth: 0 }}>
          <Flex wrap gap={8} align="center" justify="space-between">
            <Typography.Text strong>{library.name}</Typography.Text>

            {library.is_public ? (
              <Tag bordered={false}>公开</Tag>
            ) : (
              <Tag bordered={false}>私有</Tag>
            )}
          </Flex>

          {library.description && (
            <Typography.Text type="secondary" ellipsis style={{ fontSize: 12 }}>
              {library.description}
            </Typography.Text>
          )}
        </Flex>
      </Flex>
    </Card>
  );
};
