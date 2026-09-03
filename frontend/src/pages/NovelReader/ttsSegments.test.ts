import { describe, expect, it } from 'vitest';
import { IMPORTED_TTS_MAX_LENGTH, splitTtsText } from './ttsSegments';

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
