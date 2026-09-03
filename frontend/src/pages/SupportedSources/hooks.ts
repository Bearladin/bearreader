import type { SourceItem } from '@/types';
import { stringifyError } from '@/utils/errors';
import axios from 'axios';
import { useCallback, useEffect, useState } from 'react';

export function supportedSourcesRequest(refreshId: number) {
  return {
    url: '/api/meta/supported-sources',
    config: {
      params: { refresh: refreshId },
      headers: { 'Cache-Control': 'no-cache' },
    },
  };
}

export function useSupportedSources() {
  const [refreshId, setRefreshId] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [data, setData] = useState<SourceItem[]>([]);

  useEffect(() => {
    const fetchNovelSources = async () => {
      try {
        const res = await axios.get<Record<string, number>>(
          '/api/novel/domains'
        );
        const novelSources = new Map(Object.entries(res.data));
        setData((prev) =>
          prev.map((source) => ({
            ...source,
            total_novels: novelSources.get(source.domain) ?? 0,
          }))
        );
      } catch (err) {
        console.error(stringifyError(err));
      }
    };

    const fetchSupportedSources = async () => {
      try {
        setError(undefined);
        const request = supportedSourcesRequest(refreshId);
        const res = await axios.get<SourceItem[]>(request.url, request.config);
        setData(res.data.sort((a, b) => a.domain.localeCompare(b.domain)));
        fetchNovelSources();
      } catch (err) {
        setError(stringifyError(err));
      } finally {
        setLoading(false);
      }
    };

    fetchSupportedSources();
  }, [refreshId]);

  const refresh = useCallback(() => {
    setRefreshId((v) => v + 1);
  }, []);

  return { data, loading, error, refresh };
}
