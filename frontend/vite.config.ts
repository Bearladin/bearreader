import { readFileSync } from 'node:fs';
import react from '@vitejs/plugin-react-swc';
import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';
import tsconfigPaths from 'vite-tsconfig-paths';

// 应用版本单一来源：后端 lncrawl/VERSION。构建时注入，前端不再手工维护版本号。
const APP_VERSION = readFileSync(new URL('../lncrawl/VERSION', import.meta.url), 'utf-8').trim();

// https://vite.dev/config/
export default defineConfig({
  base: '/',
  define: {
    __APP_VERSION__: JSON.stringify(APP_VERSION),
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
    emptyOutDir: true,
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-antd': ['antd'],
          'vendor-antd-icons': ['@ant-design/icons'],
          'vendor-redux': ['@reduxjs/toolkit', 'react-redux', 'redux-persist'],
        },
      },
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8080',
      '/static': 'http://localhost:8080',
      '/ping': 'http://localhost:8080',
    },
  },
  plugins: [
    {
      // 窗口标题栏的版本号同样来自 lncrawl/VERSION：index.html 的 <title> 是
      // 静态文本，define 只注入 JS 模块，需要这个钩子在构建时改写 title。
      name: 'inject-app-version-into-title',
      transformIndexHtml(html) {
        return html.replace(
          /<title>.*<\/title>/,
          `<title>BearReader v${APP_VERSION}</title>`,
        );
      },
    },
    react(),
    tsconfigPaths(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: [
        'icons/bear-32.png',
        'icons/icon-192.png',
        'icons/icon-512.png',
      ],
      manifest: {
        name: 'BearReader',
        short_name: 'BearReader',
        description: '专注中文网络小说的下载、阅读与电子书导出工具',
        lang: 'zh-CN',
        theme_color: '#202329',
        background_color: '#30343B',
        display: 'standalone',
        categories: ['reader', 'novel', 'ebook', 'lightnovel'],
        icons: [
          {
            src: '/icons/icon-192.png',
            type: 'image/png',
            sizes: '192x192',
            purpose: 'any',
          },
          {
            src: '/icons/icon-512.png',
            type: 'image/png',
            sizes: '512x512',
            purpose: 'any',
          },
          {
            src: '/icons/icon-512.png',
            type: 'image/png',
            sizes: '512x512',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        cleanupOutdatedCaches: true,
        globPatterns: ['**/*.{js,css,ico,png,svg,woff2}'],
        // 阅读字体超过 Workbox 默认的 2 MiB 单文件上限；桌面版始终由
        // 本地后端提供这些资源，无需重复放入 service worker 预缓存。
        globIgnores: ['**/XiaoXiongReader*.woff2'],
        navigateFallbackDenylist: [/^\/api/, /^\/static/, /^\/docs/],
      },
    }),
  ],
});
