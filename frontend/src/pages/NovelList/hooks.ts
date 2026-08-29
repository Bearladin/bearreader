import type { Novel, Paginated } from '@/types';
import { stringifyError } from '@/utils/errors';
import { Grid } from 'antd';
import axios from 'axios';
import { debounce } from 'lodash';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

interface SearchParams {
  page?: number;
  search?: string;
  domain?: string;
}

export function useNovelList() {
  const breakpoint = Grid.useBreakpoint();
  const [searchParams, setSearchParams] = useSearchParams();

  const [refreshId, setRefreshId] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const [total, setTotal] = useState(0);
  const [novels, setNovels] = useState<Novel[]>([]);

  const search = useMemo(
    () => searchParams.get('search') || '',
    [searchParams]
  );

  const domain = useMemo(
    () => searchParams.get('domain') || '',
    [searchParams]
  );

  const currentPage = useMemo(
    () => parseInt(searchParams.get('page') || '1', 10),
    [searchParams]
  );

  const perPage = useMemo(() => {
    // xs={8} lg={6} xl={4}
    if (breakpoint.xl) {
      return 48;
    } else if (breakpoint.lg) {
      return 32;
    } else {
      return 24;
    }
  }, [breakpoint.xl, breakpoint.lg]);

  const fetchNovels = async (
    search: string,
    domain: string,
    page: number,
    limit: number
  ) => {
    setError(undefined);
    try {
      const offset = (page - 1) * limit;
      const { data } = await axios.get<Paginated<Novel>>('/api/novels', {
        params: { search, offset, limit, domain },
      });
      setTotal(data.total);
      setNovels(data.items);
    } catch (err: any) {
      setError(stringifyError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const tid = setTimeout(() => {
      fetchNovels(search, domain, currentPage, perPage);
    }, 50);
    return () => clearTimeout(tid);
  }, [search, domain, currentPage, perPage, refreshId]);

  const refresh = useCallback(() => {
    setLoading(true);
    setRefreshId((v) => v + 1);
  }, []);

  const updateParams: (updates: SearchParams) => any = useMemo(() => {
    return debounce((updates: SearchParams) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (updates.page && updates.page !== 1) {
          next.set('page', String(updates.page));
        } else if (typeof updates.page !== 'undefined') {
          next.delete('page');
        }
        if (updates.search) {
          next.set('search', String(updates.search));
        } else if (typeof updates.search !== 'undefined') {
          next.delete('search');
        }
        if (updates.domain) {
          next.set('domain', String(updates.domain));
        } else if (typeof updates.domain !== 'undefined') {
          next.delete('domain');
        }
        return next;
      });
    }, 100);
  }, [setSearchParams]);

  return {
    search,
    perPage,
    currentPage,
    domain,
    novels,
    total,
    loading,
    error,
    refresh,
    updateParams,
  };
}

export type NovelListHook = ReturnType<typeof useNovelList>;
