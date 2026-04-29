/**
 * 应用入口 — 挂载 React 根节点。
 *
 * 启动流程:
 *   1. 从后端 /health 获取平台模式 (rag / agent / full)
 *   2. 挂载 React 应用，路由和导航根据模式动态渲染
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
import { usePlatformStore } from './stores/platformStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// 在挂载前获取平台模式，确保首次渲染就能正确过滤路由和导航
usePlatformStore.getState().fetchPlatformMode().finally(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </StrictMode>,
  );
});
