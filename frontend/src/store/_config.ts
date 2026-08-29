import type { PayloadAction } from '@reduxjs/toolkit';
import { createSelector, createSlice } from '@reduxjs/toolkit';
import type { PersistConfig } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import type { RootState } from '.';

//
// Initial State
//

export interface ConfigState {
  supportSourcesPageSize: number;
}

const buildInitialState = (): ConfigState => ({
  supportSourcesPageSize: 12,
});

//
// Slice
//
export const ConfigSlice = createSlice({
  name: 'auth',
  initialState: buildInitialState(),
  reducers: {
    setSupportedSourcesPageSize(state, action: PayloadAction<number>) {
      state.supportSourcesPageSize = action.payload;
    },
  },
});

//
// Actions & Selectors
//
const selectConfigState = (state: RootState) => state.config;
const supportedSourcesPageSize = createSelector(
  selectConfigState,
  (state) => state.supportSourcesPageSize
);

export const Config = {
  action: ConfigSlice.actions,
  select: {
    supportedSourcesPageSize,
  },
};

//
// Persist Config
//
const blacklist: Array<keyof ConfigState> = [
  // items to exclude from local storage
];

export const configPersistConfig: PersistConfig<ConfigState> = {
  key: 'config',
  version: 1,
  storage,
  blacklist,
};
