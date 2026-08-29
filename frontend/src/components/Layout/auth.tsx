import { APP_NAME } from '@/config';
import { Card, Flex, Layout, Space, Typography } from 'antd';
import { Outlet } from 'react-router-dom';

export const AuthLayout: React.FC<any> = () => {
  return (
    <Layout style={{ padding: '10px', height: '100vh' }}>
      <Layout.Content style={{ overflow: 'auto' }}>
        <Flex
          wrap
          align="center"
          justify="center"
          style={{ width: '100%', height: '100%' }}
        >
          <Card
            style={{ width: 'min(500px, 100%)', borderColor: 'var(--br-border-strong)' }}
            title={
              <Space
                align="center"
                vertical
                style={{ padding: '15px', width: '100%' }}
              >
                <img
                  src="/icons/bear-128.png"
                  width={96}
                  height={96}
                  alt="BearReader"
                  draggable={false}
                  style={{
                    display: 'block',
                  }}
                />
                <Typography.Title
                  level={3}
                  className="br-serif"
                  style={{ margin: 0, color: 'var(--br-ink)' }}
                >
                  {APP_NAME}
                </Typography.Title>
              </Space>
            }
          >
            <Outlet />
          </Card>
        </Flex>
      </Layout.Content>
    </Layout>
  );
};
