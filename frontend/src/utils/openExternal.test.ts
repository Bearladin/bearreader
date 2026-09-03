import { describe, expect, it } from 'vitest';
import { externalHttpUrl } from './openExternal';

describe('externalHttpUrl', () => {
  const current = 'http://localhost:31580/novel/1?app=1';

  it('accepts external HTTP and HTTPS links', () => {
    expect(externalHttpUrl('https://example.com/book', current)).toBe(
      'https://example.com/book'
    );
    expect(externalHttpUrl('http://example.com/', current)).toBe(
      'http://example.com/'
    );
  });

  it('leaves same-origin links and downloads inside BearReader', () => {
    expect(externalHttpUrl('/static/book.epub', current)).toBeUndefined();
    expect(
      externalHttpUrl('http://localhost:31580/novel/2', current)
    ).toBeUndefined();
  });

  it('rejects non-web and malformed URLs', () => {
    expect(externalHttpUrl('file:///C:/Windows/notepad.exe', current)).toBeUndefined();
    expect(externalHttpUrl('javascript:alert(1)', current)).toBeUndefined();
    expect(externalHttpUrl('://broken', current)).toBeUndefined();
  });
});
