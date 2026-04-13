# 📔 系统架构加固履历 (System Stabilization Log)

> **任务描述**: 解决前端 401/500 循环报错、修复 Swarm 核心接口异常、适配 Ant Design v6 及网络跨域连接加固
> **执行者**: HiveMind Antigravity (Senior Architect)
> **日期**: 2026-04-13
> **状态**: ✅ 已交付 (Stabilized)

---

## 📅 [2026-04-13] 紧急加固 (Hotfixes & Connectivity Hardening)

### 1. 跨域与网络连接加固 (Network Connectivity)
- **问题**: 后端响应 `net::ERR_CONNECTION_REFUSED`，主要由于 IPv6/IPv4 绑定歧义（localhost vs 127.0.0.1）导致。
- **动作**: 
  - 修改 `run.bat` 将后端绑定至 `0.0.0.0`。
  - 修改 `vite.config.ts` 将代理目标明确指向 `127.0.0.1:8000`，规避 Windows 环境下 `localhost` 解析为 `::1` 的干扰。
- **结果**: ✅ 已验证。前端可以稳定连接到后端服务。

### 2. React 渲染与规范适配 (UI Specification)
- **问题**: `Typography.Text` 误传 `block` 属性触发 React 警告；缺失 PWA 建议的 Meta 标签。
- **动作**: 
  - 将 `DashboardPage.tsx` 中的 `Text block` 替换为 `style={{ display: 'block' }}`。
  - 在 `index.html` 补全 `<meta name="mobile-web-app-capable" content="yes">`。
- **结果**: ✅ 已验证。控制台警告归零，符合 PWA 规范。

### 3. 登录权限秒级同步 (Auth & Permission Synchronization)
- **问题**: 登录后菜单项缺失或闪烁（Lagging），原因为 `initProfile` 异步滞后且 `AccessGuard` 缺少状态订阅。
- **动作**: 
  - 重构 `authStore.ts` 支持在 `setAuthenticated` 时立即注入 `user` 对象。
  - 更新 `LoginPage.tsx` 实现登录成功后的即时 Profile 填充。
  - 在 `AccessGuard.tsx` 中增加 `profile` 监听，确保路由守卫能即时响应权限变更。
- **结果**: ✅ 已验证。管理员登录后可立即看到全量菜单，无滞后感。

---

## 🕒 现状剖析 (Diagnosis)
- **核心痛点 1**: 后端 `/api/v1/agents/swarm/stats` 报 500 错误，导致前端 Dashboard 无法显示且触发 CORS 异常。
- **核心痛点 2**: 前端 401 认证失败后进入重定向死循环，控制台充满警告。
- **技术债**: 升至 Ant Design v6 后，大量 `message` 字段弃用，`List` 组件面临移除风险。

---

## 🔄 动作日记 (Action Log)

### 1. 后端核心修复 (AttributeError & Exception Governance)
- **动作**: 
  - 修复 `SwarmOrchestrator` 类在重构中丢失的 `get_agents()` 和 `invoke_stream()` 方法。
  - 在 `main.py` 注入 `register_exception_handlers`，确保非预期错误也能返回合规的 `ApiResponse` 格式并保持跨域头。
- **结果**: ✅ 已验证。通过 `scratch/debug_stats.py` 确认接口响应恢复正常（200 OK）。

### 2. 前端 401 处理锁加固 (Auth Loop Protection)
- **动作**: 
  - 在 `api.ts` 拦截器中引入 `window.isAuthRedirecting` 标记位。
  - 强制清除 `tokenVault` 并中止所有并发连接，确保单一重定向路径。
- **结果**: ✅ 已验证。死循环现象消除。

### 3. Ant Design v6 渐进式适配 (UI Refactoring)
- **动作**: 
  - **通知字段转换**: 全量将 `notification.error({ message: ... })` 替换为 `title:`，消除控制台警告。
  - **组件迁移**: 将 `DashboardPage.tsx` 中的已弃用 `List` 组件重构为基于 `Flex` 的现代列表布局。
- **样式增强**: 在 `DashboardPage.module.css` 增加了 `.reportItem` 悬停动效。
- **结果**: ✅ 已验证。控制台警告归零，UI 视觉动效提升。

### 4. 菜单渲染与角色权限回归 (Menu & Role Fixes)
- **动作**: 
  - **图标映射补全**: 补全 `AppLayout.tsx` 中缺失的 8 个 Ant Design 图标映射（架构实验室、Token 大屏等），防止 UI 渲染异常。
  - **Mock 角色对齐**: 修复 `MockControl.tsx` 中角色标识符（Operator/Viewer）与权限引擎（admin/user/readonly）不匹配的问题，确保切换 Admin 后能看到全量菜单。
  - **i18n 标准化**: 为所有受保护路由增加了对应的 `nav.*` 翻译项，移除硬编码中文标签。
- **结果**: ✅ 已验证。侧边栏在 Classic 模式下通过 Admin 身份可显示完整 15+ 项菜单。

---

## 📈 治理成效 (Outcomes)
- [x] 后端服务健康度恢复，`stats` 端点恢复。
- [x] 全局异常捕获机制上线。
- [x] 前端 UI 兼容性警告清零。
- [x] API 响应格式完全标准化。

---

## 🚀 遗留与后续 (Post-Mortem)
- **同步**: 建议运行 `python scripts/sync_governance_to_graph.py` 刷新图谱。
- **监控**: 继续观察 `MonitorService` 是否有新的 4xx 异常捕获。
