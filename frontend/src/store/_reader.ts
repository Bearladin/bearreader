import { FontFamily, ReaderLayout, ReaderTheme, TextAlign } from '@/types';
import type { PayloadAction } from '@reduxjs/toolkit';
import { createSelector, createSlice } from '@reduxjs/toolkit';
import type { PersistConfig } from 'redux-persist';
import storage from 'redux-persist/lib/storage';
import type { RootState } from '.';

//
// Initial State
//

export interface LastRead {
  chapterId: string;
  offset: number;
}

export interface ReaderState {
  voice: string | undefined;
  voiceSpeed: number;
  voicePause: number; // 句间停顿时长（毫秒），Edge-TTS 在线朗读
  speaking: boolean;
  speakPosition: number;
  fontSize: number;
  lineHeight: number;
  theme: ReaderTheme;
  layout: ReaderLayout;
  fontFamily: FontFamily;
  textAlign: TextAlign;
  autoFetch: boolean;
  autoScroll: boolean;
  autoScrollSpeed: number;
  /** 每本书最后阅读位置（key=novelId）；继续阅读恢复滚动用 */
  lastReads: Record<string, LastRead>;
}

const buildInitialState = (): ReaderState => ({
  layout: ReaderLayout.vertical,
  speaking: false,
  speakPosition: 0,
  voice: undefined,
  voiceSpeed: 1,
  voicePause: 300,
  fontSize: 16,
  lineHeight: 1.4,
  theme: ReaderTheme.White,
  fontFamily: FontFamily.MicrosoftYaHei,
  autoFetch: false,
  textAlign: TextAlign.left,
  autoScroll: false,
  autoScrollSpeed: 60,
  lastReads: {},
});

//
// Slice
//
export const ReaderSlice = createSlice({
  name: 'reader',
  initialState: buildInitialState(),
  reducers: {
    setLayout(state, action: PayloadAction<ReaderState['layout']>) {
      state.layout = action.payload;
    },
    setVoice(state, action: PayloadAction<ReaderState['voice']>) {
      state.voice = action.payload;
    },
    setTheme(state, action: PayloadAction<ReaderState['theme']>) {
      state.theme = action.payload;
    },
    setLineHeight(state, action: PayloadAction<ReaderState['lineHeight']>) {
      state.lineHeight = action.payload;
    },
    setTextAlign(state, action: PayloadAction<ReaderState['textAlign']>) {
      state.textAlign = action.payload;
    },
    setFontSize(state, action: PayloadAction<ReaderState['fontSize']>) {
      // clamp 到可读范围；设置面板与 NavBar 快捷按钮共用此约束
      state.fontSize = Math.min(32, Math.max(12, action.payload));
    },
    setFontFamily(state, action: PayloadAction<ReaderState['fontFamily']>) {
      state.fontFamily = action.payload;
    },
    setSpeaking(state, action: PayloadAction<ReaderState['speaking']>) {
      state.speaking = action.payload;
    },
    setSepakPosition(state, action: PayloadAction<number>) {
      state.speakPosition = action.payload;
    },
    setVoiceSpeed(state, action: PayloadAction<number>) {
      state.voiceSpeed = action.payload;
    },
    setVoicePause(state, action: PayloadAction<number>) {
      state.voicePause = action.payload;
    },
    setAutoFetch(state, action: PayloadAction<boolean>) {
      state.autoFetch = action.payload;
    },
    setAutoScroll(state, action: PayloadAction<boolean>) {
      state.autoScroll = action.payload;
    },
    setAutoScrollSpeed(state, action: PayloadAction<number>) {
      state.autoScrollSpeed = Math.min(300, Math.max(10, action.payload));
    },
    setLastRead(
      state,
      action: PayloadAction<{
        novelId: string;
        chapterId: string;
        offset: number;
      }>
    ) {
      const { novelId, chapterId, offset } = action.payload;
      state.lastReads[novelId] = { chapterId, offset };
    },
  },
});

//
// Actions & Selectors
//
const selectReader = (state: RootState) => state.reader;

export const Reader = {
  action: ReaderSlice.actions,
  select: {
    textAlign: createSelector(selectReader, (reader) => reader.textAlign),
    theme: createSelector(selectReader, (reader) => reader.theme),
    layout: createSelector(selectReader, (reader) => reader.layout),
    fontSize: createSelector(selectReader, (reader) => reader.fontSize),
    fontFamily: createSelector(selectReader, (reader) => reader.fontFamily),
    lineHeight: createSelector(selectReader, (reader) => reader.lineHeight),
    voice: createSelector(selectReader, (reader) => reader.voice),
    voiceSpeed: createSelector(selectReader, (reader) => reader.voiceSpeed),
    voicePause: createSelector(selectReader, (reader) => reader.voicePause),
    speaking: createSelector(selectReader, (reader) => reader.speaking),
    autoFetch: createSelector(selectReader, (reader) => reader.autoFetch),
    speakPosition: createSelector(
      selectReader,
      (reader) => reader.speakPosition
    ),
    lastReads: createSelector(selectReader, (reader) => reader.lastReads),
    autoScroll: createSelector(selectReader, (reader) => reader.autoScroll),
    autoScrollSpeed: createSelector(
      selectReader,
      (reader) => reader.autoScrollSpeed
    ),
  },
};

//
// Persist Config
//
const blacklist: Array<keyof ReaderState> = [
  // items to exclude from local storage
  'speaking',
  'speakPosition',
  'autoScroll',
];

export const readerPersistConfig: PersistConfig<ReaderState> = {
  key: 'reader',
  version: 3,
  storage,
  blacklist,
  migrate: async (state) => {
    if (!state) return state;

    const persisted = state as unknown as Partial<ReaderState>;
    const validFontFamilies: readonly string[] = Object.values(FontFamily);
    const fontFamily = validFontFamilies.includes(persisted.fontFamily ?? '')
      ? persisted.fontFamily
      : FontFamily.MicrosoftYaHei;

    return { ...state, fontFamily, lastReads: persisted.lastReads ?? {} };
  },
};
