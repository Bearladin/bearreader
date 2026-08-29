import { Divider, Grid, Layout } from 'antd';
import { Outlet } from 'react-router-dom';
import { MobileLayoutHeader } from './_header';
import { MobileNavbar } from './_navbar';
import { MainLayoutSidebar } from './_sidebar';

const PageContainer: React.FC<any> = () => {
  return (
    <div
      style={{
        width: '100%',
        maxWidth: 1480,
        margin: '0 auto',
      }}
    >
      <Outlet />
    </div>
  );
};

const MainLayoutDesktop: React.FC<any> = () => {
  const { xl } = Grid.useBreakpoint();
  return (
    <Layout>
      <MainLayoutSidebar
        width={xl ? 240 : 216}
        style={{
          position: 'sticky',
          top: 0,
        }}
      />
      <Layout.Content
        style={{
          minHeight: '100vh',
          padding: '32px clamp(24px, 4vw, 64px) 64px',
          position: 'relative',
        }}
      >
        <PageContainer />
      </Layout.Content>
    </Layout>
  );
};

const MainLayoutMobile: React.FC<any> = () => {
  return (
    <Layout>
      <Layout.Content
        style={{
          minHeight: '100vh',
          position: 'relative',
          padding: '0 14px 96px',
        }}
      >
        <MobileLayoutHeader />
        <Divider size="small" style={{ margin: '0 0 18px' }} />
        <PageContainer />
      </Layout.Content>

      <MobileNavbar />
    </Layout>
  );
};

export const MainLayout: React.FC<any> = () => {
  const { lg: isDesktop } = Grid.useBreakpoint();
  if (isDesktop) {
    return <MainLayoutDesktop />;
  }
  return <MainLayoutMobile />;
};
