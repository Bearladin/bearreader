export const PRELOAD_RECOVERY_KEY = 'bearreader/preload-recovery';
export const PRELOAD_RECOVERY_STABLE_MS = 30_000;

export type PreloadRecoveryRecord = {
  state: 'reload-requested' | 'failed';
  attemptedAt: number;
  href: string;
};

type StorageLike = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>;

export type PreloadRecoveryOptions = {
  target: EventTarget;
  storage: StorageLike;
  href: () => string;
  now: () => number;
  reloadSilently: () => void;
  schedule: (callback: () => void, delayMs: number) => number;
  cancelSchedule: (id: number) => void;
};

const PRELOAD_ERROR_PATTERNS = [
  'Failed to fetch dynamically imported module',
  'Importing a module script failed',
  'Unable to preload CSS',
] as const;

function isRecord(value: unknown): value is PreloadRecoveryRecord {
  if (!value || typeof value !== 'object') return false;
  const record = value as Record<string, unknown>;
  return (
    (record.state === 'reload-requested' || record.state === 'failed') &&
    typeof record.attemptedAt === 'number' &&
    Number.isFinite(record.attemptedAt) &&
    typeof record.href === 'string'
  );
}

export function readPreloadRecovery(
  storage: StorageLike
): PreloadRecoveryRecord | undefined {
  try {
    const raw = storage.getItem(PRELOAD_RECOVERY_KEY);
    if (!raw) return undefined;
    const parsed: unknown = JSON.parse(raw);
    if (isRecord(parsed)) return parsed;
    storage.removeItem(PRELOAD_RECOVERY_KEY);
  } catch {
    // Storage can be disabled by policy. The safe fallback is no auto reload.
  }
  return undefined;
}

function writePreloadRecovery(
  storage: StorageLike,
  record: PreloadRecoveryRecord
): boolean {
  try {
    storage.setItem(PRELOAD_RECOVERY_KEY, JSON.stringify(record));
    return true;
  } catch {
    return false;
  }
}

function clearPreloadRecovery(storage: StorageLike): boolean {
  try {
    storage.removeItem(PRELOAD_RECOVERY_KEY);
    return true;
  } catch {
    return false;
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  if (error && typeof error === 'object' && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return '';
}

export function isPreloadRouteError(
  error: unknown,
  storage: StorageLike
): boolean {
  if (readPreloadRecovery(storage)?.state === 'failed') return true;
  const message = errorMessage(error);
  return PRELOAD_ERROR_PATTERNS.some((pattern) => message.includes(pattern));
}

export function installPreloadRecovery(
  options: PreloadRecoveryOptions
): () => void {
  const {
    target,
    storage,
    href,
    now,
    reloadSilently,
    schedule,
    cancelSchedule,
  } = options;
  let timer: number | undefined;

  const scheduleStableClear = () => {
    const record = readPreloadRecovery(storage);
    if (record?.state !== 'reload-requested') return;
    const elapsed = Math.max(0, now() - record.attemptedAt);
    const delay = Math.max(0, PRELOAD_RECOVERY_STABLE_MS - elapsed);
    timer = schedule(() => {
      const current = readPreloadRecovery(storage);
      if (
        current?.state === 'reload-requested' &&
        now() - current.attemptedAt >= PRELOAD_RECOVERY_STABLE_MS
      ) {
        clearPreloadRecovery(storage);
      }
    }, delay);
  };

  const onPreloadError = (event: Event) => {
    let record = readPreloadRecovery(storage);
    if (record?.state === 'failed') return;

    if (record?.state === 'reload-requested') {
      if (now() - record.attemptedAt <= PRELOAD_RECOVERY_STABLE_MS) {
        writePreloadRecovery(storage, { ...record, state: 'failed' });
        return;
      }
      if (!clearPreloadRecovery(storage)) return;
      record = undefined;
    }

    const requested: PreloadRecoveryRecord = {
      state: 'reload-requested',
      attemptedAt: now(),
      href: href(),
    };
    if (!writePreloadRecovery(storage, requested)) return;
    event.preventDefault();
    reloadSilently();
  };

  target.addEventListener('vite:preloadError', onPreloadError);
  scheduleStableClear();

  return () => {
    target.removeEventListener('vite:preloadError', onPreloadError);
    if (timer !== undefined) cancelSchedule(timer);
  };
}
