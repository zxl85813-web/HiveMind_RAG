# ⚛️ 前端核心治理与韧性架构 (Frontend Resilience & Governance)

> 本文档定义了 HiveMind RAG 前端在容错处理、日志溯源、稳定性建设及实时保护方面的技术规范与演进路径。

---

## 1. 容错架构 (Fault Tolerance)

### 1.1 颗粒度错误边界 (Error Boundaries)
*   **状态**: ✅ 已实现 (Global & Schema-Aware)
*   **机制**:
    *   使用 `src/components/common/ErrorBoundary.tsx` 拦截 React 渲染崩溃。
    *   **Schema 联动**: 异常触发后自动通过 `AppError.fromCrash` 包装，并调用 `MonitorService` 上报。
    *   **策略**: 隔离受灾面。全局边界守住底线，局部边界保护核心（如：图谱崩溃不影响对话面板）。
    *   **自愈**: 降级 UI 接入 `window.location.reload()` 及状态重置 Hook。

### 1.2 鉴权与权限拦截
*   **状态**: ✅ 已实现
*   **机制**:
    *   `AuthGuard`: 路由级强制跳转至 Login。
    *   `AccessGuard`: 基于角色的功能位屏蔽，配合 `PermissionButton` 实现 UI 级防御。

---

## 2. 实时系统保护 (Real-time Protection)

### 2.1 混合通信链路韧性
*   **SSE 保护**: 基于 `@microsoft/fetch-event-source` 的 `useSSE.ts` 支持 POST 请求、自动重连与 AbortController 信号控制。
*   **WebSocket 退避机制**: `useWebSocket.ts` 实现了指数级重连退避，防止在网络震荡期瘫痪浏览器标签页。

### 2.2 数据流防腐 (Anti-Corruption Layer)
*   **后端感知**: 响应拦截器统一对 `4xx/5xx` 返回进行 UI 通知（AntD Notification），不通过异常数据污染 Store。
*   **类型安全**: 强制 TypeScript 全链路定义，严禁在渲染层使用 `any` 访问深度嵌套字段。

---

## 3. 日志与可观测性 (Observability)

### 3.1 Schema-Driven 监控体系 (Monitoring)
*   **状态**: ✅ 已实现
*   **核心组件**:
    *   `src/core/schema/monitoring.ts`: 基于 Zod 定义标准的 `MonitorEvent` 契约。
    *   `src/hooks/useMonitor.ts`: 组件级埋点 Hook，支持 `track`（动作）与 `report`（异常）。
    *   `MonitorService`: 统一上报收口，支持本地开发日志输出与生产环境（规划中）Sentry 转发。

### 3.2 结构化异常管理 (Exceptions)
*   **状态**: ✅ 已实现
*   **实现**: 
    *   `AppError`: 继承原生 `Error`，强制绑定 `code` (ErrorCode)、`layer` 和 `severity`。
    *   `safeValidate`: 基于 Zod 的 Anti-Corruption Layer (ACL)，在 API 数据流入业务层前进行 Schema 校验。

### 3.3 生产级 APM 接入 (Sentry)
*   **状态**: ✅ 已实现
*   **实现**: 
    *   集成 `@sentry/react`。
    *   `MonitorService` 自动将 `reportError` 转发至 Sentry，并附加结构化 Tag（error_code, layer）。
    *   开启 Browser Tracing 与 Session Replay，感知长任务与渲染异常。

### 3.4 全链路统一日志协议 (Unified Logging Protocol)
*   **状态**: 🚀 已落地 (V1.0)
*   **定义**: 为实现前后端日志对齐，所有系统日志需遵循统一 JSON 结构。
*   **示例**:
    ```json
    {
      "ts": "2026-03-25T07:31:57Z",
      "level": "ERROR",
      "trace_id": "uuid-xxx-xxx",
      "platform": "FE",
      "category": "error",
      "module": "ChatPanel",
      "action": "send_message",
      "msg": "Failed to send message",
      "meta": { "error_code": "TIMEOUT" },
      "env": "production"
    }
    ```

---

## 4. 稳定性建设 (Stability Construction)

### 4.1 故障演练中心 (Mock Control)
*   **状态**: ✅ 已实现
*   **核心功能**: 允许架构师手动切换 `ERROR_500`、`LONG_LATENCY`、`MALFORMED_DATA` 等场景，验证前端在断路状态下的交互反馈。

### 4.2 [ planned ] 数据 Fetching 标准化
*   **目标**: 淘汰 `useEffect` 手写请求，全面通过 **TanStack Query (React Query)** 收口。
*   **收益**: 获得自动缓存管理、SWR 机制及请求防抖，消除数据加载抖动。

---

### 4.3 i18n-Agent 桥接协议 (i18n Bridge)
*   **状态**: ✅ 已实现
*   **机制**:
    *   **前端**: 在 `api.ts` 与 `chatApi.ts` 中通过 `Accept-Language` 请求头透传 `i18next.language`。
    *   **后端**: `ChatService` 提取 header 并注入 Swarm 运行上下文。
    *   **Prompt 注入**: 在 `PromptEngine` 的基座模板（Supervisor/Agent/Reflection）中动态加入 **LANGUAGE** 约束，强制 LLM 按前端语种回复。
    *   **质量闭环**: Reflection 节点自动校验回复语种与请求语种的一致性。

---

### 4.4 PWA / 离线协同 (Offline Strategy)
*   **状态**: ✅ 已实现
*   **机制**:
    *   **Service Worker**: 使用 `vite-plugin-pwa` 自动生成。采用 `autoUpdate` 策略，支持新版本提示。
    *   **缓存策略**: 
        *   静态资源 (JS/CSS/HTML): 自动预缓存。
        *   外部资源 (Google Fonts): 采用 `CacheFirst` 策略。
    *   **清单文件**: 部署 `manifest.webmanifest`，支持 Web App 安装 (A2HS)。
    *   **UI 反馈**: `main.tsx` 中集成升级提示逻辑与离线就绪通知。

---

## 5. 待建设路线图 (Roadmap)

| 任务 ID | 描述 | 优先级 | 备注 |
| :--- | :--- | :--- | :--- |
| **FE-GOV-001** | **全量接入 React Query** | P0 | 解决重复请求与状态不一致问题 |
| **FE-GOV-002** | **Sentry / APM 部署** | ✅ | 已通过 MonitorService 完成生产级接入 |
| **FE-GOV-003** | **i18n-Agent 桥接协议** | ✅ | 已通过 Accept-Language Header 透传并注入 Prompt |
| **FE-GOV-004** | **可视化库代码分割优化** | ✅ | 针对 G6/X6/ForceGraph 进行组件级 React.lazy 载入，优化 TTI |
| **FE-GOV-005** | **PWA/离线资源缓存** | ✅ | 部署 Service Worker 与 Manifest，支持 Google Fonts 离线缓存与应用安装 |

---

> 📏 **架构契约**: 任何破坏上述韧性机制的代码（如移除 ErrorBoundary 或绕过 API 拦截器）在 CR 阶段应被直接拒绝。
