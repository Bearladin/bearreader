import type { Paginated, TrackedNovel } from '@/types';
import { stringifyError } from '@/utils/errors';
import axios from 'axios';
import { debounce } from 'lodash';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

interface SearchParams {
  page?: number;
  is_active?: boolean;
}

export function useTrackedNovels() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [refreshId, setRefreshId] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<TrackedNovel[]>([]);

  const perPage = 25;
  const currentPage = useMemo(
    () => parseInt(searchParams.get('page') || '1', 10),
    [searchParams]
  );

  const isActive = useMemo(() => {
    const value = searchParams.get('is_active');
    if (value === 'true') return true;
    if (value === 'false') return false;
    return undefined;
  }, [searchParams]);

  useEffect(() => {
    const fetchData = async () => {
      setError(undefined);
      try {
        const offset = (currentPage - 1) * perPage;
        const { data } = await axios.get<Paginated<TrackedNovel>>(
          '/api/watchers',
          {
            params: { offset, limit: perPage, is_active: isActive },
          }
        );
        setTotal(data.total);
        setItems(data.items);
      } catch (err: any) {
        setError(stringifyError(err));
      } finally {
        setLoading(false);
      }
    };

    const tid = setTimeout(fetchData, 50);
    return () => clearTimeout(tid);
  }, [currentPage, isActive, refreshId]);

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
        if (typeof updates.is_active === 'boolean') {
          next.set('is_active', String(updates.is_active));
        } else if (typeof updates.is_active !== 'undefined') {
          next.delete('is_active');
        }
        return next;
      });
    }, 100);
  }, [setSearchParams]);

  return {
    items,
    loading,
    error,
    total,
    currentPage,
    perPage,
    isActive,
    refresh,
    updateParams,
  };
}
