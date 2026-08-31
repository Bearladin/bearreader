import './index.scss';

import { copy } from '@/locales/zh-CN';
import { store } from '@/store';
import { Reader } from '@/store/_reader';
import { type Job, type ReadChapter } from '@/types';
import { stringifyError } from '@/utils/errors';
import { formatFromNow } from '@/utils/time';
import { Button, Flex, Result, Spin } from 'antd';
import axios from 'axios';
import { LRUCache } from 'lru-cache';
import { useEffect, useRef, useState } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { useSelector } from 'react-redux';
import { useNavigate, useParams } from 'react-router-dom';
import { ReaderVerticalLayout } from './ReaderVerticalLayout';
import { focusReaderPosition, isReaderInteractiveTarget } from './utils';

const fetchJobs = new LRUCache<string, Promise<Job>>({ max: 1000 });
const cache = new LRUCache<string, Promise<ReadChapter>>({ max: 1000 });

async function fetchChapter(id: string) {
  const { data } = await axios.get<ReadChapter>(`/api/chapter/${id}/read`);
  if (data.content) {
    const header = renderToStaticMarkup(
      <>
        <h1 style={{ marginBottom: 6 }}>{data.chapter.title.trim()}</h1>
        <div style={{ fontSize: 12, opacity: 0.8, marginBottom: 25 }}>
          章节：{data.chapter.serial} / {data.novel.chapter_count}
          <span> | </span>
          更新于 {formatFromNow(data.chapter.updated_at)}
        </div>
      </>
    );
    const clean = data.content.replace(
      /<p>(\s+)|(&nbsp;)+<\/p>(\n|\s|<br\/>)+/gim,
      ''
    );
    data.content = header + clean;
  }
  return data;
}

function fetchChapterCached(id: string): Promise<ReadChapter> {
  if (!cache.has(id)) {
    const request = fetchChapter(id).catch((error) => {
      if (cache.get(id) === request) {
        cache.delete(id);
      }
      throw error;
    });
    cache.set(id, request);
  }
  return cache.get(id)!;
}

function createFetchJob(id: string) {
  if (!fetchJobs.has(id)) {
    const promise = axios
      .get<Job>(`/api/chapter/${id}/fetch`)
      .then((res) => res.data)
      .catch((error) => {
        // a failed job fetch must not stay cached forever — allow a retry
        if (fetchJobs.get(id) === promise) {
          fetchJobs.delete(id);
        }
        throw error;
      });
    fetchJobs.set(id, promise);
  }
  return fetchJobs.get(id)!;
}

