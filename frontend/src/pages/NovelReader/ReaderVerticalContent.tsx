import cx from 'classnames';
import styles from './ReaderVerticalLayout.module.scss';

import { API_BASE_URL } from '@/config';
import { store } from '@/store';
import { Auth } from '@/store/_auth';
import { Reader } from '@/store/_reader';
import type { ReadChapter } from '@/types';
import { message } from 'antd';
import axios from 'axios';
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import {
  buildTtsSegments,
  resolveTtsFocusElement,
  selectLiveTtsSegments,
  type TtsSegment,
} from './ttsSegments';

const DEFAULT_VOICE = 'zh-CN-XiaoxiaoNeural';
const PREFETCH_AHEAD = 3; // 预取后续段落数（边合成边播的缓冲）
const MAX_CACHE_URLS = 240; // 音频 Blob URL 上限，超出 revoke 最早的防止泄漏

interface ActivePlayer {
  audio: HTMLAudioElement;
  finish: () => void;
}

/**
 * Edge-TTS 在线朗读引擎（v1.1.8）。
 *
 * 逐段（<p> 节拍）流水线：合成一段 → 播放 → 句间停顿 → 下一段；
 * 后台并发预取后续 PREFETCH_AHEAD 段。依赖后端 /api/tts/synthesize，
 * 必须联网；合成失败时提示并停止朗读。
 */
