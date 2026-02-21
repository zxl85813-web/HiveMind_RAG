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

import { ConfigProvider, theme, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/common/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { AgentsPage } from './pages/AgentsPage';
import { StudioPage } from './pages/StudioPage';
import { LearningPage } from './pages/LearningPage';
import { SettingsPage } from './pages/SettingsPage';

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
  return (
    <ConfigProvider theme={appTheme} locale={zhCN}>
      <AntApp>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            {/* Dashboard 是默认首页 */}
            <Route index element={<DashboardPage />} />
            {/* 功能页面 — Chat Panel 始终跟随 */}
            <Route path="knowledge" element={<KnowledgePage />} />
            <Route path="agents" element={<AgentsPage />} />
            <Route path="studio" element={<StudioPage />} />
            <Route path="learning" element={<LearningPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </AntApp>
    </ConfigProvider>
  );
}

export default App;
