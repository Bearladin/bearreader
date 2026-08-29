import { AxiosError } from 'axios';

export function stringifyError(
  err: any,
  _default: string = '操作失败，请稍后重试。'
) {
  if (err instanceof AxiosError) {
    const data = err.response?.data;
    if (typeof data === 'string' && data) {
      return data;
    }
    if (data?.error && typeof data?.error === 'string') {
      return data.error;
    }
    if (data?.detail && typeof data?.detail === 'string') {
      return data.detail;
    }
    if (data?.stack && typeof data?.stack === 'string') {
      return data.stack;
    }
    if (data?.name === 'ER_DUP_ENTRY') {
      return '内容重复';
    }
    if (err.response?.status === 401 || err.response?.status === 403) {
      return '无权执行此操作';
    }
  }

  return _default || '' + err;
}
