declare const __APP_VERSION__: string;

/** 应用版本号：构建时由 vite.config.ts 从 lncrawl/VERSION 注入（单一来源，避免前后端版本失同步）。 */
export const APP_VERSION = __APP_VERSION__;
