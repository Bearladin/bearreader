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
    if (Array.isArray(data?.detail)) {
      const messages = data.detail
        .slice(0, 3)
        .map((item: unknown) => {
          if (!item || typeof item !== 'object') return undefined;
          const message = Reflect.get(item, 'msg');
          return typeof message === 'string' ? message : undefined;
        })
        .filter((item: unknown): item is string => typeof item === 'string');
      if (messages.length) {
        return `请求参数无效：${messages.join('；')}`;
      }
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
