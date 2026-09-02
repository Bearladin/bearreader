import { describe, expect, it } from 'vitest';
import {
  IMPORT_MODAL_BODY_STYLE,
  IMPORT_MODAL_TOP,
  IMPORT_MODAL_WIDTH,
  IMPORT_PREVIEW_STYLE,
} from './layout';

describe('book import modal layout', () => {
  it('keeps the dialog and preview bounded', () => {
    expect(IMPORT_MODAL_WIDTH).toBe(680);
    expect(IMPORT_MODAL_TOP).toBe(24);
    expect(IMPORT_MODAL_BODY_STYLE).toEqual({
      maxHeight: 'calc(100vh - 160px)',
      overflowY: 'auto',
    });
    expect(IMPORT_PREVIEW_STYLE).toEqual({
      maxHeight: 220,
      overflowY: 'auto',
      paddingRight: 4,
    });
  });
});
