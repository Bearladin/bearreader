/// <reference types="vite/client" />
/// <reference types="vite-plugin-pwa/client" />

declare module 'moment/locale/zh-cn.js';

interface VitePreloadErrorEvent extends Event {
  payload: unknown;
}

interface WindowEventMap {
  'vite:preloadError': VitePreloadErrorEvent;
}

declare module 'virtual:pwa-register' {
  export function registerSW(options?: {
    immediate?: boolean;
    onNeedRefresh?: () => void;
    onOfflineReady?: () => void;
    onRegistered?: (
      registration: ServiceWorkerRegistration | undefined
    ) => void;
    onRegisterError?: (error: unknown) => void;
  }): (reloadPage?: boolean) => Promise<void>;
}