export const NovelReaderPage: React.FC<any> = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const autoFetch = useSelector(Reader.select.autoFetch);
  const restoredChapterRef = useRef<string | undefined>(undefined);

  const [refreshId, setRefreshId] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const [data, setData] = useState<ReadChapter>();
  const [job, setJob] = useState<Job>();
  const chapterId = data?.chapter.id;
  const chapterDone = data?.chapter.is_done;
  const chapterContent = data?.content;
  const novelId = data?.novel.id;

  // current chapter content data
  useEffect(() => {
    // Generation guard: rapidly switching chapters must never let a stale
    // response overwrite the currently displayed chapter.
    let stale = false;
    if (id) {
      setLoading(true);
      const fetchChapter = async () => {
        setError(undefined);
        try {
          if (fetchJobs.has(id)) {
            cache.delete(id);
          } else {
            setJob(undefined);
          }
          const data = await fetchChapterCached(id);
          if (stale) return;
          setData(data);
          // Mark read history only for the chapter actually opened here —
          // preloads of prev/next never write history. Non-blocking: a
          // failed history write must never interrupt reading.
          void axios.post(`/api/read-history/add/${id}`).catch(() => {});
        } catch (err) {
          if (stale) return;
          setError(stringifyError(err));
        } finally {
          if (!stale) setLoading(false);
        }
      };
      fetchChapter();
    } else {
      setData(undefined);
      setJob(undefined);
      setError('URL 中缺少章节 ID');
    }
    return () => {
      stale = true;
      // Chapter-to-chapter navigation keeps TTS playing: the new chapter's
      // layout remounts and resumes from paragraph 0. Leaving /read/* is the
      // only place that stops playback here (navigate() already pushed the
      // new URL by the time this cleanup runs).
      if (!window.location.pathname.startsWith('/read/')) {
        store.dispatch(Reader.action.setSpeaking(false));
      }
    };
  }, [id, refreshId]);

  // preload previous chapter
  useEffect(() => {
    if (data?.previous_id) {
      fetchChapterCached(data.previous_id)
        .then((prev) => {
          if (autoFetch && !prev.chapter.is_done) {
            createFetchJob(prev.chapter.id).catch(() => {});
          }
        })
        .catch(() => {});
    }
  }, [data?.previous_id, autoFetch]);

  // preload next chapter
  useEffect(() => {
    if (data?.next_id) {
      fetchChapterCached(data.next_id)
        .then((next) => {
          if (autoFetch && !next.chapter.is_done) {
            createFetchJob(next.chapter.id).catch(() => {});
          }
        })
        .catch(() => {});
    }
  }, [data?.next_id, autoFetch]);

  // get job details if auto fetch is enabled
  useEffect(() => {
    if (autoFetch && data?.chapter?.id && !data.chapter.is_done) {
      createFetchJob(data.chapter.id).then(setJob).catch(console.error);
    } else {
      setJob(undefined);
    }
  }, [autoFetch, data?.chapter.id, data?.chapter.is_done]);

  // auto refresh job status
  useEffect(() => {
    if (!job?.id || !data?.chapter.id || data.chapter.is_done) {
      return;
    }
    const id = data.chapter.id;
    if (job.is_done) {
      cache.delete(id);
      setRefreshId((v) => v + 1);
    } else {
      const refreshJob = async () => {
        try {
          const { data } = await axios.get<Job>(`/api/job/${job.id}`);
          fetchJobs.set(id, Promise.resolve(data));
          setJob(data);
        } catch {}
      };
      const iid = setInterval(refreshJob, 1000);
      return () => clearInterval(iid);
    }
  }, [data?.chapter.id, data?.chapter.is_done, job?.is_done, job?.id]);

  // Reader hotkeys: ←/→ chapter or paragraph, Space scroll/page, S speak.
  // Reads live values from the store so the listener never goes stale.
  useEffect(() => {
    if (!data) return;
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (
        e.ctrlKey ||
        e.altKey ||
        e.metaKey ||
        isReaderInteractiveTarget(target)
      ) {
        return;
      }
      const isSpeaking = Reader.select.speaking(store.getState());
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        const forward = e.key === 'ArrowRight';
        if (isSpeaking) {
          e.preventDefault();
          const position = Reader.select.speakPosition(store.getState());
          const next = forward ? position + 1 : Math.max(0, position - 1);
          if (next !== position || forward) {
            store.dispatch(Reader.action.setSepakPosition(next));
            focusReaderPosition(next);
          }
        } else if (!e.repeat) {
          e.preventDefault();
          const dest = forward ? data.next_id : data.previous_id;
          if (dest) navigate(`/read/${dest}`);
        }
        return;
      }
      if (e.key === '+' || e.code === 'NumpadAdd') {
        e.preventDefault();
        const fontSize = Reader.select.fontSize(store.getState());
        store.dispatch(Reader.action.setFontSize(fontSize + 1));
        return;
      }
      if (e.key === '-' || e.code === 'NumpadSubtract') {
        e.preventDefault();
        const fontSize = Reader.select.fontSize(store.getState());
        store.dispatch(Reader.action.setFontSize(fontSize - 1));
        return;
      }
      if (e.key === ' ') {
        e.preventDefault();
        const doc = document.documentElement;
        const atBottom =
          window.scrollY + window.innerHeight >= doc.scrollHeight - 10;
        if (atBottom && !isSpeaking && !e.repeat && data.next_id) {
          navigate(`/read/${data.next_id}`);
          return;
        }
        window.scrollBy({ top: window.innerHeight * 0.9, behavior: 'auto' });
        return;
      }
      if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        if (isSpeaking) {
          store.dispatch(Reader.action.setSpeaking(false));
        } else if (data.content) {
          store.dispatch(Reader.action.setSpeaking(true));
          focusReaderPosition(Reader.select.speakPosition(store.getState()));
        }
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [data, navigate]);

  // Chapter-scoped state must change only when the chapter identity changes.
  useEffect(() => {
    if (!chapterId) return;
    restoredChapterRef.current = undefined;
    store.dispatch(Reader.action.setSepakPosition(0));
  }, [chapterId]);

  useEffect(() => {
    if (
      !chapterContent ||
      !chapterId ||
      !novelId ||
      restoredChapterRef.current === chapterId
    ) {
      return;
    }
    restoredChapterRef.current = chapterId;
    const saved = Reader.select.lastReads(store.getState())[novelId];
    const target = saved && saved.chapterId === chapterId ? saved.offset : 0;
    let raf1 = 0;
    let raf2 = 0;
    raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        const max = Math.max(
          0,
          document.documentElement.scrollHeight - window.innerHeight
        );
        window.scrollTo(0, Math.min(target, max));
      });
    });

    return () => {
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
    };
  }, [chapterContent, chapterId, novelId]);

  useEffect(() => {
    if (chapterId && !chapterContent && chapterDone) {
      store.dispatch(Reader.action.setSpeaking(false));
    }
  }, [chapterContent, chapterDone, chapterId]);

  // Persist the reading offset (throttled) so "continue reading" reopens
  // at the same spot. Only the currently opened chapter writes history.
  useEffect(() => {
    if (!data) return;
    let lastWrite = 0;
    const onScroll = () => {
      const now = Date.now();
      if (now - lastWrite < 500) return;
      lastWrite = now;
      const max = Math.max(
        0,
        document.documentElement.scrollHeight - window.innerHeight
      );
      store.dispatch(
        Reader.action.setLastRead({
          novelId: data.novel.id,
          chapterId: data.chapter.id,
          offset: Math.min(Math.max(0, window.scrollY), max),
        })
      );
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, [data]);

  if (loading || (!error && id && data && data.chapter.id !== id)) {
    return (
      <Flex
        align="center"
        justify="center"
        style={{ height: 'calc(100vh - 60px)' }}
      >
        <Spin
          size="large"
          aria-label="正在加载章节内容"
          style={{ margin: '50px 0' }}
        />
      </Flex>
    );
  }

  if (error || !data || !id) {
    return (
      <Flex
        align="center"
        justify="center"
        style={{ height: 'calc(100vh - 60px)' }}
      >
        <Result
          status="404"
          title="加载章节内容失败"
          subTitle={error}
          extra={
            <Button
              onClick={() => {
                setLoading(true);
                setRefreshId((v) => v + 1);
              }}
            >
              {copy.common.retry}
            </Button>
          }
        />
      </Flex>
    );
  }

  return <ReaderVerticalLayout key={id} data={data} job={job} />;
};
