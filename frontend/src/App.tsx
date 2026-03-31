/**
 * App 根组件 — AI-First 架构。
 *
 * 核心变化:
 *   - Chat 不再是页面 (ChatPage 退役)，Chat 是永驻右侧面板
 *   - 默认首页: DashboardPage (概览)
 *   - ChatPanel 在 AppLayout 中始终渲染
 *
 * @see docs/design/ai-first-frontend.md
 * @see skills/frontend-design/SKILL.md
 */

import { lazy, Suspense, useEffect } from 'react';
import { ConfigProvider, theme, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { Routes, Route, Navigate } from 'react-router-dom';

import { XProvider } from '@ant-design/x';
import { AppLayout } from './components/common/AppLayout';
import { LoadingState } from './components/common/LoadingState';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { MockControl } from './components/common/MockControl';
import { appRoutes } from './config/appRoutes';
import { AuthGuard } from './guards/AuthGuard';
import { AccessGuard } from './guards/AccessGuard';
import { useAuthStore } from './stores/authStore';

// 🚀 [Architecture-Gate]: 路由级代码分割 (Code Splitting)
// 所有页面组件采用 React.lazy 按需加载，优化首屏 TTI。
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })));
const KnowledgePage = lazy(() => import('./pages/KnowledgePage').then(m => ({ default: m.KnowledgePage })));
const AgentsPage = lazy(() => import('./pages/AgentsPage').then(m => ({ default: m.AgentsPage })));
const StudioPage = lazy(() => import('./pages/StudioPage').then(m => ({ default: m.StudioPage })));
const LearningPage = lazy(() => import('./pages/LearningPage').then(m => ({ default: m.LearningPage })));
const AuditPage = lazy(() => import('./pages/AuditPage').then(m => ({ default: m.AuditPage })));
const EvalPage = lazy(() => import('./pages/EvalPage').then(m => ({ default: m.EvalPage })));
const FineTuningPage = lazy(() => import('./pages/FineTuningPage').then(m => ({ default: m.FineTuningPage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then(m => ({ default: m.SettingsPage })));
const BatchPage = lazy(() => import('./pages/BatchPage').then(m => ({ default: m.BatchPage })));
const SecurityPage = lazy(() => import('./pages/SecurityPage').then(m => ({ default: m.SecurityPage })));
const PipelineBuilderPage = lazy(() => import('./pages/PipelineBuilderPage').then(m => ({ default: m.PipelineBuilderPage })));
const CanvasLabPage = lazy(() => import('./pages/CanvasLabPage').then(m => ({ default: m.CanvasLabPage })));
const ArchitectureLabPage = lazy(() => import('./pages/ArchitectureLabPage'));
const TokenDashboardPage = lazy(() => import('./pages/TokenDashboardPage').then(m => ({ default: m.TokenDashboardPage })));
const KBAnalyticsPage = lazy(() => import('./pages/KBAnalyticsPage').then(m => ({ default: m.KBAnalyticsPage })));
const TracePage = lazy(() => import('./pages/TracePage').then(m => ({ default: m.TracePage })));
const ForbiddenPage = lazy(() => import('./pages/ForbiddenPage').then(m => ({ default: m.ForbiddenPage })));

const pageComponentMap = {
  dashboard: DashboardPage,
  knowledge: KnowledgePage,
  audit: AuditPage,
  security: SecurityPage,
  evaluation: EvalPage,
  finetuning: FineTuningPage,
  pipelines: PipelineBuilderPage,
  canvasLab: CanvasLabPage,
  studio: StudioPage,
  agents: AgentsPage,
  batch: BatchPage,
  learning: LearningPage,
  settings: SettingsPage,
  architectureLab: ArchitectureLabPage,
  tokenDashboard: TokenDashboardPage,
  kbAnalytics: KBAnalyticsPage,
  trace: TracePage,
} as const;

/**
 * Ant Design 全局主题 — Cyber-Refined。
 */
const appTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#06D6A0',
    colorSuccess: '#06D6A0',
    colorWarning: '#FFD166',
    colorError: '#EF476F',
    colorInfo: '#118AB2',

    colorBgContainer: '#111827',
    colorBgElevated: '#1F2937',
    colorBgLayout: '#0A0E1A',

    colorText: '#F8FAFC',
    colorTextSecondary: '#94A3B8',
    colorTextTertiary: '#475569',

    colorBorder: 'rgba(255, 255, 255, 0.08)',
    colorBorderSecondary: 'rgba(255, 255, 255, 0.05)',

    borderRadius: 10,
    borderRadiusLG: 14,
    borderRadiusSM: 6,

    fontFamily: "'Sora', -apple-system, BlinkMacSystemFont, sans-serif",
    fontSize: 14,

    padding: 16,
    paddingLG: 24,
    paddingSM: 12,
    paddingXS: 8,

    motionDurationMid: '0.25s',
  },
  components: {
    Layout: {
      headerBg: 'transparent',
      bodyBg: 'transparent',
    },
    Menu: {
      darkItemBg: 'transparent',
      darkItemSelectedBg: 'rgba(6, 214, 160, 0.12)',
      darkItemHoverBg: 'rgba(255, 255, 255, 0.04)',
      darkItemSelectedColor: '#06D6A0',
      horizontalItemSelectedColor: '#06D6A0',
    },
    Button: {
      primaryShadow: '0 2px 12px rgba(6, 214, 160, 0.3)',
    },
    Card: {
      colorBgContainer: '#111827',
    },
    Input: {
      colorBgContainer: '#1F2937',
    },
    Select: {
      colorBgContainer: '#1F2937',
    },
  },
};

function App() {
  const initProfile = useAuthStore((state) => state.initProfile);

  useEffect(() => {
    void initProfile();
  }, [initProfile]);

  return (
    <XProvider>
      <ConfigProvider theme={appTheme} locale={zhCN}>
        <AntApp>
          <ErrorBoundary>
            <Suspense fallback={<LoadingState fullScreen tip="🧩 模块载入中..." />}>
              <Routes>
                <Route path="/forbidden" element={<ForbiddenPage />} />
                <Route path="/" element={<AuthGuard><AppLayout /></AuthGuard>}>
                  {appRoutes.map((route) => {
                    const PageComponent = pageComponentMap[route.key as keyof typeof pageComponentMap];
                    if (!PageComponent) {
                      return null;
                    }

                    const guardedElement = (
                      <AccessGuard access={route.access}>
                        <PageComponent />
                      </AccessGuard>
                    );

                    if (route.path === '/') {
                      return <Route key={route.key} index element={guardedElement} />;
                    }

                    return (
                      <Route
                        key={route.key}
                        path={route.path.slice(1)}
                        element={guardedElement}
                      />
                    );
                  })}
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
          <MockControl />
        </AntApp>
      </ConfigProvider>
    </XProvider>
  );
}

export default App;
