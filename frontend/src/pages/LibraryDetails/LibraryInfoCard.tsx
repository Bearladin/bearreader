import { Auth } from '@/store/_auth';
import type { Library } from '@/types';
import { BookOutlined } from '@ant-design/icons';
import { Card, Divider, Flex, Grid, Typography } from 'antd';
import { useSelector } from 'react-redux';
import { DeleteLibraryButton } from './DeleteLibraryButton';
import { EditLibraryButton } from './EditLibraryButton';

interface LibraryInfoCardProps {
  library: Library;
  isOwner: boolean;
  onLibraryUpdated?: (updatedLibrary: Library) => void;
}

export const LibraryInfoCard: React.FC<LibraryInfoCardProps> = ({
  library,
  isOwner,
  onLibraryUpdated,
}) => {
  const { lg } = Grid.useBreakpoint();
  const isAdmin = useSelector(Auth.select.isAdmin);

  return (
    <Card
      style={{
        position: 'relative',
        overflow: 'hidden',
        background: 'var(--br-surface)',
        borderColor: 'var(--br-border-strong)',
      }}
      styles={{
        body: {
          display: 'flex',
          position: 'relative',
          alignItems: 'flex-start',
          gap: lg ? 16 : 8,
          padding: lg ? 16 : 8,
          flexWrap: lg ? 'nowrap' : 'wrap',
          justifyContent: lg ? 'space-between' : 'center',
        },
      }}
    >
      {/* Cover Image */}
      <BookOutlined
        style={{
          fontSize: 48,
          marginTop: 6,
          color: 'var(--br-secondary)',
        }}
      />

      {/* Content */}
      <Flex vertical justify="center" style={{ width: '100%' }}>
        <Typography.Title
          level={3}
          className="br-serif"
          style={{ margin: 0, textAlign: lg ? 'left' : 'center' }}
        >
          {library.name || '书架'}
        </Typography.Title>

        {/* 管理员登录模式下隐藏所有者名称显示 */}

        {library.description ? (
          <>
            {!lg && <Divider size="small" />}
            {library.description.split('\n\n').map((line, index) => (
              <Typography.Text
                key={index}
                style={{
                  margin: '4px 0',
                  display: 'block',
                }}
              >
                {line}
              </Typography.Text>
            ))}
          </>
        ) : null}
      </Flex>

      {!lg && <Divider size="small" />}

      {/* Owner Controls */}
      {(isOwner || isAdmin) && (
        <Flex
          vertical
          gap={7}
          style={{ width: 300 }}
          align={lg ? 'flex-end' : 'center'}
        >
          <Flex gap={4} align="center" wrap justify={lg ? 'end' : 'center'}>
            <EditLibraryButton library={library} onSuccess={onLibraryUpdated} />
            <DeleteLibraryButton library={library} />
          </Flex>
        </Flex>
      )}
    </Card>
  );
};
