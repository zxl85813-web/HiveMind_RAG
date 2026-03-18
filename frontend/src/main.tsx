/**
 * 应用入口 — 挂载 React 根节点。
 *
 * 参见: REGISTRY.md > 前端
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';
import './i18n/config';
import { monitor } from './core/MonitorService';
import { registerSW } from 'virtual:pwa-register';

// 🚀 [FE-GOV-005]: PWA Service Worker 注册
const updateSW = registerSW({
  onNeedRefresh() {
    if (confirm('🎉 新版本已准备好，是否立即更新？')) {
      updateSW(true);
    }
  },
  onOfflineReady() {
    console.log('📶 HiveMind RAG 已准备就绪，支持离线访问。');
  },
});

// 🛰️ [FE-GOV-002]: 应用启动上报
monitor.log({
  category: 'system',
  action: 'app_start',
  metadata: { version: '0.0.0' }
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
