import { JobStatus, JobType, type Job } from '@/types';

export type SearchOutcomeKind =
  | 'running'
  | 'found'
  | 'found-partial'
  | 'not-found'
  | 'not-found-partial'
  | 'failed'
  | 'canceled';

export interface SearchOutcome {
  kind: SearchOutcomeKind;
  resultCount: number;
  sourceTotal: number;
  sourceCompleted: number;
  sourceFailed: number;
}

export function isSearchJob(job: Job): boolean {
  return (
    job.type === JobType.SEARCH_SOURCE ||
    job.type === JobType.SEARCH_ALL_SOURCES
  );
}

export function getSearchOutcome(job: Job): SearchOutcome {
  const resultCount = job.extra.search_results?.length ?? 0;
  if (job.type === JobType.SEARCH_SOURCE) {
    const sourceFailed = job.status === JobStatus.FAILED ? 1 : 0;
    const sourceCompleted = job.extra.search_completed ? 1 : 0;
    return classify(job, resultCount, 1, sourceCompleted, sourceFailed);
  }

  const sources = Object.values(job.extra.search_sources ?? {});
  const sourceTotal = job.extra.search_source_total ?? sources.length;
  const sourceCompleted = sources.filter(
    (source) => source.state === 'completed'
  ).length;
  // A partial source finished its own search; only hard failures count
  // toward sourceFailed here — the partial signal still flows through
  // job.status / sourcePartial below (CR-06).
  const sourceFailed = sources.filter(
    (source) => source.state === 'failed'
  ).length;
  const sourcePartial = sources.filter(
    (source) => source.state === 'partial'
  ).length;
  return classify(
    job,
    resultCount,
    sourceTotal,
    sourceCompleted,
    sourceFailed,
    sourcePartial
  );
}

function classify(
  job: Job,
  resultCount: number,
  sourceTotal: number,
  sourceCompleted: number,
  sourceFailed: number,
  sourcePartial = 0
): SearchOutcome {
  let kind: SearchOutcomeKind;
  if (!job.is_done) {
    kind = 'running';
  } else if (job.status === JobStatus.CANCELED) {
    // The user aborted — do not present this as "searched and found nothing"
    // (CR-06); results already collected, if any, are kept by the caller.
    kind = 'canceled';
  } else if (job.status === JobStatus.FAILED) {
    kind = 'failed';
  } else if (sourceTotal > 0 && sourceFailed >= sourceTotal) {
    // Every source hard-failed its request.
    kind = 'failed';
  } else if (resultCount > 0) {
    kind =
      job.status === JobStatus.PARTIAL ||
      sourceFailed > 0 ||
      sourcePartial > 0
        ? 'found-partial'
        : 'found';
  } else {
    kind =
      job.status === JobStatus.PARTIAL ||
      sourceFailed > 0 ||
      sourcePartial > 0
        ? 'not-found-partial'
        : 'not-found';
  }
  return {
    kind,
    resultCount,
    sourceTotal,
    sourceCompleted,
    sourceFailed,
  };
}
