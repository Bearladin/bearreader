import { ErrorState } from '@/components/Loading/ErrorState';
import { LoadingState } from '@/components/Loading/LoadingState';
import type { Library, Paginated } from '@/types';
import { stringifyError } from '@/utils/errors';
import { Empty, Flex, Input, Pagination, Row } from 'antd';
import axios from 'axios';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { LibraryCard } from './LibraryCard';

const PAGE_SIZE = 18;

type SearchParams = {
  tab?: string;
  page?: number;
  query?: string;
};

export const LibraryList: React.FC<{
  refreshId?: number;
  type: 'public' | 'my' | 'all';
}> = ({ type, refreshId }) => {
  const [searchParams, setSearchParams] = useSearchParams();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [total, setTotal] = useState(0);
  const [libraries, setLibraries] = useState<Library[]>([]);
  const [searchValue, setSearchValue] = useState('');

  const page = useMemo(() => {
    return parseInt(searchParams.get('page') || '1', 10);
  }, [searchParams]);

  const query = useMemo(() => {
    return searchParams.get('query') || '';
  }, [searchParams]);

  useEffect(() => {
    setSearchValue(query);
  }, [query]);

  const updateParams = useCallback(
    (updates: SearchParams) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (updates.page && updates.page !== 1) {
          next.set('page', String(updates.page));
        } else if (typeof updates.page !== 'undefined') {
          next.delete('page');
        }
        if (updates.query) {
          next.set('query', String(updates.query));
        } else if (typeof updates.query !== 'undefined') {
          next.delete('query');
        }
        return next;
      });
    },
    [setSearchParams]
  );

  useEffect(() => {
    const loadLibraries = async () => {
      setLoading(true);
      setError(undefined);
      try {
        const offset = (page - 1) * PAGE_SIZE;
        const { data } = await axios.get<Paginated<Library>>(
          `/api/library/${type}`,
          {
            params: {
              query,
              offset,
              limit: PAGE_SIZE,
            },
          }
        );
        setLibraries(data.items);
        setTotal(data.total);
      } catch (err) {
        setError(stringifyError(err));
      } finally {
        setLoading(false);
      }
    };

    loadLibraries();
  }, [page, query, refreshId, type]);

  return (
    <Flex vertical gap={16}>
      <Input.Search
        size="large"
        allowClear
        value={searchValue}
        defaultValue={query}
        placeholder="搜索书架"
        onClear={() => updateParams({ query: '' })}
        onChange={(e) => setSearchValue(e.target.value)}
        onSearch={(value) => updateParams({ query: value })}
      />

      {loading ? (
        <LoadingState />
      ) : error ? (
        <ErrorState error={error} title="加载书架失败" />
      ) : !libraries.length ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无书架"
        />
      ) : (
        <Row gutter={[12, 12]}>
          {libraries.map((library) => (
            <LibraryCard key={library.id} library={library} />
          ))}
        </Row>
      )}

      <Pagination
        current={page}
        total={total}
        hideOnSinglePage
        pageSize={PAGE_SIZE}
        showSizeChanger={false}
        onChange={(page) => updateParams({ page })}
      />
    </Flex>
  );
};
