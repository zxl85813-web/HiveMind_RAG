/**
 * 应用入口 — 挂载 React 根节点。
 *
 * 参见: REGISTRY.md > 前端
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { intentManager } from './core/IntentManager';
import App from './App';
import './index.css';
import { loggingService } from './services/loggingService';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// 🛰️ [HMER Phase 4]: 意图预加载管理器初始化
intentManager.init(queryClient);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
