import { Reader } from '@/store/_reader';
import { store } from '@/store';
import { useEffect } from 'react';

/**
 * 自动滚动引擎：rAF 平滑滚动；用户手动滚轮/触摸即关闭自动滚动；
 * 滚到章底自动停止（不自动切章）；朗读中不启动（朗读跟随另管）。
 */
export function useAutoScroll(
  enabled: boolean,
  speedPxPerSec: number,
  speaking: boolean
) {
  useEffect(() => {
    if (!enabled || speaking) return;

    const stopOnManualScroll = () => {
      store.dispatch(Reader.action.setAutoScroll(false));
    };
    window.addEventListener('wheel', stopOnManualScroll, { passive: true });
    window.addEventListener('touchstart', stopOnManualScroll, {
      passive: true,
    });

    let raf = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.1);
      last = now;
      window.scrollBy(0, speedPxPerSec * dt);
      const doc = document.documentElement;
      const atBottom =
        window.scrollY + window.innerHeight >= doc.scrollHeight - 4;
      if (atBottom) {
        store.dispatch(Reader.action.setAutoScroll(false));
        return;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('wheel', stopOnManualScroll);
      window.removeEventListener('touchstart', stopOnManualScroll);
    };
  }, [enabled, speedPxPerSec, speaking]);
}
