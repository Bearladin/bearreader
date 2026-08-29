export function parseJwt(token: any): Record<string, any> | undefined {
  if (typeof token !== 'string') {
    return undefined;
  }
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const content = atob(base64)
      .split('')
      .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
      .join('');
    const payload = decodeURIComponent(content);
    return JSON.parse(payload) || undefined;
  } catch {
    return undefined;
  }
}
