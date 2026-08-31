import { ErrorState } from '@/components/Loading/ErrorState';
import { LoadingState } from '@/components/Loading/LoadingState';
import type { SourceItem } from '@/types';
import { Divider, Empty, Flex, Grid, Tabs, Typography } from 'antd';
import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useSupportedSources } from './hooks';
import { SupportedSourceFilter } from './SupportedSourceFilter';
import { SupportedSourceList } from './SupportedSourceList';
import { filterAndSortSources } from './utils';

export const SupportedSourcesPage: React.FC<any> = () => {
  const { sm } = Grid.useBreakpoint();
  const [searchParams, setSearchParams] = useSearchParams();

  const { data, loading, error, refresh } = useSupportedSources();

  const [filteredSources, setFilteredSources] = useState<SourceItem[]>([]);

  const tabKey = useMemo(
    () => searchParams.get('tab') || 'active',
    [searchParams]
  );
  const setTabKey = (tab: string) => {
    setSearchParams({ tab });
  };

  const [activeSources, usedSources] = useMemo(() => {
    const active = [];
    const used = [];
    for (const src of filteredSources) {
      if (!src.is_disabled) {
        active.push(src);
      }
      if (src.total_novels > 0) {
        used.push(src);
      }
    }
    return [active, used];
  }, [filteredSources]);

  const currentSources = useMemo(
    () =>
      ({
        active: activeSources,
        used: usedSources,
      }[tabKey]),
    [activeSources, usedSources, tabKey]
  );

  return (
    <div className="br-page-container">
      <Flex align="baseline" justify="space-between" gap="8px" wrap>
        <div>
          <Typography.Text className="br-section-label">书源目录</Typography.Text>
          <Typography.Title level={2} className="br-page-title">支持的书源</Typography.Title>
        </div>
      </Flex>

      <Divider size="small" />

      <SupportedSourceFilter
        onChange={(f) => setFilteredSources(filterAndSortSources(data, f))}
      />

      <Flex align="center" style={{ marginTop: 10 }}>
        <Tabs
          activeKey={tabKey}
          onChange={setTabKey}
          style={{ flex: 1 }}
          items={[
            {
              key: 'active',
              label: sm ? '可用书源' : '可用',
            },
            {
              key: 'used',
              label: sm ? '使用中的书源' : '使用中',
            },
          ]}
        />
        {currentSources?.length ? (
          <Typography.Text
            type="secondary"
            style={{
              flex: 1,
              fontSize: 14,
              marginLeft: 10,
              textAlign: 'right',
              whiteSpace: 'nowrap',
            }}
          >
            {currentSources?.length} 项
          </Typography.Text>
        ) : null}
      </Flex>

      <Divider size="small" style={{ marginTop: 4 }} />

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState
          error={error}
          title="书源加载失败"
          onRetry={refresh}
        />
      ) : !currentSources?.length ? (
        <Empty
          description="暂无书源"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <SupportedSourceList
          sources={currentSources}
          disabled={false}
        />
      )}
    </div>
  );
};
