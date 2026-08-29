import type { Job } from '@/types';
import { formatDuration } from '@/utils/time';
import { HourglassFilled } from '@ant-design/icons';
import { Tag } from 'antd';
import { useEffect, useMemo, useState } from 'react';

interface ProgressEntry {
  time: number;
  done: number;
  total: number;
}

export const JobEtaTimeTag: React.FC<{ job: Job }> = ({ job }) => {
  const [entries, setEntries] = useState<ProgressEntry[]>([]);

  useEffect(() => {
    const v: ProgressEntry = {
      time: Date.now(),
      done: job.done,
      total: job.total,
    };
    queueMicrotask(() => {
      setEntries((p) => {
        if (p.length > 0) {
          const last = p[p.length - 1];
          if (last.total !== v.total) {
            return [v];
          }
          if (last.done === v.done) {
            last.time = Date.now();
            return [...p];
          }
        }
        return [v, ...p.slice(0, 500)];
      });
    });
  }, [job.done, job.total]);

  const eta = useMemo(() => {
    let sum = 0;
    let total = 0;
    const r = 1 - job.done / job.total;
    for (let i = 0; i < entries.length; ++i) {
      const a = entries[i];
      const ap = a.done / a.total;
      for (let j = i + 1; j < entries.length; ++j) {
        const b = entries[j];
        const bp = b.done / b.total;
        const dt = a.time - b.time;
        const dp = ap - bp;
        if (dp > 0) {
          sum += (r * dt) / dp;
          total++;
        }
      }
    }
    if (total > 0) {
      return sum / total;
    }
  }, [entries, job.done, job.total]);

  if (!job.is_running || !eta) {
    return null;
  }

  return (
    <Tag icon={<HourglassFilled />} color="default">
      <b>预计剩余时间：</b>
      {formatDuration(eta)}
    </Tag>
  );
};
