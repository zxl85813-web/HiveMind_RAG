/**
 * App 根组件 — AI-First 架构 + 平台模式适配。
 *
 * 根据后端 PLATFORM_MODE 动态注册路由:
 *   - "rag"   → 知识库、评测、微调、Pipeline 等 RAG 页面
 *   - "agent" → Agent 蜂巢、Studio、批处理等 Agent 页面
 *   - "full"  → 全部页面
 *
 * @see docs/design/ai-first-frontend.md
 */

import { lazy, Suspense } from 'react';
import { ConfigProvider, theme, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { Routes, Route } from 'react-router-dom';

import { XProvider } from '@ant-design/x';
import { AppLayout } from './components/common/AppLayout';
import { LoadingState } from './components/common/LoadingState';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { MockControl } from './components/common/MockControl';
import { usePlatformStore } from './stores/platformStore';

// 🚀 [Architecture-Gate]: 路由级代码分割 (Code Splitting)
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
const ExportWizardPage = lazy(() => import('./pages/ExportWizardPage').then(m => ({ default: m.ExportWizardPage })));
const UsagePage = lazy(() => import('./pages/UsagePage').then(m => ({ default: m.UsagePage })));

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
  const { ragEnabled, agentEnabled } = usePlatformStore();

  return (
    <XProvider>
      <ConfigProvider theme={appTheme} locale={zhCN}>
        <AntApp>
          <ErrorBoundary>
            <Suspense fallback={<LoadingState fullScreen tip="🧩 模块载入中..." />}>
              <Routes>
                <Route path="/" element={<AppLayout />}>
                  {/* Dashboard — 始终可用 */}
                  <Route index element={<DashboardPage />} />

                  {/* SHARED — 始终可用 */}
                  <Route path="audit" element={<AuditPage />} />
                  <Route path="security" element={<SecurityPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                  <Route path="export" element={<ExportWizardPage />} />
                  <Route path="usage" element={<UsagePage />} />

                  {/* RAG MODULE — 知识库、评测、微调、Pipeline、学习 */}
                  {ragEnabled && (
                    <>
                      <Route path="knowledge" element={<KnowledgePage />} />
                      <Route path="evaluation" element={<EvalPage />} />
                      <Route path="finetuning" element={<FineTuningPage />} />
                      <Route path="pipelines" element={<PipelineBuilderPage />} />
                      <Route path="learning" element={<LearningPage />} />
                    </>
                  )}

                  {/* AGENT MODULE — Agent 蜂巢、Studio、批处理、生成 */}
                  {agentEnabled && (
                    <>
                      <Route path="agents" element={<AgentsPage />} />
                      <Route path="studio" element={<StudioPage />} />
                      <Route path="batch" element={<BatchPage />} />
                    </>
                  )}
                </Route>
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
