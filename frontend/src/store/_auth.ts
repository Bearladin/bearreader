import type { LoginResponse, NotificationItem, User } from '@/types';
import { UserRole } from '@/types/enums';
import { parseJwt } from '@/utils/jwt';
import type { PayloadAction } from '@reduxjs/toolkit';
import { createSelector, createSlice } from '@reduxjs/toolkit';
import axios from 'axios';
import type { PersistConfig } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import type { RootState } from '.';

//
// Initial State
//

interface UserAuth {
  user: User;
  token: string;
  tokenExpiresAt: number;
  emailVerified: boolean;
}

export interface AuthState {
  auth: UserAuth | null;
  availableAuths: Record<string, UserAuth>;
}

const buildInitialState = (): AuthState => ({
  auth: null,
  availableAuths: {},
});

//
// Slice
//
export const AuthSlice = createSlice({
  name: 'auth',
  initialState: buildInitialState(),
  reducers: {
    login(state, action: PayloadAction<LoginResponse>) {
      const { user, token } = action.payload;
      const tokenExpiresAt = 1000 * parseJwt(token)!.exp;
      state.auth = {
        user,
        token,
        emailVerified: user.is_verified,
        tokenExpiresAt,
      };
      state.availableAuths[state.auth.user.id] = state.auth;
      axios.defaults.headers.common.Authorization = `Bearer ${token}`;
      for (const [key, val] of Object.entries(state.availableAuths)) {
        if (val.tokenExpiresAt <= Date.now()) {
          delete state.availableAuths[key];
        }
      }
    },
    refreshToken(
      state,
      action: PayloadAction<{ userId: string; token: string }>
    ) {
      if (!state.auth || state.auth.user.id !== action.payload.userId) return;
      const { token } = action.payload;
      const expiresAt = parseJwt(token)?.exp;
      if (typeof expiresAt !== 'number') return;
      state.auth.token = token;
      state.auth.tokenExpiresAt = 1000 * expiresAt;
      state.availableAuths[state.auth.user.id] = state.auth;
      axios.defaults.headers.common.Authorization = `Bearer ${token}`;
    },
    logout(state) {
      state.auth = null;
      axios.defaults.headers.common.Authorization = undefined;
    },
    switchUser(state, action: PayloadAction<string>) {
      state.auth = state.availableAuths[action.payload];
      axios.defaults.headers.common.Authorization = `Bearer ${state.auth.token}`;
    },
    removeUserHistory(state, action: PayloadAction<string>) {
      delete state.availableAuths[action.payload];
    },
    setEmailVerified(state) {
      if (!state.auth) return;
      state.auth.emailVerified = true;
      state.availableAuths[state.auth.user.id].emailVerified = true;
    },
    setUser(state, action: PayloadAction<User>) {
      const user = action.payload;
      if (state.auth?.user.id === user.id) {
        state.auth.user = user;
      }
      if (state.availableAuths[user.id]) {
        state.availableAuths[user.id].user = user;
      }
    },
    setEmailAlerts(
      state,
      action: PayloadAction<Record<NotificationItem, boolean>>
    ) {
      if (!state.auth) return;
      state.auth.user.extra ||= {};
      state.auth.user.extra.email_alerts = {
        ...state.auth.user.extra.email_alerts,
        ...action.payload,
      };
      state.availableAuths[state.auth.user.id].user = state.auth.user;
    },
  },
});

//
// Actions & Selectors
//
const selectAuthState = (state: RootState) => state.auth;
const selectAuth = createSelector(selectAuthState, (state) => state.auth);
const selectLoggedIn = createSelector(
  selectAuth,
  (auth) => auth?.token && auth.tokenExpiresAt > Date.now()
);
const selectUser = createSelector(selectAuth, (auth) => auth?.user);
const selectIsAdmin = createSelector(
  selectUser,
  (user) => user?.role === UserRole.ADMIN
);
const selectToken = createSelector(selectAuth, (auth) => auth?.token);
const selectAuthorization = createSelector(
  selectAuth,
  selectLoggedIn,
  (auth, loggedIn) => (auth && loggedIn ? `Bearer ${auth.token}` : undefined)
);
const selectEmailVerified = createSelector(selectAuth, (auth) =>
  Boolean(auth?.emailVerified)
);
const selectEmailAlertConfig = createSelector(
  selectUser,
  (user) => user?.extra.email_alerts
);
const selectAvailableUsers = createSelector(
  selectAuthState,
  selectUser,
  (state, user) =>
    Object.values(state.availableAuths)
      .filter((x) => x.user.id !== user?.id && x.tokenExpiresAt > Date.now())
      .sort((a, b) => b.tokenExpiresAt - a.tokenExpiresAt)
      .map((x) => x.user)
);

export const Auth = {
  action: AuthSlice.actions,
  select: {
    loggedIn: selectLoggedIn,
    user: selectUser,
    isAdmin: selectIsAdmin,
    authToken: selectToken,
    isVerified: selectEmailVerified,
    authorization: selectAuthorization,
    emailAlerts: selectEmailAlertConfig,
    availableUsers: selectAvailableUsers,
  },
};

//
// Persist Config
//
const blacklist: Array<keyof AuthState> = [
  // items to exclude from local storage
];

export const authPersistConfig: PersistConfig<AuthState> = {
  key: 'auth',
  version: 1,
  storage,
  blacklist,
};
