import { JobStatus, JobType, type Job } from '@/types';
import { describe, expect, it } from 'vitest';
import { getSearchOutcome } from './searchOutcome';

function searchJob(overrides: Partial<Job> = {}): Job {
  return {
    id: 'job',
    user_id: 'user',
    type: JobType.SEARCH_ALL_SOURCES,
    priority: 1,
    status: JobStatus.SUCCESS,
    is_done: true,
    is_running: false,
    is_pending: false,
    done: 3,
    failed: 0,
    total: 3,
    progress: 100,
    created_at: 1,
    updated_at: 1,
    extra: {
      query: '测试小说',
      search_results: [],
      search_source_total: 2,
      search_sources: {
        'a.example': { state: 'completed', result_count: 0 },
        'b.example': { state: 'completed', result_count: 0 },
      },
    },
    ...overrides,
  };
}

describe('getSearchOutcome', () => {
  it('does not announce no results while a search is running', () => {
    expect(
      getSearchOutcome(
        searchJob({ status: JobStatus.RUNNING, is_done: false })
      ).kind
    ).toBe('running');
  });

  it('distinguishes a complete zero-result search', () => {
    expect(getSearchOutcome(searchJob()).kind).toBe('not-found');
  });

  it('marks zero results with one failed source as incomplete', () => {
    const job = searchJob({ status: JobStatus.PARTIAL, failed: 1 });
    job.extra.search_sources!['b.example'].state = 'failed';
    const outcome = getSearchOutcome(job);
    expect(outcome.kind).toBe('not-found-partial');
    expect(outcome.sourceFailed).toBe(1);
    expect(outcome.sourceTotal).toBe(2);
  });

  it('keeps found results while exposing a partial search', () => {
    const job = searchJob({ status: JobStatus.PARTIAL, failed: 1 });
    job.extra.search_results = [{ title: '测试小说', url: 'https://a.example/book' }];
    job.extra.search_sources!['b.example'].state = 'failed';
    expect(getSearchOutcome(job).kind).toBe('found-partial');
  });

  it('marks all searchable sources failing as failed', () => {
    const job = searchJob({ status: JobStatus.FAILED, failed: 3 });
    job.extra.search_sources!['a.example'].state = 'failed';
    job.extra.search_sources!['b.example'].state = 'failed';
    expect(getSearchOutcome(job).kind).toBe('failed');
  });
});
