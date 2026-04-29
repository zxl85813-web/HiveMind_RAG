/**
 * 自定义 render 函数 — 包装测试所需的 Provider 层。
 *
 * 复用 main.tsx 中的 Provider 结构：
 *   - QueryClientProvider (TanStack Query)
 *   - BrowserRouter (React Router)
 *
 * 每次 render 创建独立的 QueryClient 实例，确保测试间隔离。
 *
 * @validates Requirements 5.1, 5.3
 */

import React from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

/**
 * 创建测试专用的 QueryClient。
 *
 * 关闭 retry 和 refetch 以避免测试中的异步副作用。
 */
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        refetchOnWindowFocus: false,
        gcTime: Infinity,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

interface RenderWithProvidersOptions extends Omit<RenderOptions, 'wrapper'> {
  /** 自定义 QueryClient 实例（默认每次创建新实例） */
  queryClient?: QueryClient;
  /** 初始路由路径（默认 "/"） */
  initialRoute?: string;
}

/**
 * 包装 Provider 的自定义 render 函数。
 *
 * @example
 * ```tsx
 * import { renderWithProviders, screen } from '@/test/utils/render';
 *
 * it('should render component', () => {
 *   renderWithProviders(<MyComponent />);
 *   expect(screen.getByText('Hello')).toBeInTheDocument();
 * });
 * ```
 */
export function renderWithProviders(
  ui: React.ReactElement,
  options: RenderWithProvidersOptions = {},
) {
  const {
    queryClient = createTestQueryClient(),
    initialRoute = '/',
    ...renderOptions
  } = options;

  // 设置初始路由
  window.history.pushState({}, 'Test page', initialRoute);

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          {children}
        </BrowserRouter>
      </QueryClientProvider>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    queryClient,
  };
}

// Re-export everything from @testing-library/react for convenience
export * from '@testing-library/react';

// Override the default render with our custom one
export { renderWithProviders as render };
