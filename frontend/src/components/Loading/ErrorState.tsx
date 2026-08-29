import { copy } from '@/locales/zh-CN';
import { Button, Flex, Result } from 'antd';

export const ErrorState: React.FC<{
  title: string;
  error?: string;
  onRetry?: () => void;
}> = ({ title, error, onRetry }) => {
  return (
    <Flex align="center" justify="center" style={{ height: '100%' }}>
      <Result
        status="error"
        title={title}
        subTitle={error || '加载数据时发生错误。'}
        extra={
          onRetry ? (
            <Button key="retry" onClick={onRetry}>
              {copy.common.retry}
            </Button>
          ) : undefined
        }
      />
    </Flex>
  );
};
