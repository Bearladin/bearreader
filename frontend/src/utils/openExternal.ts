import axios from 'axios';

export function externalHttpUrl(href: string, currentHref: string) {
  try {
    const current = new URL(currentHref);
    const target = new URL(href, current);
    if (!['http:', 'https:'].includes(target.protocol)) return undefined;
    if (target.origin === current.origin) return undefined;
    return target.href;
  } catch {
    return undefined;
  }
}

export function installExternalLinkHandler() {
  const openThroughSystem = (event: MouseEvent) => {
    if (event.defaultPrevented || ![0, 1].includes(event.button)) return;
    const target = event.target;
    if (!(target instanceof Element)) return;
    const anchor = target.closest('a[href]');
    if (!(anchor instanceof HTMLAnchorElement)) return;
    const url = externalHttpUrl(anchor.href, window.location.href);
    if (!url) return;

    event.preventDefault();
    void axios.post('/api/desktop/open-external', { url }).catch((error) => {
      console.warn('Failed to open external link in the system browser', error);
      window.alert('无法使用系统浏览器打开这个链接，请稍后重试。');
    });
  };
  document.addEventListener('click', openThroughSystem);
  document.addEventListener('auxclick', openThroughSystem);
}
