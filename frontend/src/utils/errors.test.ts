import { AxiosError } from 'axios';
import { describe, expect, it } from 'vitest';
import { stringifyError } from './errors';

function axiosError(data: unknown): AxiosError {
  return new AxiosError('request failed', 'ERR_BAD_REQUEST', undefined, undefined, {
    data,
    status: 422,
    statusText: 'Unprocessable Entity',
    headers: {},
    config: { headers: {} } as never,
  });
}

describe('stringifyError', () => {
  it('keeps a string server detail', () => {
    expect(stringifyError(axiosError({ detail: '文件太大' }))).toBe('文件太大');
  });

  it('renders bounded FastAPI validation details', () => {
    const error = axiosError({
      detail: [
        { msg: 'Field required' },
        { msg: 'Invalid value' },
        { msg: 'Third error' },
        { msg: 'Must not be shown' },
      ],
    });

    expect(stringifyError(error)).toBe(
      '请求参数无效：Field required；Invalid value；Third error'
    );
  });

  it('uses the fallback for an unknown response shape', () => {
    expect(stringifyError(axiosError({ detail: [{ unknown: true }] }), '回退')).toBe(
      '回退'
    );
  });
});
