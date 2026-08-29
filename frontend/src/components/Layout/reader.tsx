import { Grid, Layout } from 'antd';
import { throttle } from 'lodash';
import { useEffect, useRef, useState } from 'react';
import { Outlet } from 'react-router-dom';
import { MobileLayoutHeader } from './_header';
import { MobileNavbar } from './_navbar';
import { MainLayoutSidebar } from './_sidebar';

export const ReaderLayout: React.FC<any> = () => {
  const { md } = Grid.useBreakpoint();
  const previousPosition = useRef<number>(0);
  const [showNavbar, setShowNavbar] = useState(true);

  useEffect(() => {
    const handleScroll = throttle(() => {
      const position = Math.round(window.scrollY / 10);
      if (position > previousPosition.current) {
        setShowNavbar(false);
      } else if (position < previousPosition.current) {
        setShowNavbar(true);
      }
      previousPosition.current = position;
    }, 100);

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <Layout>
      {md && <MainLayoutSidebar style={{ position: 'sticky', top: 0 }} />}

      <Layout.Content style={{ padding: 0 }}>
        {!md && <MobileLayoutHeader />}

        <div
          style={{
            minHeight: 'calc(100% - 100px)',
            transition: 'all 0.2s ease-in-out',
          }}
        >
          <Outlet />
        </div>
      </Layout.Content>

      {!md && showNavbar && <MobileNavbar />}
    </Layout>
  );
};
