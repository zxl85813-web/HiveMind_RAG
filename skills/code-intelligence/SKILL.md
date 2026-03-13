---
name: code-intelligence
description: "用于代码库的深度分析、影响评估和逻辑解构。当用户询问：‘修改 X 会影响哪里？’、‘解释这段复杂的异步逻辑’、‘分析某个类的依赖树’时使用。它超越了简单的搜索，专注于代码的语义关联和副作用分析。"
---

# Code Intelligence Skill

该 Skill 旨在增强对大规模代码库的理解，特别是处理复杂的异步逻辑、跨模块调用和隐式依赖。

## 1. 深度分析模式 (Deep Analysis Patterns)

### A. 架构拓扑扫描 (Architecture Topology)
当你被要求“理解某个模块”时，不要只看代码，要看拓扑：
1. **入口追踪**：识别谁在直接调用这个 Entry Point（是 API Route 还是异步任务？）。
2. **状态流转**：追踪 `SQLModel` 对象从数据库取出后，经过了哪些 Service 修改，最终如何返回。
3. **资源绑定**：识别该模块强依赖的基础设施（如它是依赖 Elasticsearch 进行向量检索，还是依赖 Neo4j 存储图关系？）。

### B. 级联影响评估 (Impact Cascading)
在修改代码前执行“影子评估”：
- **静态分析**：使用 `grep_search` 查找所有显式调用。
- **隐式关联**：检查 `REGISTRY.md` 中的登记信息，确认是否有动态注册的 Hook 或 Event Listener 关联。
- **破坏性检查**：如果修改了 `schemas/` 中的 Pydantic 模型，必须列出所有受影响的前端组件。

### C. 逻辑解构与可视化
对于复杂的业务流程（如 `memory_compression_design.md` 的实现）：
- **翻译**：将复杂的异步处理链翻译为步骤明确的伪代码或 Mermaid 图。
- **边界识别**：明确指出哪些逻辑是在 `Main Process` 中运行，哪些是跑在 `BackgroundTask` 中。

## 2. 强制审计项 (Audit Checklist)

在进行 Code Review 或解答架构问题时，必须对照以下“红线”：
- **Layer Violation**：是否存在 Service 直接调 API，或 API 直接调 DB 驱动？
- **Sync in Async**：在 `async` 函数中是否存在没加 `await` 的阻塞型磁盘或网络 IO？
- **Log Hygiene**：错误捕获是否只写了 `print` 而没用 `logger.exception`？

## 3. 工具组合策略 (Tool Combinations)

| 意图 | 推荐链式操作 |
|------|------------|
| **找 Bug 原因** | `grep_search` (查错误日志关键字) -> `view_file` (分析上下文) -> `code-intelligence` (推导因果) |
| **重构建议** | `find_by_name` (查相关类) -> `code-intelligence` (分析耦合度) -> 编写重构方案 |
| **版本 PK** | 针对新旧代码运行 `skill-creator` 的 `comparator.md` 进行盲测分析 |

## 4. 指令模式 (Standard Response Format)

当用户询问影响分析时，**必须**按以下格式回答：
1. **直接受影响 (Direct)**：文件名 + 行号 + 变更点。
2. **级联影响 (Indirect)**：受影响的下游 API 或前端页面。
3. **风险系数 (Risk Level)**：高/中/低，并说明理由。
4. **测试建议 (Testing)**：建议运行的具体测试用例。
