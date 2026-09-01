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
import { setupAxios } from './utils/setupAxios.ts';
import { appTheme } from './utils/theme.ts';

// Close-confirmation state. The SW's self-reload is a lossless update
// (state lives in redux-persist / localStorage), so it must never trip the
// confirmation dialog — without the flag, an update right after installing
// a new build showed "重新加载应用吗" the moment the user first switched
// pages. Any real close/refresh still asks.
const swReloading = { value: false };
window.addEventListener('beforeunload', (e) => {
  if (store.getState().reader.confirmOnClose && !swReloading.value) {
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
      swReloading.value = true;
    });
  },
});
window.addEventListener('controllerchange', () => {
  // Belt-and-suspenders: if the controller swaps without an updatefound we
  // observed (e.g. immediate:true on first register), the incoming reload
  // is still a SW self-update and stays exempt.
  swReloading.value = true;
  window.setTimeout(() => {
    swReloading.value = false;
  }, 5000);
});

// Desktop window-closing beacon: only in standalone app-mode (Edge --app=,
// which is tagged with ?app=1 by the launcher). A plain browser tab (fallback
// path) must NOT send this — its close is not "app closed". sendBeacon keeps
// the POST alive during unload; the backend only marks a timestamp and the
// keep-alive loop still verifies the window title is gone before exiting.
if (new URLSearchParams(window.location.search).has('app')) {
  window.addEventListener('beforeunload', () => {
    navigator.sendBeacon('/api/app/bye');
  });
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
