import type {
  FeedbackStatus,
  FeedbackType,
  JobPriority,
  JobStatus,
  JobType,
  NotificationItem,
  OutputFormat,
  UserRole,
  UserTier,
} from './enums';

export * from './enums';

interface _Base {
  id: string;
  created_at: number;
  updated_at: number;
  extra: Record<string, unknown>;
}

export interface User extends _Base {
  name: string;
  email: string;
  role: UserRole;
  tier: UserTier;
  is_active: boolean;
  is_verified: boolean;
  referrer_id?: string;

  extra: {
    email_alerts?: Record<NotificationItem, boolean>;
  };
}

export interface UserToken {
  user_id: string;
  token: string;
  expires_at: number;
}

export interface LoginResponse {
  user: User;
  token: string;
}

export interface Paginated<T> {
  total: number;
  offset: number;
  limit: number;
  items: T[];
}

export interface EpubImportSample {
  title: string;
  body_preview: string;
}

export interface EpubImportPreview {
  title: string;
  authors: string;
  language?: string;
  synopsis: string;
  tags: string[];
  chapters: number;
  volumes: number;
  cover_available: boolean;
  samples: EpubImportSample[];
}

export interface EpubImportStartResponse {
  session_id?: string;
  job_id?: string;
  existing_novel_id?: string;
}

export interface EpubImportSession {
  id: string;
  status: string;
  original_name: string;
  file_size: number;
  expires_at: number;
  analyze_job_id?: string;
  commit_job_id?: string;
  novel_id?: string;
  job_status?: JobStatus;
  progress: number;
  phase?: string;
  error?: string;
  preview?: EpubImportPreview;
}

export interface Job extends _Base {
  parent_job_id?: string;

  user_id: string;
  type: JobType;
  priority: JobPriority;

  status: JobStatus;
  is_done: boolean;
  is_running: boolean;
  is_pending: boolean;

  error?: string;
  started_at?: number;
  finished_at?: number;

  done: number;
  failed: number;
  total: number;
  progress: number;
  job_title?: string;

  extra: {
    url?: string;
    urls?: string[];
    novel_id?: string;
    volume_id?: string;
    volume_ids?: string[];
    chapter_id?: string;
    chapter_ids?: string[];
    image_id?: string;
    image_ids?: string[];
    format?: OutputFormat;
    formats?: OutputFormat[];
    novel_title?: string;
    volume_serial?: string;
    chapter_serial?: string;
    artifact_id?: string;
    query?: string;
    domain?: string;
    failure_kind?: string;
    failure_detail?: string;
    failure_url?: string;
    status_code?: number | null;
    is_permanent?: boolean;
    blocking_layer?: number | null;
    blocking_layer_name?: string | null;
    reads?: string | null;
    stance?: string | null;
    search_results?: {
      title: string;
      url: string;
      info?: string;
    }[];
    import_session_id?: string;
    original_name?: string;
    authors?: string;
    phase?: string;
  };
}

export interface Novel extends _Base {
  url: string;
  domain: string;

  title: string;
  crawled: boolean;
  authors: string;
  synopsis: string;
  tags: string[];
  manga: boolean;
  mtl: boolean;
  language: string;
  rtl: boolean;
  volume_count: number;
  chapter_count: number;

  cover_url: string;
  cover_file: string;
  cover_available: boolean;

  extra: {
    crawler_version?: number;
    imported?: boolean;
    source_format?: string;
    original_name?: string;
    file_sha256?: string;
  };
}

export interface Library extends _Base {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  is_public: boolean;

  extra: {
    owner_name?: string;
    novel_count?: number;
  };
}

export interface LibraryItem {
  id: string;
  name: string;
  description?: string;
  is_public: boolean;
}

export interface Chapter extends _Base {
  novel_id: string;
  volume_id: string;
  url: string;
  title: string;
  serial: number;

  is_done: boolean;
  is_available: boolean;
  content_file: string;

  extra: {
    crawler_version?: number;
    imported?: boolean;
    source_format?: string;
  };
}

export interface Volume extends _Base {
  id: string;
  novel_id: string;
  title: string;
  serial: number;
  chapter_count: number;
}

export interface Artifact extends _Base {
  format: OutputFormat;
  novel_id: string;
  job_id?: string;
  user_id?: string;
  is_zip: boolean;
  output_file: string;
  file_name: string;
  file_size?: number;
  is_available: boolean;
}

export interface SourceItem {
  url: string;
  domain: string;
  version: number;
  has_manga: boolean;
  has_mtl: boolean;
  language: string;
  is_disabled: boolean;
  disable_reason?: string;
  can_search: boolean;
  can_login: boolean;
  total_commits: number;
  contributors: string[];
  total_novels: number;
}

export interface ReadHistory extends Record<string, boolean> {}

export interface ReadChapter {
  novel: Novel;
  chapter: Chapter;
  content?: string;
  next_id?: string;
  previous_id?: string;
}

export interface TrackedNovel extends _Base {
  user_id: string;
  novel_id?: string;
  novel_url: string;
  title: string;
  domain: string;
  last_known_chapters: number;
  last_checked_at?: number;
  is_active: boolean;
  is_complete: boolean;
  check_interval_minutes: number;
  auto_download: boolean;
  output_format: string;
  last_error?: string;
}

export interface Feedback extends _Base {
  user_id: string;
  type: FeedbackType;
  status: FeedbackStatus;
  subject: string;
  message: string;
  admin_notes?: string;
  extra: {
    user_name?: string;
    job_id?: string;
    job_error?: string;
    novel_id?: string;
    chapter_id?: string;
  };
}