function useEdgeTtsSpeech(
  speechSegments: TtsSegment[],
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
  const playerRef = useRef<ActivePlayer | null>(null);
  const abortControllerRef = useRef(new AbortController());
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

      const text = speechSegments[idx]?.text;
      if (!text) {
        throw new Error('空段落');
      }
      const promise = (async () => {
        const { data: blob } = await axios.post<Blob>(
          '/api/tts/synthesize',
          { sentence: text, voice: effectiveVoice, rate: voiceSpeed },
          {
            responseType: 'blob',
            signal: abortControllerRef.current.signal,
          }
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
        if (inflightAudios.current.get(idx) === promise) {
          inflightAudios.current.delete(idx);
        }
      }
    },
    [speechSegments, effectiveVoice, voiceSpeed]
  );

  const stopPlayer = useCallback(() => {
    const active = playerRef.current;
    if (!active) return;
    active.finish();
    active.audio.pause();
    active.audio.removeAttribute('src');
    active.audio.load();
  }, []);

  const playUrl = useCallback(
    (url: string): Promise<void> =>
      new Promise((resolve, reject) => {
        stopPlayer();
        const audio = new Audio(url);
        let settled = false;
        const finish = (error?: Error) => {
          if (settled) return;
          settled = true;
          audio.onended = null;
          audio.onerror = null;
          if (playerRef.current?.audio === audio) {
            playerRef.current = null;
          }
          if (error) {
            reject(error);
          } else {
            resolve();
          }
        };
        playerRef.current = { audio, finish };
        audio.onended = () => finish();
        audio.onerror = () => finish(new Error('语音播放失败，请检查系统音频设置'));
        void audio
          .play()
          .catch(() => finish(new Error('语音播放失败，请检查系统音频设置')));
      }),
    [stopPlayer]
  );

  const clearAudioResources = useCallback((renewController: boolean) => {
    stoppedRef.current = true;
    abortControllerRef.current.abort();
    if (renewController) {
      abortControllerRef.current = new AbortController();
    }
    stopPlayer();
    for (const url of audioCache.current.values()) {
      URL.revokeObjectURL(url);
    }
    audioCache.current.clear();
    inflightAudios.current.clear();
  }, [stopPlayer]);

  // 停止时清理播放器与音频缓存，并为同章再次朗读准备新请求。
  useEffect(() => {
    if (speaking) {
      stoppedRef.current = false;
      if (abortControllerRef.current.signal.aborted) {
        abortControllerRef.current = new AbortController();
      }
      return;
    }
    clearAudioResources(true);
  }, [speaking, clearAudioResources]);

  useEffect(
    () => () => {
      clearAudioResources(false);
    },
    [clearAudioResources]
  );

  // MediaSession: system media keys and the OS media flyout control TTS,
  // so playback can be toggled while the window is minimized.
  useEffect(() => {
    if (typeof navigator === 'undefined' || !('mediaSession' in navigator)) {
      return;
    }
    if (speaking) {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: data.chapter.title.trim(),
        artist: data.novel.title,
        album: 'BearReader',
      });
      navigator.mediaSession.playbackState = 'playing';
    } else {
      navigator.mediaSession.playbackState = 'paused';
    }
  }, [speaking, data]);

  useEffect(() => {
    if (typeof navigator === 'undefined' || !('mediaSession' in navigator)) {
      return;
    }
    navigator.mediaSession.setActionHandler('play', () => {
      store.dispatch(Reader.action.setSpeaking(true));
    });
    navigator.mediaSession.setActionHandler('pause', () => {
      store.dispatch(Reader.action.setSpeaking(false));
    });
    return () => {
      navigator.mediaSession.setActionHandler('play', null);
      navigator.mediaSession.setActionHandler('pause', null);
      navigator.mediaSession.playbackState = 'paused';
    };
  }, []);

  // 后台预取：边合成边播的缓冲
  useEffect(() => {
    if (!speaking || speechSegments.length === 0) return;
    const count = speechSegments.length;
    const stop = Math.min(position + 1 + PREFETCH_AHEAD, count);
    for (let i = position + 1; i < stop; i += 1) {
      const text = speechSegments[i]?.text;
      if (!text) continue;
      const cached = audioCache.current.get(i);
      const pending = inflightAudios.current.get(i);
      if (cached || pending) continue;
      void ensureAudio(i).catch(() => {
        // 预取失败静默，主循环会重试
      });
    }
  }, [speaking, position, speechSegments, ensureAudio]);

  // 开读预热：进入章节即后台合成第 0 段。edge-tts 单句合成本身要
  // ~2.5s（接口固定握手延迟），预热让用户点击朗读时首段已就绪、
  // 几乎立即出声。合成失败静默（点击时主循环会重试）。
  useEffect(() => {
    if (speechSegments.length === 0) return;
    void ensureAudio(0).catch(() => {});
  }, [speechSegments, ensureAudio]);

  // 主朗读循环（段落节拍）：合成 → 播放 → 句间停顿 → 下一段
  useEffect(() => {
    if (!speaking || speechSegments.length === 0 || !data.content) {
      return;
    }
    stoppedRef.current = false;
    let cancelled = false;
    let tid: ReturnType<typeof setTimeout> | undefined;

    const playSection = async () => {
      const count = speechSegments.length;
      if (position >= count) {
        store.dispatch(Reader.action.setSepakPosition(0));
        if (data.next_id) {
          navigate(`/read/${data.next_id}`);
        } else {
          store.dispatch(Reader.action.setSpeaking(false));
        }
        return;
      }

      const text = speechSegments[position]?.text;
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
        if (cancelled || axios.isCancel(err)) return;
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
      stopPlayer();
    };
  }, [
    speaking,
    speechSegments,
    position,
    data,
    voicePause,
    ensureAudio,
    playUrl,
    stopPlayer,
    navigate,
  ]);
}

