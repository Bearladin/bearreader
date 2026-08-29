import cx from 'classnames';
import styles from './ReaderVerticalLayout.module.scss';

import { API_BASE_URL } from '@/config';
import { store } from '@/store';
import { Auth } from '@/store/_auth';
import { Reader } from '@/store/_reader';
import type { ReadChapter } from '@/types';
import { message } from 'antd';
import axios from 'axios';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';

const DEFAULT_VOICE = 'zh-CN-XiaoxiaoNeural';
const PREFETCH_AHEAD = 3; // 预取后续段落数（边合成边播的缓冲）
const MAX_CACHE_URLS = 240; // 音频 Blob URL 上限，超出 revoke 最早的防止泄漏

/**
 * Edge-TTS 在线朗读引擎（v1.1.8）。
 *
 * 逐段（<p> 节拍）流水线：合成一段 → 播放 → 句间停顿 → 下一段；
 * 后台并发预取后续 PREFETCH_AHEAD 段。依赖后端 /api/tts/synthesize，
 * 必须联网；合成失败时提示并停止朗读。
 */
function useEdgeTtsSpeech(
  contentEl: HTMLDivElement | null,
  data: ReadChapter
) {
  const navigate = useNavigate();

  const voice = useSelector(Reader.select.voice);
  const speaking = useSelector(Reader.select.speaking);
  const position = useSelector(Reader.select.speakPosition);
  const voiceSpeed = useSelector(Reader.select.voiceSpeed);
  const voicePause = useSelector(Reader.select.voicePause);

  const audioCache = useRef(new Map<number, string>()); // 段序号 -> Blob URL
  const inflightAudios = useRef(new Map<number, Promise<string>>());
  const playerRef = useRef<HTMLAudioElement | null>(null);
  // true once the reading session ends; a synthesize that finishes LATE must
  // not publish its Blob URL into the cache (resource leak) and its URL is
  // revoked immediately.
  const stoppedRef = useRef(false);

  const effectiveVoice = voice ?? DEFAULT_VOICE;

  const ensureAudio = useCallback(
    async (idx: number): Promise<string> => {
      const cached = audioCache.current.get(idx);
      if (cached) return cached;
      const pending = inflightAudios.current.get(idx);
      if (pending) return pending;

      const text = contentEl?.children[idx]?.textContent?.trim();
      if (!text) {
        throw new Error('空段落');
      }
      const promise = (async () => {
        const { data: blob } = await axios.post<Blob>(
          '/api/tts/synthesize',
          { sentence: text, voice: effectiveVoice, rate: voiceSpeed },
          { responseType: 'blob' }
        );
        const url = URL.createObjectURL(blob);
        if (stoppedRef.current) {
          // session ended while this request was in flight: drop the audio
          // immediately instead of leaking it into the cache
          URL.revokeObjectURL(url);
          return url; // the caller is cancelled and will not play it
        }
        if (audioCache.current.size >= MAX_CACHE_URLS) {
          const first = audioCache.current.keys().next().value;
          if (first !== undefined) {
            const oldUrl = audioCache.current.get(first);
            if (oldUrl) URL.revokeObjectURL(oldUrl);
            audioCache.current.delete(first);
          }
        }
        audioCache.current.set(idx, url);
        return url;
      })();
      inflightAudios.current.set(idx, promise);
      try {
        return await promise;
      } finally {
        inflightAudios.current.delete(idx);
      }
    },
    [contentEl, effectiveVoice, voiceSpeed]
  );

  const playUrl = useCallback(
    (url: string): Promise<void> =>
      new Promise((resolve) => {
        const audio = new Audio(url);
        playerRef.current = audio;
        audio.onended = () => {
          playerRef.current = null;
          resolve();
        };
        audio.onerror = () => {
          playerRef.current = null;
          resolve();
        };
        void audio.play().catch(() => {
          playerRef.current = null;
          resolve();
        });
      }),
    []
  );

  // 停止时清理播放器与音频缓存
  useEffect(() => {
    if (speaking) return;
    stoppedRef.current = true;
    if (playerRef.current) {
      playerRef.current.pause();
      playerRef.current = null;
    }
    for (const url of audioCache.current.values()) {
      URL.revokeObjectURL(url);
    }
    audioCache.current.clear();
    inflightAudios.current.clear();
  }, [speaking]);

  // 后台预取：边合成边播的缓冲
  useEffect(() => {
    if (!speaking || !contentEl) return;
    const count = contentEl.children.length;
    const stop = Math.min(position + 1 + PREFETCH_AHEAD, count);
    for (let i = position + 1; i < stop; i += 1) {
      const text = contentEl.children[i]?.textContent?.trim();
      if (!text) continue;
      const cached = audioCache.current.get(i);
      const pending = inflightAudios.current.get(i);
      if (cached || pending) continue;
      void ensureAudio(i).catch(() => {
        // 预取失败静默，主循环会重试
      });
    }
  }, [speaking, position, contentEl, ensureAudio]);

  // 开读预热：进入章节即后台合成第 0 段。edge-tts 单句合成本身要
  // ~2.5s（接口固定握手延迟），预热让用户点击朗读时首段已就绪、
  // 几乎立即出声。合成失败静默（点击时主循环会重试）。
  useEffect(() => {
    if (!contentEl) return;
    void ensureAudio(0).catch(() => {});
  }, [contentEl, ensureAudio]);

  // 主朗读循环（段落节拍）：合成 → 播放 → 句间停顿 → 下一段
  useEffect(() => {
    if (!speaking || !contentEl || !data.content) {
      return;
    }
    stoppedRef.current = false;
    let cancelled = false;
    let tid: ReturnType<typeof setTimeout> | undefined;

    const playSection = async () => {
      const count = contentEl!.children.length;
      if (position >= count) {
        store.dispatch(Reader.action.setSepakPosition(0));
        if (data.next_id) {
          navigate(`/read/${data.next_id}`);
        } else {
          store.dispatch(Reader.action.setSpeaking(false));
        }
        return;
      }

      const text = contentEl!.children[position]?.textContent?.trim();
      if (!text) {
        store.dispatch(Reader.action.setSepakPosition(position + 1));
        return;
      }
      store.dispatch(Reader.action.setSepakPosition(position));

      try {
        const url = await ensureAudio(position);
        if (cancelled) return;
        await playUrl(url);
        if (cancelled) return;
        if (voicePause > 0) {
          await new Promise<void>((resolve) => {
            tid = setTimeout(resolve, voicePause);
          });
        }
        if (cancelled) return;
        store.dispatch(Reader.action.setSepakPosition(position + 1));
      } catch (err) {
        message.error(
          err instanceof Error && err.message
            ? err.message
            : '语音合成失败，请检查网络'
        );
        store.dispatch(Reader.action.setSpeaking(false));
      }
    };

    void playSection();

    return () => {
      cancelled = true;
      if (tid) clearTimeout(tid);
      if (playerRef.current) {
        playerRef.current.pause();
        playerRef.current = null;
      }
    };
  }, [
    speaking,
    contentEl,
    position,
    data,
    voicePause,
    ensureAudio,
    playUrl,
    navigate,
  ]);
}

