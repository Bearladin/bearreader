import {
  ClearOutlined,
  SearchOutlined,
  SortAscendingOutlined,
  SortDescendingOutlined,
} from '@ant-design/icons';
import { Button, Flex, Input, Select } from 'antd';
import { isEqual } from 'lodash';
import React, { useEffect, useState } from 'react';

type SortBy = 'domain' | 'total_novels' | 'version';
type SortOrder = 'asc' | 'desc';

export type SourceFilterState = {
  search: string;
  language?: string;
  features: {
    has_manga?: boolean;
    has_mtl?: boolean;
    can_search?: boolean;
    can_login?: boolean;
  };
  sortBy?: SortBy;
  sortOrder: SortOrder;
};

const defaultSourceFilters: SourceFilterState = {
  search: '',
  language: undefined,
  features: {},
  sortBy: 'version',
  sortOrder: 'desc',
};

const defaultSortOrder: Record<SortBy, SortOrder> = {
  domain: 'asc',
  total_novels: 'desc',
  version: 'desc',
};

export const SupportedSourceFilter: React.FC<{
  onChange: (f: SourceFilterState) => void;
}> = ({ onChange }) => {
  const [filter, setFilter] = useState(defaultSourceFilters);

  useEffect(() => {
    const timeout = setTimeout(() => {
      onChange(filter);
    }, 50);
    return () => clearTimeout(timeout);
  }, [filter, onChange]);

  const sortByOptions = [
    { value: 'domain', label: '域名' },
    { value: 'total_novels', label: '小说数量' },
    { value: 'version', label: '版本' },
  ];

  const toggleFeature = (feature: keyof SourceFilterState['features']) => {
    setFilter((prev) => ({
      ...prev,
      features: {
        ...prev.features,
        [feature]: !prev.features[feature],
      },
    }));
  };

  return (
    <Flex align="center" gap={5} wrap>
      {/* Search */}
      <Input
        allowClear
        prefix={<SearchOutlined />}
        placeholder="按域名搜索"
        value={filter.search}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
          setFilter({ ...filter, search: e.target.value })
        }
        style={{ flex: 2, minWidth: 250 }}
      />

      {/* Sort */}
      <Select
        virtual={false}
        placeholder="排序方式"
        options={sortByOptions}
        value={filter.sortBy}
        prefix={
          filter.sortOrder === 'asc' ? (
            <SortAscendingOutlined />
          ) : (
            <SortDescendingOutlined />
          )
        }
        onClear={() => {
          setFilter({
            ...filter,
            sortBy: 'version',
            sortOrder: 'desc',
          });
        }}
        onSelect={(value) => {
          if (filter.sortBy === value) {
            setFilter({
              ...filter,
              sortOrder: filter.sortOrder === 'asc' ? 'desc' : 'asc',
            });
          } else {
            setFilter({
              ...filter,
              sortBy: value,
              sortOrder: defaultSortOrder[value],
            });
          }
        }}
        allowClear={filter.sortBy !== 'version' || filter.sortOrder !== 'desc'}
        style={{ flex: 1, minWidth: 150 }}
      />

      {/* Searchable-source filter only */}
      <Button
        type={filter.features.can_search ? 'primary' : 'default'}
        onClick={() => toggleFeature('can_search')}
        icon={<SearchOutlined />}
      >
        支持书名搜索
      </Button>

      {/* Clear Filters */}
      {!isEqual(filter, defaultSourceFilters) && (
        <Button
          shape="round"
          icon={<ClearOutlined />}
          onClick={() => setFilter(defaultSourceFilters)}
          title="清除筛选条件"
          aria-label="清除筛选条件"
        />
      )}
    </Flex>
  );
};
