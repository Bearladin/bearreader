import {
  BookOutlined,
  DeploymentUnitOutlined,
  FileDoneOutlined,
  FolderOpenOutlined,
  HistoryOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { Flex, Layout, Menu, Typography } from 'antd';
import { Link, useLocation } from 'react-router-dom';
import { APP_VERSION } from '@/version';
import { BrandBlock } from './BrandBlock';

function getClassName(currentPath: string, path: string): string | undefined {
  if (currentPath === path) {
    return 'ant-menu-item-selected';
  }
  return undefined;
}

export const MainLayoutSidebar: React.FC<{
  fullWidth?: boolean;
  width?: number;
  style?: React.CSSProperties;
}> = ({ fullWidth, width = 240, style }) => {
  const { pathname: currentPath } = useLocation();

  return (
    <Layout.Sider
      theme="light"
      collapsible={false}
      width={fullWidth ? '100%' : width}
      style={{
        ...style,
        height: fullWidth ? '100%' : '100vh',
        background: 'var(--br-surface)',
      }}
    >
      <Flex
        vertical
        style={{
          height: '100%',
          borderRight: '1px solid var(--br-border)',
        }}
      >
        <BrandBlock />
        <Menu
          key={currentPath}
          mode="inline"
          inlineIndent={15}
          subMenuOpenDelay={0}
          style={{
            flex: 1,
            overflow: 'auto',
            borderRight: 'none',
            userSelect: 'none',
            padding: '14px 10px',
            background: 'var(--br-surface)',
          }}
          items={[
            {
              type: 'group',
              key: 'workspace',
              label: '工作区',
            },
            {
              key: '/',
              icon: <DeploymentUnitOutlined />,
              className: getClassName(currentPath, '/'),
              label: <Link to="/">任务请求</Link>,
            },
            {
              key: '/novels',
              icon: <BookOutlined />,
              className: getClassName(currentPath, '/novels'),
              label: <Link to="/novels">小说</Link>,
            },
            {
              key: '/libraries',
              icon: <FolderOpenOutlined />,
              className: getClassName(currentPath, '/libraries'),
              label: <Link to="/libraries">书架</Link>,
            },
            {
              key: '/meta/sources',
              icon: <FileDoneOutlined />,
              className: getClassName(currentPath, '/meta/sources'),
              label: <Link to="/meta/sources">书源</Link>,
            },
            {
              type: 'group',
              key: 'help',
              label: '帮助与说明',
            },
            {
              key: '/changelog',
              icon: <HistoryOutlined />,
              className: getClassName(currentPath, '/changelog'),
              label: <Link to="/changelog">更新日志</Link>,
            },
            {
              key: '/tutorial',
              icon: <QuestionCircleOutlined />,
              className: getClassName(currentPath, '/tutorial'),
              label: <Link to="/tutorial">使用教程</Link>,
            },
          ]}
        />
        <Typography.Text
          type="secondary"
          style={{ padding: '14px 18px', borderTop: '1px solid var(--br-border)', fontSize: 12 }}
        >
          v{APP_VERSION} · 本地运行
        </Typography.Text>
      </Flex>
    </Layout.Sider>
  );
};
