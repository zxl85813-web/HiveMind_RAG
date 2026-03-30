# 🧪 Graph-Driven E2E 测试规范与模式 (Testing Patterns)

## 1. 核心原则
- **拒绝硬编码**: 测试数据必须通过 Factory 动态生成，避免依赖特定的 ID 或状态。
- **状态清理**: 测试前后必须清理副作用，使用 `yield` 配合 `clean_test_db` Fixture。
- **端到端边界**:
  - API 层测试: 必须使用 `TestClient` 或 `AsyncClient` 发起真实的 HTTP 请求，不要直接调用 Service Layer（除非图谱指示需要绕过 API）。
  - Frontend 层测试: (如果是集成代码层级) 检查 Store State 的变化。
  
## 2. Mock 规范 (Mocking Strategy)
根据图谱中的节点类型进行精准 Mock：
- **APIEndpoint**: 发起真实网络请求 (TestClient)。
- **Service 层 (外部依赖)**: 必须 Mock Neo4j/LLM 等外部调用网关。
  - 例如：`@patch("app.services.rag_gateway.RAGGateway.retrieve")`
- **DatabaseModel**: 尽量使用真实的测试数据库 (`pytest.fixture: clean_test_db`)，确保 SQL 约束、触发器被真实验证。

## 3. 业务流转断言 (Flow Assertions)
不要只测 200 OK。根据图谱链路，必须断言**副作用**：
- 如果图谱中有 `DatabaseModel`，断言数据库记录是否新增。
- 如果图谱中有 `UI_State`，描述如何验证返回的 Payload 符合 UI State 的预期解构。
- 如果图谱中有 `MetricNode` (可观测性记录)，如果业务包含审计或监控，必须断言 `record_trace` 方法被调用。
