import { JobType, type Job, type Paginated } from '@/types';
import { stringifyError } from '@/utils/errors';
import axios from 'axios';
import { debounce } from 'lodash';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { JobStatusFilterParams, JobTypeFilterParams } from './constants';

interface SearchParams {
  page?: number;
  type?: JobType;
  status?: string;
}

export function useJobList(
  autoRefresh: boolean = true,
  customUserId?: string,
  parentJobId?: string
) {
  const [searchParams, setSearchParams] = useSearchParams();

  const [refreshId, setRefreshId] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();

  const [total, setTotal] = useState(0);
  const [jobs, setJobs] = useState<Job[]>([]);

  const perPage = 10;

  const currentPage = useMemo(
    () => parseInt(searchParams.get('page') || '1', 10),
    [searchParams]
  );

  const type: SearchParams['type'] = useMemo(() => {
    const value = parseInt(searchParams.get('type') || '-1', 10);
    if (Object.values(JobType).includes(value)) {
      return value as JobType;
    }
  }, [searchParams]);

  const status: SearchParams['status'] = useMemo(() => {
    const param = searchParams.get('status')?.toLowerCase();
    for (const item of JobStatusFilterParams) {
      if (item.value === param) {
        return param;
      }
    }
  }, [searchParams]);

  useEffect(() => {
    const fetchJobs = async () => {
      setError(undefined);
      try {
        const offset = (currentPage - 1) * perPage;
        const statusParams = JobStatusFilterParams.find(
          (v) => v.value === status
        )?.params;
        const { data } = await axios.get<Paginated<Job>>('/api/jobs', {
          params: {
            offset,
            limit: perPage,
            type,
            user_id: customUserId,
            parent_job_id: parentJobId,
            ...statusParams,
          },
        });
        setTotal(data.total);
        setJobs(data.items);
      } catch (err: any) {
        setError(stringifyError(err));
      } finally {
        setLoading(false);
      }
    };
    const tid = setTimeout(fetchJobs, 50);
    return () => clearTimeout(tid);
  }, [
    parentJobId,
    customUserId,
    currentPage,
    type,
    status,
    perPage,
    refreshId,
  ]);

  const hasIncompleteJobs = useMemo(() => {
    if (error) return false;
    for (const job of jobs) {
      if (!job.is_done) {
        return true;
      }
    }
    return false;
  }, [error, jobs]);

  useEffect(() => {
    // refresh if it has incomplete jobs
    // or auto refresh is on in the first page,
    if (hasIncompleteJobs || (autoRefresh && currentPage === 1)) {
      let stopped = false;
      let tid: ReturnType<typeof setTimeout>;
      const schedule = () => {
        if (stopped) return;
        // chained setTimeout: never overlaps with an in-flight request
        tid = setTimeout(() => {
          if (stopped) return;
          setRefreshId((v) => v + 1);
          schedule();
        }, 5000);
      };
      schedule();
      return () => {
        stopped = true;
        clearTimeout(tid);
      };
    }
  }, [autoRefresh, currentPage, hasIncompleteJobs]);

  const refresh = useCallback(() => {
    setLoading(true);
    setRefreshId((v) => v + 1);
  }, []);

  const updateParams: (updates: SearchParams) => any = useMemo(() => {
    return debounce((updates: SearchParams) => {
      setLoading(true);
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (typeof updates.page !== 'undefined') {
          if (updates.page && updates.page !== 1) {
            next.set('page', String(updates.page));
          } else {
            next.delete('page');
          }
        }
        if (typeof updates.type !== 'undefined') {
          if (
            typeof updates.type === 'number' &&
            updates.type !== JobTypeFilterParams[0].value
          ) {
            next.set('type', String(updates.type));
          } else {
            next.delete('type');
          }
        }
        if (typeof updates.status !== 'undefined') {
          if (
            updates.status &&
            updates.status !== JobStatusFilterParams[0].value &&
            JobStatusFilterParams.find((v) => v.value === updates.status)
          ) {
            next.set('status', updates.status);
          } else {
            next.delete('status');
          }
        }
        return next;
      });
    }, 100);
  }, [setSearchParams]);

  return {
    type,
    status,
    perPage,
    currentPage,
    jobs,
    total,
    loading,
    error,
    refresh,
    updateParams,
  };
}

export type JobListHook = ReturnType<typeof useJobList>;
