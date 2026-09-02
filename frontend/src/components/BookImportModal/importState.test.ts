import { describe, expect, it } from 'vitest';
import { importDialogReducer, initialImportDialogState } from './importState';

describe('book import dialog state', () => {
  it.each(['close', 'cancel', 'complete', 'duplicate'])('clears stale state after %s', () => {
    const dirty = importDialogReducer(initialImportDialogState, {
      type: 'patch',
      value: {
        fileName: 'old.epub',
        sessionId: 'old-session',
        error: 'old error',
        title: 'old title',
        authors: 'old author',
        uploadProgress: 88,
      },
    });
    expect(importDialogReducer(dirty, { type: 'reset' })).toEqual(initialImportDialogState);
  });
});
