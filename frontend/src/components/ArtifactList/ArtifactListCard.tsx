import { type Artifact } from '@/types';
import { Card, Empty, List } from 'antd';
import { ArtifactListItemCard } from './ArtifactListItemCard';
import { MakeArtifactButton } from './MakeArtifactButton';

export const ArtifactListCard: React.FC<{
  artifacts: Artifact[];
  novelId?: string;
  showMakeButton?: boolean;
}> = ({ novelId, artifacts, showMakeButton }) => {
  return (
    <Card
      title="导出文件"
      variant="outlined"
      styles={{
        title: { fontSize: 20 },
        body: { paddingTop: 5, paddingBottom: 5 },
      }}
      extra={
        showMakeButton && novelId ? (
          <MakeArtifactButton novelId={novelId} />
        ) : undefined
      }
    >
      {artifacts && artifacts.length > 0 ? (
        <List
          dataSource={artifacts}
          renderItem={(item) => <ArtifactListItemCard artifact={item} />}
        />
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无导出文件"
        />
      )}
    </Card>
  );
};
