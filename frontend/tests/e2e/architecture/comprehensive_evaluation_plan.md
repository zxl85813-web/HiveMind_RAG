# HiveMind 前端架构重构 — 深度压测与评估计划 (QA-Ops)

> **核心目标**: 超越功能层面的测试，从"容量极限"、"混沌网络"、"系统长效稳定性"三个维度，用真实且极端的测试数据去"拷问"我们新上线的每一层架构。

---

## 评估阶段 1: 边界容量与性能退化测试 (IndexedDB 极限)
*针对 Phase 2 (Local Edge Engine) 的深度测评*

**当前盲点**: 测试只有 1 条数据，无法暴露主线程卡顿和游标查询的性能拐点。

### 1.1 大数据量造数方案 (Mocking Strategy)
- **工具**: 编写一个 Playwright Fixture，利用 `@faker-js/faker` 注入海量模拟数据。
- **数据矩阵**:
  - `Dataset A`: 50 个高频极简对话 (每个对话 2-3 轮，短文本)。
  - `Dataset B`: 1,000 个沉寂历史对话 (测试 `useChatQuery` 列表渲染的虚拟化/分页能力)。
  - `Dataset C`: 5 个极端超长对话 (每个对话含 200 个轮次，单条消息含 10,000+ Tokens，夹杂巨大 Markdown/代码块)。

### 1.2 测评用例 (Test Cases)
*   **用例 1.2.1: Cold Boot Time (冷启动耗时)**: 在注入 `Dataset B` (1000条数据) 的沙盒下，用 Chrome DevTools Performance 协议强制捕捉页面卸载到侧边栏初次渲染的耗时。若 `>300ms` 即视为不达标。
*   **用例 1.2.2: IDB Long Task 卡顿 (主线程剥夺)**: 当写入 `Dataset C` 的超长消息到 IndexedDB 时，捕捉浏览器是否有超过 `50ms` 的 Long Task，验证是否需要将 IndexedDB 写入转移至 Web Worker。
*   **用例 1.2.3: Storage Quota 踩踏**: 用脚本持续往 IndexedDB 塞入大文件或 Base64 图片直至触碰浏览器 (如 Safari 的 50MB) 储存上限，验证系统的 LRU (Least Recently Used) 淘汰机制是否会正常将最旧的对话驱逐出本地空间，且不触发前端崩溃。

---

## 评估阶段 2: 混沌工程与流式韧性矩阵 (Chaos Matrix)
*针对 Phase 3 (弹性流层) 的深度测评*

**当前盲点**: 仅测试了干脆的 `setOffline(true)`，未涉及半死不活的弱网风暴和恶意 Payload。

### 2.1 网络风暴矩阵模拟
利用 Playwright 的 `page.route` 和第三方网关代理 (如 Toxiproxy 构建测试拓扑)：
- 🌀 **场景 A (慢速 3G 的持续折磨)**: 全程节流下载速率到 50kbps，验证 UI 的逐字渲染是否有迟滞感，组件的 React 渲染频率是否因节流而失控。
- 🌀 **场景 B (网络抖动与 TCP 丢包)**: 每隔 2 秒断开并立即重连一次。验证 `StreamManager` 是否会陷入死循环，或者因多次建立并发请求导致服务器资源耗尽。
- 🌀 **场景 C (TTFB 极限超时)**: AI 思考了整整 45 秒才吐出第一个 Token，验证浏览器的原生请求超时与 `fetchEventSource` 的存活策略，确保它不会过早抛出 `AbortError`。
- 🌀 **场景 D (服务端 429 风暴)**: 服务端故意连续返回 3 次 `429 Too Many Requests`，验证 `LLMHealthMonitor` 的状态转换 (`DEGRADED` -> `CRITICAL`) 是否正常熔断，并弹出对用户友好的错误页，而非直接抛出前端控制台红字。

### 2.2 恶意数据结构 (Payload Fuzzing)
- **残缺 JSON**: 后端在 `MultiTrackParser` 等待一个 `status` 更新时，由于 Nginx 截断，故意吐出不完整的 JSON `{ "type": "status", "cont`。验证 Parser 的 `try-catch` 是否稳固，是否能将受损块降级处理或安全丢弃，而非导致整条流崩溃。

---

## 评估阶段 3: 长效稳定性与内存剖析 (Memory Profiling)
*针对整体架构改动的长时间运转稳定性*

**当前盲点**: 所有的自动化脚本均在 30 秒内执行完毕，掩盖了 React Hook 闭包泄漏或事件监听器遗留问题。

### 3.1 “不死鸟”马拉松脚本 (Endurance Testing)
- **执行方式**: Playwright 针对同一个页面实例，执行一个 **“发送请求 -> 接收回答 -> 点开另一条历史数据”** 的超级循环，重复 **500 次**，持续时长约 2-3 小时。
- **采集指标**:
  - 每隔 50 轮探测一次 `performance.memory.usedJSHeapSize`。
  - 使用 Chrome DevTools Protocol (CDP) 捕获 `DOM Nodes` 和 `JS Event Listeners` 的数量。
- **验收标准 (Pass/Fail)**:
  - 如果 JS Heap 从基础的 `30MB` 阶梯式增长一直爬升到 `200MB+` 且 GC(垃圾回收) 无法将其压回，即证明存在内存泄露 (大概率在 `MultiTrackParser.handlers` 未被注销，或 `Zustand` 状态未清理)。
  - 如果 DOM Node 数量呈现线性无尽增长，证明历史对话切换时，旧组件未被正常卸载。

---

## 评估阶段 4: 前后端全栈遥测的一致性审计 (Telemetry Audit)
*针对 Phase 1 (AI Telemetry) 的深度测评*

### 4.1 数据对账 (Reconciliation Test)
- **断头台场景**: 当 AI 流刚输出完 `[metrics]` 轨道（即响应完成），Playwright 立即极其暴力地调用 `page.close()` 关闭标签页。
- **验证目的**: 用户在看到结果后秒关页面，此时 `BaselineProbe` 的埋点数据会不会丢失？验证基于 `navigator.sendBeacon()` 或 `fetch(keepalive: true)` 机制的退场埋点是否能100%安全抵达后端。
- **如何证明**: 自动化脚本关闭前端页面后，再去查询后端的测试数据库对应的埋点记录，确保它未掉单。

---

### 下一步行动指南 (Next Steps)
为了执行上述计划，我们需要补充一些专用的测试工具，特别是:
1. `faker-builder.ts`: 用于往 IndexedDB 瞬间注水造数据的工具。
2. `chaos-network-interceptor.ts`: 利用 Playwright 的 CDP 会话创建更底层的网络波动干预工具。

我们是否需要先挑选一个**痛点最高**的阶段（例如：**评估阶段 1: 大数据量内存并发** 或是 **评估阶段 2: Payload 破坏测试**），让我立刻为您编写相应的极客级压测探测脚本？
