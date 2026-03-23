import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';
import { visualizer } from 'rollup-plugin-visualizer';
import viteCompression from 'vite-plugin-compression';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'mask-icon.svg', 'icon-512.png'],
      manifest: {
        name: 'HiveMind RAG',
        short_name: 'HiveMind',
        description: 'AI-First RAG Platform with HiveMind Swarm Orchestration',
        theme_color: '#111827',
        icons: [
          {
            src: 'icon-512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      },
      workbox: {
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'google-fonts-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365 // <== 365 days
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          },
          {
            urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'gstatic-fonts-cache',
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365 // <== 365 days
              },
              cacheableResponse: {
                statuses: [0, 200]
              }
            }
          }
        ]
      }
    }),
    visualizer({
      open: false,
      filename: 'stats.html',
      gzipSize: true,
      brotliSize: true,
    }),
    viteCompression({
      verbose: true,
      disable: false,
      threshold: 10240,
      algorithm: 'gzip',
      ext: '.gz',
    }),
    viteCompression({
      verbose: true,
      disable: false,
      threshold: 10240,
      algorithm: 'brotliCompress',
      ext: '.br',
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            // React Core & Router
            if (
              id.includes('react') ||
              id.includes('react-dom') ||
              id.includes('react-router-dom') ||
              id.includes('zustand') ||
              id.includes('@tanstack/react-query')
            ) {
              return 'react-vendor';
            }
            
            // UI Component Libraries (Ant Design)
            if (id.includes('antd') || id.includes('@ant-design')) {
              return 'antd-vendor';
            }
            
            // Visualization & Graph Libraries
            if (
              id.includes('@antv') ||
              id.includes('@xyflow') ||
              id.includes('force-graph') ||
              id.includes('d3-force')
            ) {
              return 'graph-vendor';
            }
            
            // Dashboard & Charting (Recharts)
            if (id.includes('recharts')) {
              return 'charts-vendor';
            }
            
            // Markdown & Syntax Highlighting
            if (
              id.includes('react-markdown') ||
              id.includes('highlight.js') ||
              id.includes('rehype') ||
              id.includes('remark')
            ) {
              return 'markdown-vendor';
            }
            
            // Backend Integration & Utilities
            if (
              id.includes('axios') ||
              id.includes('zod') ||
              id.includes('i18next') ||
              id.includes('lucide-react')
            ) {
              return 'utils-vendor';
            }

            // Sentry & Observability
            if (id.includes('@sentry')) {
              return 'sentry-vendor';
            }
            
            // Everything else from node_modules goes to general vendor
            return 'vendor';
          }
        },
      },
    },
    chunkSizeWarningLimit: 1000, // 增加分包后的警报阈值
  },
  css: {
    modules: {
      localsConvention: 'camelCase',
    },
  },
});
