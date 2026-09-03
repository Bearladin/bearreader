import { JobStatus, JobType, type Job } from '@/types';

export type SearchOutcomeKind =
  | 'running'
  | 'found'
  | 'found-partial'
  | 'not-found'
  | 'not-found-partial'
  | 'failed';

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
  const sourceFailed = sources.filter(
    (source) => source.state === 'failed' || source.state === 'partial'
  ).length;
  return classify(
    job,
    resultCount,
    sourceTotal,
    sourceCompleted,
    sourceFailed
  );
}

function classify(
  job: Job,
  resultCount: number,
  sourceTotal: number,
  sourceCompleted: number,
  sourceFailed: number
): SearchOutcome {
  let kind: SearchOutcomeKind;
  if (!job.is_done) {
    kind = 'running';
  } else if (
    job.status === JobStatus.FAILED ||
    (sourceTotal > 0 && sourceFailed >= sourceTotal)
  ) {
    kind = 'failed';
  } else if (resultCount > 0) {
    kind =
      job.status === JobStatus.PARTIAL || sourceFailed > 0
        ? 'found-partial'
        : 'found';
  } else {
    kind =
      job.status === JobStatus.PARTIAL || sourceFailed > 0
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