export const ReaderVerticalContent: React.FC<{
  data: ReadChapter;
}> = ({ data }) => {
  const token = useSelector(Auth.select.authToken);
  const speaking = useSelector(Reader.select.speaking);
  const position = useSelector(Reader.select.speakPosition);
  const [contentTarget, setContentTarget] = useState<{
    element: HTMLDivElement;
    contentKey: string;
  }>();

  const contentHTML = useMemo(() => {
    if (!token || !data.content) {
      return '';
    }
    const parser = new DOMParser();
    const doc = parser.parseFromString(data.content, 'text/html');
    for (const img of doc.querySelectorAll('img')) {
      // The authenticated image URL is resolved through the identifier that
      // src and alt share. Legacy imported chapters kept a stale alt after
      // the src was rewritten to the stored id (CR-04), so fall back to the
      // src stem when the pair does not match — no re-import needed.
      let key = img.alt;
      if (!key || !img.src.includes(key)) {
        const match = img.src.match(/images\/([0-9a-f]+)\.jpg/i);
        key = match?.[1] ?? '';
      }
      if (!key) continue;
      img.src = `${API_BASE_URL}/static/novels/${data.novel.id}/images/${key}.jpg?token=${token}`;
      img.alt = key;
      img.loading = 'lazy';
    }
    return doc.body.innerHTML;
  }, [data.content, data.novel.id, token]);

  const isImportedBook =
    data.novel.extra?.imported === true &&
    (data.novel.extra.source_format === 'epub' ||
      data.novel.extra.source_format === 'txt');
  const contentRef = useCallback(
    (element: HTMLDivElement | null) => {
      if (!element) return;
      setContentTarget((current) =>
        current?.element === element && current.contentKey === contentHTML
          ? current
          : { element, contentKey: contentHTML }
      );
    },
    [contentHTML]
  );
  const contentEl = contentTarget?.element ?? null;
  const speechSegments = useMemo(
    () =>
      buildTtsSegments(contentTarget?.element ?? null, {
        imported: isImportedBook,
        chapterTitle: data.chapter.title,
      }),
    [contentTarget, data.chapter.title, isImportedBook]
  );
  const getLiveSpeechSegments = useCallback(
    () =>
      selectLiveTtsSegments(speechSegments, isImportedBook, () =>
        buildTtsSegments(contentEl, {
          imported: true,
          chapterTitle: data.chapter.title,
        })
      ),
    [contentEl, data.chapter.title, isImportedBook, speechSegments]
  );

  useEdgeTtsSpeech(speechSegments, data);

  useEffect(() => {
    if (!speaking) return;
    const fid = requestAnimationFrame(() => {
      const liveSegments = getLiveSpeechSegments();
      const childEl = resolveTtsFocusElement(
        contentEl,
        liveSegments,
        position,
        isImportedBook
      );
      childEl?.setAttribute('data-focus', 'true');
      childEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    return () => {
      cancelAnimationFrame(fid);
      const liveSegments = getLiveSpeechSegments();
      const childEl = resolveTtsFocusElement(
        contentEl,
        liveSegments,
        position,
        isImportedBook
      );
      childEl?.removeAttribute('data-focus');
    };
  }, [speaking, position, contentEl, isImportedBook, getLiveSpeechSegments]);

  const handleClick = (e: React.MouseEvent<HTMLElement>) => {
    const target = e.target as HTMLElement | null;
    if (!contentEl || !contentEl.contains(target)) return;
    if (target) {
      if (!isImportedBook) {
        let topLevel: HTMLElement | null = target;
        while (topLevel && topLevel.parentElement !== contentEl) {
          topLevel = topLevel.parentElement;
        }
        if (!topLevel) return;
        const position = Array.prototype.indexOf.call(
          contentEl.children,
          topLevel
        );
        if (position >= 0) {
          store.dispatch(Reader.action.setSepakPosition(position));
        }
        return;
      }
      const liveSegments = getLiveSpeechSegments();
      let clicked: HTMLElement | null = target;
      let index = -1;
      while (clicked && clicked !== contentEl.parentElement) {
        index = liveSegments.findIndex(
          (segment) => segment.element === clicked
        );
        if (index >= 0 || clicked === contentEl) break;
        clicked = clicked.parentElement;
      }
      if (index < 0) return;
      store.dispatch(Reader.action.setSepakPosition(index));
    }
  };

  return (
    <div
      id="chapter-content"
      ref={contentRef}
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
