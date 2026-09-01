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

// Register PWA and reload when a new deployment is active (avoids stale cached app)
registerSW({ immediate: true });
moment.locale('zh-cn');

// Desktop window-closing beacon: only in standalone app-mode (Edge --app=,
// which is tagged with ?app=1 by the launcher). A plain browser tab (fallback
// path) must NOT send this — its close is not "app closed". sendBeacon keeps
// the POST alive during unload; the backend only marks a timestamp and the
// keep-alive loop still verifies the window title is gone before exiting.
//
// The close-confirmation (confirmOnClose) makes the browser ask before the
// window actually closes, so an accidental click on X cannot kill a reading
// or download session. When the user stays, the early bye beacon is
// harmless: the backend requires the window title to stay gone as well.
if (new URLSearchParams(window.location.search).has('app')) {
  window.addEventListener('beforeunload', (e) => {
    if (store.getState().reader.confirmOnClose) {
      e.preventDefault();
      // Chromium requires this legacy property to show the dialog
      e.returnValue = '';
    }
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
