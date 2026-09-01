import type { Novel } from '@/types';
import { getGradientForId } from '@/utils/gradients';
import { Typography } from 'antd';

export const ImportedCover: React.FC<{
  novel: Pick<Novel, 'id' | 'title' | 'authors'>;
  style?: React.CSSProperties;
}> = ({ novel, style }) => {
  return (
    <div
      aria-label="本地导入小说封面"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        overflow: 'hidden',
        padding: 18,
        textAlign: 'center',
        color: '#fff',
        background: getGradientForId(novel.id, 'dark'),
        ...style,
      }}
    >
      <Typography.Text
        ellipsis={{ tooltip: novel.title }}
        style={{
          maxWidth: '100%',
          color: 'inherit',
          fontFamily: 'var(--br-serif)',
          fontSize: '1.1rem',
          lineHeight: 1.5,
        }}
      >
        {novel.title || '未命名小说'}
      </Typography.Text>
      <Typography.Text
        ellipsis={{ tooltip: novel.authors || '作者未知' }}
        style={{
          maxWidth: '100%',
          color: 'rgba(255, 255, 255, 0.82)',
          fontSize: '0.8rem',
        }}
      >
        {novel.authors || '作者未知'}
      </Typography.Text>
      <Typography.Text
        style={{
          color: 'rgba(255, 255, 255, 0.68)',
          fontSize: '0.72rem',
        }}
      >
        本地导入
      </Typography.Text>
    </div>
  );
};
