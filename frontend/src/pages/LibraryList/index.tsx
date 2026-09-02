import { Flex, Typography } from 'antd';
import { useState } from 'react';
import { CreateLibraryButton } from './CreateLibraryButton';
import { LibraryList } from './LibraryList';

export const LibraryListPage: React.FC = () => {
  const [refresh, setRefresh] = useState(0);

  return (
    <div className="br-page-container">
      <Flex wrap align="end" justify="space-between" style={{ marginBottom: 24 }}>
        <div>
          <Typography.Text className="br-section-label">我的书架</Typography.Text>
          <Typography.Title level={2} className="br-page-title">书架</Typography.Title>
          <Typography.Text type="secondary">整理、收藏和管理你的小说</Typography.Text>
        </div>
        <CreateLibraryButton onSuccess={() => setRefresh((v) => v + 1)} />
      </Flex>
      <LibraryList type="my" refreshId={refresh} />
    </div>
  );
};
