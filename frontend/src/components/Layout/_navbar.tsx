import {
  BookOutlined,
  CloseOutlined,
  DeploymentUnitOutlined,
  FileDoneOutlined,
  FolderOpenOutlined,
  MenuFoldOutlined,
} from '@ant-design/icons';
import { Button, Drawer, Flex } from 'antd';
import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { MainLayoutSidebar } from './_sidebar';

const NavbarButton: React.FC<{
  label: string;
  icon: React.ReactNode;
  active?: boolean;
  onClick: React.MouseEventHandler<HTMLDivElement>;
}> = ({ label, icon, active, onClick }) => {
  return (
    <Flex
      gap={0}
      vertical
      align="center"
      onClick={onClick}
      style={{
        flex: 1,
        cursor: 'pointer',
        userSelect: 'none',
        padding: '8px 16px',
        color: active ? 'var(--br-ink)' : 'var(--br-secondary)',
        background: active ? 'var(--br-selected)' : 'transparent',
        borderTop: active ? '2px solid var(--br-ink)' : '2px solid transparent',
      }}
    >
      <div style={{ fontSize: 18 }}>{icon}</div>
      <div style={{ fontSize: 11, fontWeight: 500, whiteSpace: 'nowrap' }}>
        {label}
      </div>
    </Flex>
  );
};

export const MobileNavbar: React.FC<{
  style?: React.CSSProperties;
}> = ({ style }) => {
  const navigate = useNavigate();
  const { pathname: currentPath } = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    queueMicrotask(() => setDrawerOpen(false));
  }, [currentPath]);

  const handleNavClick = (path: string) => {
    navigate(path);
  };

  return (
    <>
      <Flex
        gap={4}
        align="center"
        justify="space-between"
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 1000,
          padding: '0 5px',
          userSelect: 'none',
          background: 'var(--br-surface)',
          borderTop: '1px solid var(--br-border)',
          ...style,
        }}
      >
        <NavbarButton
          label="任务请求"
          icon={<DeploymentUnitOutlined />}
          active={currentPath === '/'}
          onClick={() => handleNavClick('/')}
        />
        <NavbarButton
          label="小说"
          icon={<BookOutlined />}
          active={currentPath === '/novels'}
          onClick={() => handleNavClick('/novels')}
        />
        <NavbarButton
          label="书架"
          icon={<FolderOpenOutlined />}
          active={currentPath === '/libraries'}
          onClick={() => handleNavClick('/libraries')}
        />
        <NavbarButton
          label="书源"
          icon={<FileDoneOutlined />}
          active={currentPath === '/meta/sources'}
          onClick={() => handleNavClick('/meta/sources')}
        />
        <NavbarButton
          label="更多"
          icon={<MenuFoldOutlined />}
          onClick={() => setDrawerOpen((v) => !v)}
        />
      </Flex>

      <Drawer
        open={drawerOpen}
        size={280}
        closable={false}
        placement="right"
        destroyOnHidden
        onClose={() => setDrawerOpen(false)}
        styles={{ body: { padding: 0 } }}
      >
        <MainLayoutSidebar fullWidth />
        <Button
          aria-label="关闭导航菜单"
          type="text"
          shape="circle"
          icon={<CloseOutlined />}
          onClick={() => setDrawerOpen(false)}
          style={{ position: 'absolute', top: 10, right: 10, zIndex: 5 }}
        />
      </Drawer>
    </>
  );
};
