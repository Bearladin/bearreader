import { stringifyError } from '@/utils/errors';
import {
  NOVEL_SORT_LABELS,
  NovelSort,
} from '@/types';
import { Flex, Input, message, Select } from 'antd';
import axios from 'axios';
import { useEffect, useMemo, useState } from 'react';
import { type NovelListHook } from './hooks';

export const NovelFilterBox: React.FC<
  Pick<NovelListHook, 'search' | 'domain' | 'sort' | 'updateParams'>
> = ({
  search: initialSearch,
  domain: initialDomain,
  sort: initialSort,
  updateParams,
}) => {
  const [loading, setLoading] = useState(false);
  const [domains, setDomains] = useState<Record<string, number>>({});

  useEffect(() => {
    const loadSources = async () => {
      try {
        setLoading(true);
        const { data } = await axios.get<Record<string, number>>(
          '/api/novel/domains'
        );
        setDomains(data);
      } catch (err) {
        message.error(stringifyError(err, '加载书源失败，请稍后重试。'));
      } finally {
        setLoading(false);
      }
    };
    loadSources();
  }, []);

  const sourceOptions = useMemo(() => {
    return Object.keys(domains)
      .sort()
      .map((domain) => {
        const count = domains[domain];
        return {
          value: domain,
          label: count > 0 ? `${domain} (${count})` : domain,
        };
      });
  }, [domains]);

  return (
    <Flex align="center" justify="space-between" gap="8px" wrap>
      {/* Sort Select */}
      <Select
        value={(initialSort || 'updated') as NovelSort}
        onChange={(value: NovelSort) => updateParams({ sort: value, page: 1 })}
        options={Object.entries(NOVEL_SORT_LABELS).map(([value, label]) => ({
          value: value as NovelSort,
          label,
        }))}
        style={{ width: 140 }}
        size="large"
        aria-label="排序方式"
      />

      {/* Domain Select */}
      <Select
        virtual={false}
        loading={loading}
        defaultValue={initialDomain || undefined}
        onChange={(value: string) =>
          updateParams({ domain: value || '', page: 1 })
        }
        placeholder="选择网站域名"
        allowClear
        size="large"
        options={sourceOptions}
        style={{ flex: 1, minWidth: 250 }}
      />

      {/* Search Input */}
      <Input.Search
        defaultValue={initialSearch}
        onSearch={(search) => updateParams({ search, page: 1 })}
        placeholder="搜索小说"
        allowClear
        size="large"
        style={{ flex: 3, minWidth: 300 }}
      />
    </Flex>
  );
};
