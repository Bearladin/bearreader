import { ReaderSettings } from '@/pages/SettingsPage/ReaderSettings';
import { Reader } from '@/store/_reader';
import { SettingOutlined } from '@ant-design/icons';
import { ConfigProvider, Drawer, Grid, Modal } from 'antd';
import { useState } from 'react';
import { useSelector } from 'react-redux';
import { getReaderOverlayTheme } from './readerTheme';

export const ReaderSettingsButton: React.FC<
  React.HTMLAttributes<HTMLDivElement>
> = (props) => {
  const { md } = Grid.useBreakpoint();
  const readerTheme = useSelector(Reader.select.theme);
  const [open, setOpen] = useState<boolean>(false);
  const showSettings = () => setOpen(true);

  return (
    <>
      <div
        {...props}
        aria-label={props['aria-label'] || '阅读设置'}
        role="button"
        tabIndex={0}
        onClick={(event) => {
          showSettings();
          event.currentTarget.blur();
        }}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            event.stopPropagation();
            showSettings();
          }
        }}
      >
        <SettingOutlined />
        {md && '设置'}
      </div>

      <ConfigProvider theme={getReaderOverlayTheme(readerTheme)}>
      {md ? (
        <Modal
          closable={{ 'aria-label': '关闭阅读设置窗口' }}
          centered
          width={600}
          open={open}
          footer={null}
          destroyOnHidden
          title="阅读设置"
          onCancel={() => setOpen(false)}
          styles={{
            mask: {
              background: readerTheme.background === '#121212' || readerTheme.background === '#000000'
                ? 'rgba(0, 0, 0, 0.56)'
                : 'rgba(23, 23, 23, 0.28)',
            },
            header: {
              paddingBottom: 10,
              background: 'transparent',
            },
          }}
        >
          <ReaderSettings />
        </Modal>
      ) : (
        <Drawer
          open={open}
          closable={false}
          placement="bottom"
          size={300}
          onClose={() => setOpen(false)}
          styles={{
            body: {
              padding: 5,
            },
          }}
        >
          <ReaderSettings />
        </Drawer>
      )}
      </ConfigProvider>
    </>
  );
};