export const ReaderVerticalContent: React.FC<{
  data: ReadChapter;
}> = ({ data }) => {
  const token = useSelector(Auth.select.authToken);
  const speaking = useSelector(Reader.select.speaking);
  const position = useSelector(Reader.select.speakPosition);
  const [contentEl, setContentEl] = useState<HTMLDivElement | null>(null);

  useEdgeTtsSpeech(contentEl, data);

  const contentHTML = useMemo(() => {
    if (!token || !data.content) {
      return '';
    }
    const parser = new DOMParser();
    const doc = parser.parseFromString(data.content, 'text/html');
    for (const img of doc.querySelectorAll('img')) {
      if (!img.src.includes(img.alt)) continue;
      img.src = `${API_BASE_URL}/static/novels/${data.novel.id}/images/${img.alt}.jpg?token=${token}`;
      img.loading = 'lazy';
    }
    return doc.body.innerHTML;
  }, [data.content, data.novel.id, token]);

  useEffect(() => {
    if (!speaking) return;
    const fid = requestAnimationFrame(() => {
      const childEl = contentEl?.children[position];
      childEl?.setAttribute('data-focus', 'true');
    });
    return () => {
      cancelAnimationFrame(fid);
      const childEl = contentEl?.children[position];
      childEl?.removeAttribute('data-focus');
    };
  }, [speaking, position, contentEl]);

  const handleClick = (e: React.MouseEvent<HTMLElement>) => {
    let target = e.target as HTMLElement | null;
    if (!contentEl || !contentEl.contains(target)) return;
    while (target && target.parentElement !== contentEl) {
      target = target.parentElement!;
    }
    if (target) {
      const index = Array.prototype.indexOf.call(contentEl.children, target);
      store.dispatch(Reader.action.setSepakPosition(index));
    }
  };

  return (
    <div
      id="chapter-content"
      ref={setContentEl}
      dangerouslySetInnerHTML={{
        __html: contentHTML,
      }}
      onPointerUp={handleClick}
      className={cx(styles.content, {
        [styles.speaking]: speaking,
      })}
    />
  );
};
