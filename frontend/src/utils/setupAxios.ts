import { API_BASE_URL } from '@/config';
import { store } from '@/store';
import { Auth } from '@/store/_auth';
import type { User } from '@/types';
import axios, { AxiosError } from 'axios';

const REFRESH_TOKEN_HEADER = 'x-refresh-token';
let authBootstrapPromise: Promise<void> | undefined;

function refreshTokenFrom(response: {
  headers: { get?: (name: string) => unknown; [key: string]: unknown };
}) {
  const token =
    response.headers.get?.(REFRESH_TOKEN_HEADER) ??
    response.headers[REFRESH_TOKEN_HEADER];
  return typeof token === 'string' && token ? token : undefined;
}

function authorizationFrom(headers: unknown) {
  if (!headers || typeof headers !== 'object') return undefined;

  const get = Reflect.get(headers, 'get');
  if (typeof get === 'function') {
    const value = Reflect.apply(get, headers, ['Authorization']);
    if (typeof value === 'string') return value;
  }

  for (const [name, value] of Object.entries(headers)) {
    if (name.toLowerCase() === 'authorization' && typeof value === 'string') {
      return value;
    }
  }
  return undefined;
}

export function setupAxios() {
  const state = store.getState();

  axios.defaults.baseURL = API_BASE_URL;
  axios.defaults.headers.common.Accept = 'application/json';

  // authorization header
  axios.defaults.headers.common.Authorization =
    Auth.select.authorization(state);

  axios.interceptors.response.use(null, (error: AxiosError) => {
    if (error.response?.status === 401) {
      const requestAuthorization = authorizationFrom(error.config?.headers);
      const currentAuthorization = Auth.select.authorization(store.getState());
      if (
        requestAuthorization &&
        requestAuthorization === currentAuthorization
      ) {
        store.dispatch(Auth.action.logout());
      }
    }
    throw error;
  });
}

export async function fetchCurrentUser(expectedUserId: string) {
  const response = await axios.get<User>('/api/auth/me');
  const token = refreshTokenFrom(response);
  if (token && response.data.id === expectedUserId) {
    store.dispatch(
      Auth.action.refreshToken({
        userId: response.data.id,
        token,
      })
    );
  }
  return response.data;
}

async function runAuthBootstrap() {
  const url = new URL(window.location.href);
  const token = url.searchParams.get('authToken');
  if (token === null) return;

  url.searchParams.delete('authToken');
  window.history.replaceState(
    window.history.state,
    '',
    `${url.pathname}${url.search}${url.hash}`
  );

  if (!token) {
    store.dispatch(Auth.action.logout());
    return;
  }

  try {
    const response = await axios.get<User>('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    });
    store.dispatch(
      Auth.action.login({
        user: response.data,
        token: refreshTokenFrom(response) ?? token,
      })
    );
  } catch {
    store.dispatch(Auth.action.logout());
  }
}

export function bootstrapAuthFromUrl() {
  authBootstrapPromise ??= runAuthBootstrap();
  return authBootstrapPromise;
}
