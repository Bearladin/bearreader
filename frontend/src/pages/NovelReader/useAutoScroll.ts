import { Reader } from '@/store/_reader';
import { store } from '@/store';
import { message } from 'antd';
import { useEffect } from 'react';

// 开启后 wheel/触摸停止生效的宽限期（毫秒）：点击按钮的同一瞬间
// 触摸板残留微动不应立即关闭刚开启的自动滚动
const MANUAL_INPUT_GRACE_MS = 300;

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

    const startedAt = Date.now();
    const stopOnManualScroll = () => {
      if (Date.now() - startedAt < MANUAL_INPUT_GRACE_MS) return;
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

    // 已在章底（或页面不足一屏）时开启没有意义，提示并立即关闭
    const doc = document.documentElement;
    if (window.scrollY + window.innerHeight >= doc.scrollHeight - 4) {
      message.info('已在章节末尾，自动滚动未开启');
      store.dispatch(Reader.action.setAutoScroll(false));
      return () => {
        window.removeEventListener('wheel', stopOnManualScroll);
        window.removeEventListener('touchstart', stopOnManualScroll);
      };
    }

    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('wheel', stopOnManualScroll);
      window.removeEventListener('touchstart', stopOnManualScroll);
    };
  }, [enabled, speedPxPerSec, speaking]);
}
