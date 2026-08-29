import { store } from '@/store';
import { Config } from '@/store/_config';
import type { SourceItem } from '@/types';
import { List } from 'antd';
import { useSelector } from 'react-redux';
import { SupportedSourceCard } from './SupportedSourceCard';

export const SupportedSourceList: React.FC<{
  sources: SourceItem[];
  disabled?: boolean;
}> = ({ sources, disabled }) => {
  const defaultPageSize = useSelector(Config.select.supportedSourcesPageSize);
  const updatePageSize = (pageSize: number) => {
    store.dispatch(Config.action.setSupportedSourcesPageSize(pageSize));
  };
  return (
    <>
      <List
        size="small"
        dataSource={sources}
        grid={{ gutter: 5, column: 1 }}
        renderItem={(source) => (
          <List.Item style={{ margin: 0, marginTop: 12, padding: 0 }}>
            <SupportedSourceCard source={source} disabled={disabled} />
          </List.Item>
        )}
        pagination={{
          defaultPageSize,
          hideOnSinglePage: true,
          showSizeChanger: true,
          pageSizeOptions: [8, 12, 16, 25, 50, 100],
          onChange: (_, pageSize) => updatePageSize(pageSize),
        }}
      />
    </>
  );
};
