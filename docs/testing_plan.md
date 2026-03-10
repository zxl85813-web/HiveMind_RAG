# HiveMind RAG 平台全面测试计划 (V2)

## 1. 后端测试 (Python/Pytest)

### 1.1 服务层单元测试 (Unit Tests)
*   **知识库服务 (`kb_service.py`)**: 
    *   验证 KB 创建、权限自动初始化、文档链接及其版本递增。
    *   **ACL 验证**: 模拟不同角色（Admin/User）和部门，验证跨租户访问控制。
*   **智能体服务 (`chat_service.py`)**:
    *   **Swarm 编排协议**: Mock 不同 Agent 节点，验证任务分发逻辑是否符合预期。
    *   **流式响应控制**: 验证 SSE 协议下的 Chunk 生成逻辑及异常中断处理。
*   **脱敏服务 (`security_service.py`)**:
    *   针对各种正则表达式（手机号、身份证、API Key）的识别准确率进行边界值测试。

### 1.2 API 集成测试 (Integration Tests)
*   **RAG 全链路验证**: 调用 `POST /knowledge/{kb_id}/search`，不 Mock 检索器，验证从 Query 重写到向量库检索的闭环。
*   **批处理任务控制**: 验证大批量文档上传任务的状态转换（Pending -> Indexing -> Indexed）。

---

## 2. 前端测试 (React/Vitest)

### 2.1 API 及状态测试
*   **Service 层**: 验证 `knowledgeApi.ts`、`chatApi.ts` 是否正确解析后端响应并处理 401/403 等 HTTP 状态码。
*   **Store 状态管理**: 验证 `chatStore` 在消息流式更新时的状态一致性。

### 2.2 关键组件集成 (Component Testing)
*   **`ChatPanel`**: 测试消息发送、长文本渲染、代码高亮。
*   **`AppLayout`**: 验证菜单导航跳转及 AI/传统模式切换后的组件持久化。
*   **`KnowledgeDetail`**: 模拟文件上传进度条、文档列表筛选及分页。

---

## 3. E2E 全链路测试 (Playwright)

### 3.1 核心业务流程 (Critical Paths)
*   **知识发现闭环**: 用户从仪表盘进入系统 -> 创建知识库 -> 上传 PDF 文档 -> 在右侧 Chat 面板提问 -> 验证引用标记能否正确跳转至对应文档片段。
*   **权限管控流**: 用户 A 创建私有知识库 -> 邀请用户 B 加入 -> 验证用户 B 获得权限后可搜索，而用户 C 不可见。
*   **图谱交互**: 在知识库详情页打开图谱视图 -> 点击实体节点 -> 验证右侧能展示关联的详细知识块。

### 3.2 兼容性与边界
*   测试不同屏幕尺寸（Mobile / Tablet / Desktop）下的 Chat 面板响应式表现。
*   测试网络离线/后端崩溃时的 UI 容错提示 (Error Boundaries)。

---

## 4. 系统测试 (System Integration Testing)

### 4.1 数据一致性 (Data Integrity)
*   **同步验证**: 验证文档在数据库 (`PostgreSQL`) 中逻辑删除后，向量库 (`ES`) 和图谱库 (`Neo4j`) 中的相关数据是否实时异步清理。
*   **架构审计**: 验证 AI 智能体是否遵循定义的 `app/schemas/knowledge_protocol.py` 数据协议。

### 4.2 环境依赖容错
*   模拟 `Redis` 或 `Neo4j` 宕机，验证系统是否能够降级运行（如降级为纯向量搜索），而不是全面崩溃。

---

## 5. 性能与压力测试 (Performance & Stress)

### 5.1 响应延时 (Latency)
*   **Chat 首字响应 (TTFT)**: 测量首个 SSE Chunk 返回的时间，目标：在 1M Context 下稳定在 1.5s 以内。
*   **检索耗时**: 测量 Hybrid Search（Vector + Graph）在 10 万级文档下的耗时，目标：< 500ms。

### 5.2 吞吐量 (Throughput)
*   **并发上传**: 模拟 20 个并发用户同时上传 100MB 级别文档，监视服务器 OOM 情况及 Celery 队列积压。
*   **并发对话**: 模拟 50 个并发对话流，验证向量数据库连接池和 LLM API 的限流表现。

### 5.3 资源占用分析
*   监控大规模图谱计算（Leiden 社区检测）时的 CPU 和内存峰值。

---

## 6. 成功标准 (DoD)
*   **核心功能通过率**: 100% (P0 Case)。
*   **代码覆盖率**: 后端 > 85%，前端核心 Logic > 90%。
*   **性能达标**: 关键路径延时低于设定的阈值。
*   **回归测试**: 每次 PR 必须自动运行 Playwright Smoke Tests。
