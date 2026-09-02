import axios, { type AxiosAdapter } from 'axios';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { setupAxios } from './setupAxios';

const inspectAdapter: AxiosAdapter = async (config) => ({
  data: {
    payload: config.data,
    isFormData: config.data instanceof FormData,
    contentType: config.headers.getContentType(),
  },
  status: 200,
  statusText: 'OK',
  headers: {},
  config,
});

describe('setupAxios request payloads', () => {
  beforeEach(() => {
    delete axios.defaults.headers.post['Content-Type'];
  });

  afterEach(() => {
    delete axios.defaults.headers.post['Content-Type'];
  });

  it('keeps FormData intact for multipart uploads', async () => {
    setupAxios();
    const form = new FormData();
    form.append('file', new Blob(['book']), 'book.txt');

    const response = await axios.post('/upload', form, {
      adapter: inspectAdapter,
    });

    expect(response.data.isFormData).toBe(true);
    expect(response.data.payload).toBe(form);
  });

  it('still serializes ordinary objects as JSON', async () => {
    setupAxios();

    const response = await axios.post(
      '/json',
      { title: '书名' },
      { adapter: inspectAdapter }
    );

    expect(response.data.payload).toBe('{"title":"书名"}');
    expect(response.data.contentType).toContain('application/json');
  });
});
