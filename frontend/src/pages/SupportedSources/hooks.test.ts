import { describe, expect, it } from 'vitest';
import { supportedSourcesRequest } from './hooks';

describe('supportedSourcesRequest', () => {
  it('bypasses a previous build cache and changes on retry', () => {
    expect(supportedSourcesRequest(0)).toEqual({
      url: '/api/meta/supported-sources',
      config: {
        params: { refresh: 0 },
        headers: { 'Cache-Control': 'no-cache' },
      },
    });
    expect(supportedSourcesRequest(1).config.params.refresh).toBe(1);
  });
});
