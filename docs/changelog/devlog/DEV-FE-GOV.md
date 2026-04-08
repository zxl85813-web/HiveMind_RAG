# DEV-FE-GOV: Frontend Architecture Governance & Rigorous Testing

| 字段 | 值 |
|------|------|
| **关联需求** | REQ-FE-002: Multi-User Isolation & Governance |
| **开始时间** | 2026-04-08 03:35 |
| **状态** | ✅ 已完工 (Harness Hardened) |

| # | 子任务 | 文件 | 状态 | 耗时 |
|---|--------|------|------|------|
| 1 | **测试数据集定义** | `frontend/e2e/data/mock_users.ts` | ✅ | 0.2h |
| 2 | **场景 1：并发会话隔离** | `frontend/e2e/multi_user_isolation.spec.ts` | ✅ | 0.5h |
| 4 | **场景 4：追踪链路对账** | `frontend/e2e/multi_user_isolation.spec.ts` | ✅ | 0.3h |
| 5 | **场景 5：401 故障级联** | `frontend/e2e/cascade.spec.ts` | ✅ | 0.6h |

## 开发日志

### Step 1: 数据集定义
**时间**: 03:40
**决策**: 引入 `TEST_PERSONAS` 常量，包含每个用户的 `expectedDbName`，用于物理存储对账。

### Step 2: 场景发现 (Graph-Informed)
**时间**: 04:10
**观察**: 尽管索引器在 TS 语法解析上存在版本偏差，但通过直接审计 `ChatPanel.tsx` 确认了 `useAuthStore` 是核心感知点。
**路径决策**: 测试必须覆盖 UI 渲染（Profile 显示）、持久化（IndexedDB 名）和网络层（Abort 信号）三个维度。
### Step 3: Harness 实现与 401 级联
**时间**: 06:40
**决策**: 发现 `api.ts` 拦截器仅清除 Token 但未断开长连接。通过 `connectionManager.abortAll()` 修复该治理漏洞，并在 `cascade.spec.ts` 中通过 `page.route` 模拟 401 验证熔断行为。

---
