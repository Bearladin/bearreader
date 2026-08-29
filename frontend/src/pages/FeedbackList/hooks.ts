import type { Feedback, Paginated } from '@/types';
import { stringifyError } from '@/utils/errors';
import axios from 'axios';
import { debounce } from 'lodash';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FeedbackStatus, FeedbackType } from '@/types';

interface SearchParams {
  page?: number;
  search?: string;
  status?: FeedbackStatus;
  type?: FeedbackType;
}

export function useFeedbackList() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [refreshId, setRefreshId] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const [total, setTotal] = useState(0);
  const [feedbackList, setFeedbackList] = useState<Feedback[]>([]);

  const search = useMemo(
    () => searchParams.get('search') || '',
    [searchParams]
  );

  const status = useMemo(() => {
    const value = parseInt(searchParams.get('status') || '-1', 10);
    if (Object.values(FeedbackStatus).includes(value)) {
      return value as FeedbackStatus;
    }
    return undefined;
  }, [searchParams]);

  const type = useMemo(() => {
    const value = parseInt(searchParams.get('type') || '-1', 10);
    if (Object.values(FeedbackType).includes(value)) {
      return value as FeedbackType;
    }
    return undefined;
  }, [searchParams]);

  const perPage = 25;
  const currentPage = useMemo(
    () => parseInt(searchParams.get('page') || '1', 10),
    [searchParams]
  );

  const fetchFeedback = async (
    search: string,
    page: number,
    limit: number,
    status?: FeedbackStatus,
    type?: FeedbackType
  ) => {
    setError(undefined);
    try {
      const offset = (page - 1) * limit;
      const { data } = await axios.get<Paginated<Feedback>>('/api/feedbacks', {
        params: { search, offset, limit, status, type },
      });
      setTotal(data.total);
      setFeedbackList(data.items);
    } catch (err: any) {
      setError(stringifyError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const tid = setTimeout(() => {
      fetchFeedback(search, currentPage, perPage, status, type);
    }, 50);
    return () => clearTimeout(tid);
  }, [search, currentPage, status, type, refreshId]);

  const refresh = useCallback(() => {
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
        if (updates.status) {
          next.set('status', String(updates.status));
        } else if (typeof updates.status !== 'undefined') {
          next.delete('status');
        }
        if (updates.type) {
          next.set('type', String(updates.type));
        } else if (typeof updates.type !== 'undefined') {
          next.delete('type');
        }
        return next;
      });
    }, 100);
  }, [setSearchParams]);

  return {
    search,
    status,
    type,
    perPage,
    currentPage,
    feedbackList,
    total,
    loading,
    error,
    refresh,
    updateParams,
  };
}
