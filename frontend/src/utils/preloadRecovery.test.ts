import { describe, expect, it, vi } from 'vitest';
import {
  installPreloadRecovery,
  isPreloadRouteError,
  PRELOAD_RECOVERY_KEY,
  PRELOAD_RECOVERY_STABLE_MS,
  readPreloadRecovery,
  type PreloadRecoveryRecord,
} from './preloadRecovery';

class MemoryStorage {
  private data = new Map<string, string>();

  getItem(key: string): string | null {
    return this.data.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.data.set(key, value);
  }

  removeItem(key: string): void {
    this.data.delete(key);
  }
}

function setup(record?: PreloadRecoveryRecord) {
  const target = new EventTarget();
  const storage = new MemoryStorage();
  if (record) {
    storage.setItem(PRELOAD_RECOVERY_KEY, JSON.stringify(record));
  }
  let now = 1_000;
  const reloadSilently = vi.fn();
  let callback: (() => void) | undefined;
  const cancelSchedule = vi.fn();
  const dispose = installPreloadRecovery({
    target,
    storage,
    href: () => 'http://localhost:31580/libraries',
    now: () => now,
    reloadSilently,
    schedule: (next) => {
      callback = next;
      return 7;
    },
    cancelSchedule,
  });
  return {
    target,
    storage,
    reloadSilently,
    cancelSchedule,
    dispose,
    advance(ms: number) {
      now += ms;
    },
    fireTimer() {
      callback?.();
    },
  };
}

describe('preload recovery', () => {
  it('reloads once and prevents the first preload error', () => {
    const context = setup();
    const event = new Event('vite:preloadError', { cancelable: true });
    context.target.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    expect(context.reloadSilently).toHaveBeenCalledOnce();
    expect(readPreloadRecovery(context.storage)?.state).toBe(
      'reload-requested'
    );
  });

  it('marks a recent second failure without reloading or preventing it', () => {
    const context = setup({
      state: 'reload-requested',
      attemptedAt: 1_000,
      href: 'http://localhost:31580/libraries',
    });
    const event = new Event('vite:preloadError', { cancelable: true });
    context.target.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(false);
    expect(context.reloadSilently).not.toHaveBeenCalled();
    expect(readPreloadRecovery(context.storage)?.state).toBe('failed');
  });

  it('never automatically clears failed state', () => {
    const context = setup({
      state: 'failed',
      attemptedAt: 1_000,
      href: 'http://localhost:31580/libraries',
    });
    context.advance(PRELOAD_RECOVERY_STABLE_MS * 2);
    context.fireTimer();
    expect(readPreloadRecovery(context.storage)?.state).toBe('failed');
  });

  it('clears a successful requested state after the stable interval', () => {
    const context = setup({
      state: 'reload-requested',
      attemptedAt: 1_000,
      href: 'http://localhost:31580/libraries',
    });
    context.advance(PRELOAD_RECOVERY_STABLE_MS);
    context.fireTimer();
    expect(readPreloadRecovery(context.storage)).toBeUndefined();
  });

  it('allows one new reload after a requested state expires', () => {
    const context = setup({
      state: 'reload-requested',
      attemptedAt: -PRELOAD_RECOVERY_STABLE_MS,
      href: 'http://localhost:31580/old',
    });
    context.advance(PRELOAD_RECOVERY_STABLE_MS);
    const event = new Event('vite:preloadError', { cancelable: true });
    context.target.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    expect(context.reloadSilently).toHaveBeenCalledOnce();
  });

  it('does not reload when storage cannot establish a lock', () => {
    const context = setup();
    context.storage.setItem = () => {
      throw new Error('blocked');
    };
    const event = new Event('vite:preloadError', { cancelable: true });
    context.target.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(false);
    expect(context.reloadSilently).not.toHaveBeenCalled();
  });

  it('removes its listener and scheduled timer on dispose', () => {
    const context = setup({
      state: 'reload-requested',
      attemptedAt: 1_000,
      href: 'http://localhost:31580/libraries',
    });
    context.dispose();
    const event = new Event('vite:preloadError', { cancelable: true });
    context.target.dispatchEvent(event);
    expect(context.cancelSchedule).toHaveBeenCalledWith(7);
    expect(context.reloadSilently).not.toHaveBeenCalled();
  });

  it('safely discards malformed records', () => {
    const storage = new MemoryStorage();
    storage.setItem(PRELOAD_RECOVERY_KEY, '{broken');
    expect(readPreloadRecovery(storage)).toBeUndefined();
  });

  it('recognizes only preload errors or an explicit failed record', () => {
    const storage = new MemoryStorage();
    expect(
      isPreloadRouteError(
        new Error('Failed to fetch dynamically imported module'),
        storage
      )
    ).toBe(true);
    expect(isPreloadRouteError(new Error('API request failed'), storage)).toBe(
      false
    );
    storage.setItem(
      PRELOAD_RECOVERY_KEY,
      JSON.stringify({
        state: 'failed',
        attemptedAt: 1,
        href: 'http://localhost',
      })
    );
    expect(isPreloadRouteError(new Error('other'), storage)).toBe(true);
  });
});
