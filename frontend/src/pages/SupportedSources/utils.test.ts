import type { SourceItem } from '@/types';
import { describe, expect, it } from 'vitest';
import type { SourceFilterState } from './SupportedSourceFilter';
import { URL_SOURCE_HINTS, filterAndSortSources } from './utils';

const filter: SourceFilterState = {
  search: '',
  features: {},
  sortBy: 'domain',
  sortOrder: 'asc',
};

const source = (domain: string): SourceItem => ({
  url: `https://${domain}/`,
  domain,
  version: 1,
  has_manga: false,
  has_mtl: false,
  language: 'zh',
  is_disabled: false,
  can_search: domain === 'mayiwsk.com' || domain === 'uukanshu.cc',
  can_login: false,
  total_commits: 1,
  contributors: [],
  total_novels: 0,
});

describe('supported source placement', () => {
  it('pins uukanshu.cc immediately below mayiwsk.com', () => {
    const domains = filterAndSortSources(
      [
        source('z.example'),
        source('nieba.net'),
        source('uukanshu.cc'),
        source('mayiwsk.com'),
        source('shuquta.com'),
        source('dushulai.com'),
      ],
      filter
    ).map((item) => item.domain);

    expect(domains.slice(0, 5)).toEqual([
      'mayiwsk.com',
      'uukanshu.cc',
      'dushulai.com',
      'shuquta.com',
      'nieba.net',
    ]);
  });

  it('shows only the searchable capability on uukanshu.cc', () => {
    expect(URL_SOURCE_HINTS).not.toContain('uukanshu.cc');
  });
});
