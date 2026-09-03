import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import {
  IMPORTED_TTS_MAX_LENGTH,
  resolveTtsFocusElement,
  selectLiveTtsSegments,
  splitTtsText,
  type TtsSegment,
} from './ttsSegments';

describe('splitTtsText', () => {
  it('keeps ordinary paragraphs intact', () => {
    expect(splitTtsText('这是一段普通正文。')).toEqual(['这是一段普通正文。']);
  });

  it('splits long Chinese text at sentence punctuation', () => {
    const first = '甲'.repeat(900) + '。';
    const second = '乙'.repeat(900) + '。';
    const chunks = splitTtsText(first + second);
    expect(chunks).toEqual([first, second]);
    expect(chunks.every((chunk) => chunk.length <= IMPORTED_TTS_MAX_LENGTH)).toBe(
      true
    );
    expect(chunks.join('')).toBe(first + second);
  });

  it('hard-splits a paragraph without punctuation', () => {
    const text = '长'.repeat(IMPORTED_TTS_MAX_LENGTH * 2 + 17);
    const chunks = splitTtsText(text);
    expect(chunks.map((chunk) => chunk.length)).toEqual([
      IMPORTED_TTS_MAX_LENGTH,
      IMPORTED_TTS_MAX_LENGTH,
      17,
    ]);
    expect(chunks.join('')).toBe(text);
  });

  it('rejects an invalid maximum length', () => {
    expect(() => splitTtsText('正文', 0)).toThrow('朗读分段长度必须大于 0');
  });
});

describe('resolveTtsFocusElement', () => {
  const scraped = { isConnected: true } as HTMLElement;
  const nested = { isConnected: true } as HTMLElement;
  const detached = { isConnected: false } as HTMLElement;
  const content = {
    children: { item: (index: number) => (index === 1 ? scraped : null) },
    contains: (element: HTMLElement) => element === scraped || element === nested,
  } as unknown as HTMLDivElement;

  it('uses the live top-level node for scraped books', () => {
    expect(resolveTtsFocusElement(content, [], 1, false)).toBe(scraped);
  });

  it('accepts a connected nested segment for imported books', () => {
    const segments = [{ text: '正文', element: nested }] as TtsSegment[];
    expect(resolveTtsFocusElement(content, segments, 0, true)).toBe(nested);
  });

  it('rejects a detached imported segment', () => {
    const segments = [{ text: '正文', element: detached }] as TtsSegment[];
    expect(resolveTtsFocusElement(content, segments, 0, true)).toBeNull();
  });

  it('allows nested imported paragraphs to receive the focus outline', () => {
    const styles = readFileSync(
      new URL('./ReaderVerticalLayout.module.scss', import.meta.url),
      'utf-8'
    );
    expect(styles).toContain('& [data-focus]');
    expect(styles).not.toContain('& > [data-focus]');
  });
});

describe('selectLiveTtsSegments', () => {
  const stale = {
    text: '正文',
    element: { isConnected: false } as HTMLElement,
  };
  const live = {
    text: '正文',
    element: { isConnected: true } as HTMLElement,
  };

  it('rebuilds imported segments from the current DOM', () => {
    expect(selectLiveTtsSegments([stale], true, () => [live])).toEqual([live]);
  });

  it('keeps scraped segments and does not rebuild them', () => {
    let rebuilt = false;
    const selected = selectLiveTtsSegments([live], false, () => {
      rebuilt = true;
      return [stale];
    });
    expect(selected).toEqual([live]);
    expect(rebuilt).toBe(false);
  });
});
