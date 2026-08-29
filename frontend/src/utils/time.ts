import moment, { type MomentInput } from 'moment';

export function parseDate(value?: string | number): Date | undefined {
  try {
    if (!value) return undefined;
    return new Date(value);
  } catch {
    return undefined;
  }
}

export function formatDuration(delta: number): string {
  const hh = 3600 * 1000;
  const mm = 60 * 1000;
  const ss = 1000;

  let v;
  const result = [];
  delta = Math.floor(delta);
  if (delta >= hh) {
    v = Math.floor(delta / hh);
    result.push(`${v}时`);
    delta %= hh;
  }
  if (delta > mm) {
    v = Math.floor(delta / mm);
    result.push(`${v}分`);
    delta %= mm;
  }
  v = Math.round(delta / ss);
  result.push(`${v}秒`);
  return result.join(' ');
}

export function formatDifference(a: Date, b: Date): string {
  if (a < b) {
    return formatDuration(b.getTime() - a.getTime());
  } else {
    return formatDuration(a.getTime() - b.getTime());
  }
}

export function formatDate(value?: MomentInput) {
  return moment(value).format('YYYY/M/D HH:mm');
}

export function formatFromNow(value?: MomentInput) {
  return moment(value).fromNow();
}

export function calculateRemaining(started: number, progress: number): string {
  const remaining = 100 - progress;
  const delta = Date.now() - started;
  return formatDuration((remaining * delta) / progress);
}
