import { APP_NAME } from '@/config';
import { Flex, Typography } from 'antd';
import { useNavigate } from 'react-router-dom';

export const MobileLayoutHeader: React.FC<any> = () => {
  const navigate = useNavigate();
  return (
    <Flex
      align="center"
      justify="center"
      gap={9}
      onClick={() => navigate('/')}
      style={{
        minHeight: 52,
        cursor: 'pointer',
      }}
    >
      <img
        src="/icons/bear-24.png"
        width={24}
        height={24}
        alt="BearReader"
        draggable={false}
      />
      <Typography.Title className="br-serif" level={4} style={{ fontSize: 18, margin: 0 }}>
        {APP_NAME}
      </Typography.Title>
    </Flex>
  );
};
