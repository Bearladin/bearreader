import './main.scss';

import { registerSW } from 'virtual:pwa-register';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import moment from 'moment';
import 'moment/locale/zh-cn.js';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { App } from './pages/index.tsx';
import { persistor, store } from './store/index.ts';
import { installPreloadRecovery } from './utils/preloadRecovery.ts';
import { setupAxios } from './utils/setupAxios.ts';
import {
  reloadSilently,
  silentReloading,
} from './utils/silentReload.ts';
import { appTheme } from './utils/theme.ts';
import { installExternalLinkHandler } from './utils/openExternal.ts';

// Close-confirmation state. The SW's self-reload is a lossless update
// (state lives in redux-persist / localStorage), so it must never trip the
// confirmation dialog — without the flag, an update right after installing
// a new build showed "重新加载应用吗" the moment the user first switched
// pages. Any real close/refresh still asks.
window.addEventListener('beforeunload', (e) => {
  if (store.getState().reader.confirmOnClose && !silentReloading.value) {
    e.preventDefault();
    // Chromium requires this legacy property to show the dialog
    e.returnValue = '';
  }
});

// Register PWA. autoUpdate makes workbox reload the page when a new SW
// takes over; mark that reload as exempt from the close-confirmation.
// The reload happens on 'controllerchange', which fires exactly once per
// update — matching where workbox calls location.reload().
moment.locale('zh-cn');
registerSW({
  immediate: true,
  onRegisteredSW(
    _url?: string,
    registration?: ServiceWorkerRegistration
  ) {
    if (!registration) return;
    registration.addEventListener('updatefound', () => {
      // A new SW is installing; when it activates on this page it will
      // trigger workbox's reload — that reload must stay silent.
      silentReloading.value = true;
    });
  },
});
window.addEventListener('controllerchange', () => {
  // Belt-and-suspenders: if the controller swaps without an updatefound we
  // observed (e.g. immediate:true on first register), the incoming reload
  // is still a SW self-update and stays exempt.
  silentReloading.value = true;
  window.setTimeout(() => {
    silentReloading.value = false;
  }, 5000);
});

installPreloadRecovery({
  target: window,
  storage: window.sessionStorage,
  href: () => window.location.href,
  now: () => Date.now(),
  reloadSilently,
  schedule: (callback, delayMs) => window.setTimeout(callback, delayMs),
  cancelSchedule: (id) => window.clearTimeout(id),
});

// The launcher issues the session id in the app URL. Beacons from stale tabs
// or other localhost pages therefore cannot extend or terminate this run.
// In-app navigation drops the URL params, and a later full reload (manual or
// SW update) would then lose the session entirely — no heartbeat, no bye, no
// external-link interception. Persist the session per browser tab so the
// reloaded page re-registers everything under the SAME id; the backend's
// random-per-launch session check still rejects stale sessions from old runs.
const appParams = new URLSearchParams(window.location.search);
let appSessionId = appParams.get('appSession') ?? '';
if (appParams.has('app') && appSessionId) {
  try {
    window.sessionStorage.setItem('bearreader/app-session', appSessionId);
  } catch {
    // storage unavailable (privacy mode): URL-only, a reload drops the session
  }
} else if (appParams.has('app')) {
  // Reload inside app mode without URL params: fall back to the tab session.
  try {
    appSessionId =
      window.sessionStorage.getItem('bearreader/app-session') ?? '';
  } catch {
    appSessionId = '';
  }
}
if (appParams.has('app') && appSessionId) {
  navigator.sendBeacon(`/api/app/ready/${appSessionId}`);
  const heartbeat = () => {
    navigator.sendBeacon(`/api/app/heartbeat/${appSessionId}`);
  };
  heartbeat();
  window.setInterval(heartbeat, 5000);
  for (const event of ['focus', 'pageshow', 'online']) {
    window.addEventListener(event, heartbeat);
  }
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) heartbeat();
  });
  window.addEventListener('beforeunload', () => {
    navigator.sendBeacon(`/api/app/bye/${appSessionId}`);
  });
  installExternalLinkHandler();
}

function onBeforeLift() {
  setupAxios();
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Provider store={store}>
      <PersistGate
        persistor={persistor}
        onBeforeLift={onBeforeLift}
        loading={<></>}
      >
        <ConfigProvider locale={zhCN} theme={appTheme}>
          <App />
        </ConfigProvider>
      </PersistGate>
    </Provider>
  </StrictMode>
);
