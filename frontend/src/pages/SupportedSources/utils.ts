import type { SourceItem } from '@/types';
import type { SourceFilterState } from './SupportedSourceFilter';

/**
 * Get the language label for a language code
 * @param lang - The language code
 * @returns The language label
 */
export function getLanguageLabel(lang?: string): string {
  if (!lang || lang.length !== 2) {
    return '不限';
  }
  const names = new Intl.DisplayNames(['zh-CN'], {
    type: 'language',
  });
  return names.of(lang) || '';
}

/**
 * 发行版置顶书源：支持书名搜索的书源永远放在第一个，
 * 其余新添加的（仅 URL 抓取）书源依次置顶排在后面。
 * 添加新书源时按此顺序追加域名（见 BUILD_AND_RELEASE.md「中文书源维护」）。
 */
const PINNED_DOMAINS = [
  'mayiwsk.com',
  'dushulai.com',
  'shuquta.com',
  'nieba.net',
];

/**
 * 仅支持 URL 抓取的书源：提示用户可到这些网站内搜索具体书并获取页面 URL。
 */
export const URL_SOURCE_HINTS = ['dushulai.com', 'shuquta.com', 'nieba.net'];

/**
 * Filter and sort sources based on the filter state
 * @param sources - The sources to filter and sort
 * @param filter - The filter state
 * @returns The filtered and sorted sources
 */
export function filterAndSortSources(
  sources: SourceItem[],
  filter: SourceFilterState
): SourceItem[] {
  const { language, search, features, sortBy, sortOrder } = filter;
  let data = [...sources];

  // Apply filters
  const searchLower = search?.trim().toLowerCase();
  if (language || searchLower || Object.values(features).some(Boolean)) {
    data = data.filter((src) => {
      if (language && src.language !== language) {
        return false;
      }
      if (searchLower && !src.domain.toLowerCase().includes(searchLower)) {
        return false;
      }
      if (features.has_manga && !src.has_manga) {
        return false;
      }
      if (features.has_mtl && !src.has_mtl) {
        return false;
      }
      if (features.can_search && !src.can_search) {
        return false;
      }
      if (features.can_login && !src.can_login) {
        return false;
      }
      return true;
    });
  }

  // Apply sorting
  if (sortBy) {
    data = [...data].sort((a, b) => {
      let comparison: number;

      switch (sortBy) {
        case 'domain':
          comparison = a.domain.localeCompare(b.domain);
          break;
        case 'total_novels':
          comparison = (a.total_novels ?? 0) - (b.total_novels ?? 0);
          break;
        case 'version':
          comparison = (a.version ?? 0) - (b.version ?? 0);
          break;
        default:
          return 0;
      }

      return sortOrder === 'desc' ? -comparison : comparison;
    });
  }

  // Pin the distribution's preferred sources to the top, in list order.
  const pinned: { src: SourceItem; idx: number }[] = [];
  const rest: SourceItem[] = [];
  for (const src of data) {
    const idx = PINNED_DOMAINS.indexOf(src.domain);
    if (idx >= 0) {
      pinned.push({ src, idx });
    } else {
      rest.push(src);
    }
  }
  pinned.sort((a, b) => a.idx - b.idx);
  return [...pinned.map((p) => p.src), ...rest];
}
