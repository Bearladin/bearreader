export const UserRole = {
  USER: 'user',
  ADMIN: 'admin',
};
export type UserRole = (typeof UserRole)[keyof typeof UserRole];

export const UserTier = {
  BASIC: 0,
  PREMIUM: 1,
  VIP: 2,
};
export type UserTier = (typeof UserTier)[keyof typeof UserTier];

export const JobPriority = {
  LOW: 0,
  NORMAL: 1,
  HIGH: 2,
};
export type JobPriority = (typeof JobPriority)[keyof typeof JobPriority];

export const JobStatus = {
  PENDING: 0,
  RUNNING: 1,
  SUCCESS: 2,
  FAILED: 3,
  CANCELED: 4,
  PAUSED: 5,
};
export type JobStatus = (typeof JobStatus)[keyof typeof JobStatus];

export const JobType = {
  NOVEL: 0,
  NOVEL_BATCH: 1,
  FULL_NOVEL: 5,
  FULL_NOVEL_BATCH: 6,
  CHAPTER: 10,
  CHAPTER_BATCH: 11,
  VOLUME: 20,
  VOLUME_BATCH: 21,
  IMAGE: 30,
  IMAGE_BATCH: 31,
  ARTIFACT: 40,
  ARTIFACT_BATCH: 41,
  SEARCH_SOURCE: 50,
  SEARCH_ALL_SOURCES: 51,
  FETCH_MISSING: 60,
  FETCH_LATEST: 61,
  IMPORT_EPUB_ANALYZE: 70,
  IMPORT_EPUB_COMMIT: 71,
  IMPORT_TXT_ANALYZE: 72,
  IMPORT_TXT_COMMIT: 73,
  NOVEL_TRANSLATION: 2,
  NOVEL_TRANSLATION_BATCH: 3,
  FULL_NOVEL_TRANSLATION: 7,
  FULL_NOVEL_TRANSLATION_BATCH: 8,
  CHAPTER_TRANSLATION: 12,
  CHAPTER_TRANSLATION_BATCH: 13,
  VOLUME_TRANSLATION: 22,
  VOLUME_TRANSLATION_BATCH: 23,
};
export type JobType = (typeof JobType)[keyof typeof JobType];

export const OutputFormat = {
  json: 'json',
  epub: 'epub',
  text: 'txt',
  pdf: 'pdf',
  mobi: 'mobi',
  fb2: 'fb2',
  rtf: 'rtf',
  docx: 'docx',
  azw3: 'azw3',
  lit: 'lit',
  lrf: 'lrf',
  pdb: 'pdb',
  rb: 'rb',
  tcr: 'tcr',
};
export type OutputFormat = (typeof OutputFormat)[keyof typeof OutputFormat];

export const NovelSort = {
  popular: 'popular',
  updated: 'updated',
  created: 'created',
  chapters: 'chapters',
  title_asc: 'title_asc',
  title_desc: 'title_desc',
};
export type NovelSort = (typeof NovelSort)[keyof typeof NovelSort];

export const LibraryNovelSort = {
  updated: 'updated',
  created: 'created',
  chapters: 'chapters',
  title_asc: 'title_asc',
  title_desc: 'title_desc',
};
export type LibraryNovelSort =
  (typeof LibraryNovelSort)[keyof typeof LibraryNovelSort];

export const NOVEL_SORT_LABELS: Partial<Record<NovelSort, string>> = {
  popular: '人气最高',
  updated: '最近更新',
  created: '最近收录',
  chapters: '章节最多',
};

export const LIBRARY_SORT_LABELS: Record<LibraryNovelSort, string> = {
  updated: '最近更新',
  created: '最近收录',
  chapters: '章节最多',
  title_asc: '书名升序',
  title_desc: '书名降序',
};

export const FontFamily = {
  MicrosoftYaHei:
    '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif',
  XiaoXiongKai:
    '"XiaoXiong Reader Kai", "Microsoft YaHei", "PingFang SC", sans-serif',
  XiaoXiongSerif:
    '"XiaoXiong Reader Serif", "SimSun", "Songti SC", "Microsoft YaHei", serif',
};
export type FontFamily = (typeof FontFamily)[keyof typeof FontFamily];

export const ReaderTheme = {
  Dark: { background: '#121212', color: '#E0E0E0' },
  Black: { background: '#000000', color: '#FFFFFF' },
  White: { background: '#FFFFFF', color: '#000000' },
  Paper: { background: '#F5F2E7', color: '#2B2B2B' },
  Sepia: { background: '#FDF6E3', color: '#333333' },
  Coffee: { background: '#EAE7DC', color: '#2C2C2C' },
  Parchment: { background: '#FBEEC1', color: '#3C3C3C' },
};
export type ReaderTheme = (typeof ReaderTheme)[keyof typeof ReaderTheme];

export const NotificationItem = {
  JOB_RUNNING: 10,
  JOB_SUCCESS: 20,
  JOB_FAILURE: 30,
  JOB_CANCELED: 40,
  NOVEL_SUCCESS: 50,
  ARTIFACT_SUCCESS: 60,
};
export type NotificationItem =
  (typeof NotificationItem)[keyof typeof NotificationItem];

export const ReaderLayout = {
  horizontal: 'horizontal',
  vertical: 'vertical',
};
export type ReaderLayout = (typeof ReaderLayout)[keyof typeof ReaderLayout];

export const FeedbackType = {
  GENERAL: 0,
  ISSUE: 1,
  FEATURE: 2,
};
export type FeedbackType = (typeof FeedbackType)[keyof typeof FeedbackType];

export const FeedbackStatus = {
  PENDING: 0,
  ACCEPTED: 1,
  RESOLVED: 2,
};
export type FeedbackStatus =
  (typeof FeedbackStatus)[keyof typeof FeedbackStatus];

export const TextAlign = {
  left: 'left',
  center: 'center',
  right: 'right',
  justify: 'justify',
};
export type TextAlign = (typeof TextAlign)[keyof typeof TextAlign];
