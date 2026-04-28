# 🧪 HiveMind RAG — 测试策略与执行计划

> 关联文档:
> - [分支策略](../architecture/branch-strategy.md) — CI Pipeline 对应矩阵
> - [测试报告体系](./test-reporting-guide.md) — Allure + SonarQube 基础设施
> - [CI Workflows](../../.github/workflows/) — GitHub Actions 配置

---

## 1. 现状评估 (As-Is)

### 1.1 已有基础设施 ✅
- **CI Pipelines**: 6 个 workflow 已配置（feature/develop/release/main/sonarqube/allure）
- **后端框架**: pytest + pytest-asyncio + pytest-cov + allure-pytest
- **前端框架**: Vitest + Playwright (E2E)
- **报告**: Allure 聚合报告 → GitHub Pages, SonarQube 代码质量扫描
- **覆盖率门槛**: CI 要求 ≥ 80%

### 1.2 缺口 ⚠️
| 缺口 | 影响 | 优先级 |
|------|------|--------|
| 后端仅 7 个测试文件，覆盖率远低于 80% | CI 必定失败 | P0 |
| 前端 0 个组件测试 | CI 必定失败 | P0 |
| conftest.py 导入整个 app，收集极慢 | 开发体验差 | P1 |
| 无 API 契约测试 | 前后端接口不一致风险 | P2 |
| E2E 测试框架在但用例空 | release-ci 无法跑 E2E | P2 |

---

## 2. 测试金字塔 (Test Pyramid)

```
          ╱  E2E (Playwright)  ╲          ← 少量关键路径
         ╱  Integration Tests   ╲         ← API 路由 + DB 交互
        ╱   Unit Tests (Core)    ╲        ← 大量，快速，隔离
       ╱  Static Analysis (Lint)  ╲       ← Ruff + ESLint + Mypy
      ╱─────────────────────────────╲
```

**目标比例**: Unit 70% / Integration 20% / E2E 10%

---

## 3. 后端测试计划

### 3.1 目录结构规范

```
backend/tests/
├── conftest.py              # 全局 fixtures (轻量化，不导入 app)
├── unit/                    # 单元测试 (mock 所有外部依赖)
│   ├── conftest.py          # unit 专用 fixtures
│   ├── services/            # Service 层测试
│   │   ├── test_chat_service.py
│   │   ├── test_knowledge_service.py
│   │   ├── test_tag_service.py
│   │   ├── test_learning_service.py
│   │   ├── test_cache_service.py
│   │   ├── test_rag_gateway.py
│   │   ├── test_audit_service.py
│   │   ├── test_security_service.py
│   │   ├── knowledge/
│   │   ├── memory/
│   │   ├── retrieval/
│   │   └── ingestion/
│   ├── agents/              # Agent/Swarm 逻辑测试
│   ├── models/              # Pydantic Schema 验证
│   ├── auth/                # JWT / 权限逻辑
│   ├── utils/               # 工具函数测试
│   └── skills/              # Skill 纯函数测试
├── integration/             # 集成测试 (真实 DB, mock LLM)
│   ├── conftest.py          # 集成测试 fixtures (async DB setup)
│   ├── test_knowledge_api.py
│   ├── test_chat_api.py
│   ├── test_auth_api.py
│   └── test_tag_api.py
└── e2e/                     # 端到端 (预留, Playwright 或 httpx)
```

### 3.2 优先级排序 (按业务价值 × 风险)

#### P0 — 必须先写 (CI 能跑通)
| 模块 | 测试文件 | 测试点 | 预估用例数 |
|------|---------|--------|-----------|
| Auth/JWT | `unit/auth/test_security.py` | token 生成/验证/过期/刷新 | 8-10 |
| Knowledge CRUD | `unit/services/test_knowledge_service.py` | KB 创建/列表/删除/权限 | 10-12 |
| Chat Service | `unit/services/test_chat_service.py` | 会话 CRUD, 消息发送, 流式 | 8-10 |
| Tag Service | `unit/services/test_tag_service.py` | 标签 CRUD, 关联, 自动标签 | 6-8 |
| RAG Gateway | `unit/services/test_rag_gateway.py` | 检索路由, 熔断, 降级 | 6-8 |
| Schemas | `unit/models/test_schemas.py` | 请求/响应模型验证 | 10-15 |

#### P1 — 核心业务逻辑
| 模块 | 测试文件 | 测试点 | 预估用例数 |
|------|---------|--------|-----------|
| Retrieval Pipeline | `unit/services/retrieval/` | 各 Step 独立测试 | 10-12 |
| Ingestion Pipeline | `unit/services/ingestion/` | 解析/分块/向量化 | 8-10 |
| Memory Tiers | `unit/services/memory/` | T1 抽象/T2 图谱 | 8-10 |
| Agent Swarm | `unit/agents/test_swarm.py` | 路由/调度/状态管理 | 6-8 |
| Cache Service | `unit/services/test_cache_service.py` | 语义缓存命中/失效 | 5-6 |
| Audit Service | `unit/services/test_audit_service.py` | 审计日志记录 | 4-5 |

#### P2 — 集成测试
| 模块 | 测试文件 | 测试点 |
|------|---------|--------|
| Knowledge API | `integration/test_knowledge_api.py` | 完整 CRUD 流程 + DB |
| Chat API | `integration/test_chat_api.py` | 对话创建 → 消息 → SSE |
| Auth API | `integration/test_auth_api.py` | 注册 → 登录 → 鉴权 |

### 3.3 conftest.py 重构原则

```python
# 问题: 当前 conftest.py 在 import 时加载整个 app，导致收集极慢
# 方案: 分层 conftest，unit 测试不导入 app

# tests/conftest.py — 仅放通用 markers 和 session 配置
# tests/unit/conftest.py — mock factories, 不导入 app
# tests/integration/conftest.py — 真正导入 app, 创建 TestClient + async DB
```

### 3.4 Mock 策略

| 依赖 | Unit 测试 | Integration 测试 |
|------|----------|-----------------|
| Database (PostgreSQL) | ✅ Mock AsyncSession | 🔶 SQLite in-memory |
| LLM API (ZhipuAI等) | ✅ Mock 固定返回 | ✅ Mock 固定返回 |
| ChromaDB | ✅ Mock VectorStore | 🔶 真实 Chroma (临时目录) |
| Redis | ✅ Mock / fakeredis | 🔶 fakeredis |
| Neo4j | ✅ Mock Driver | ❌ 跳过 (需要真实实例) |
| Celery | ✅ eager mode | ✅ eager mode |
| 文件系统 | ✅ tmp_path fixture | ✅ tmp_path fixture |

---

## 4. 前端测试计划

### 4.1 目录结构

```
frontend/src/
├── components/
│   ├── ChatPanel/
│   │   ├── ChatPanel.tsx
│   │   └── ChatPanel.test.tsx      ← 组件测试
│   ├── KnowledgeDetail/
│   │   └── KnowledgeDetail.test.tsx
│   └── ...
├── hooks/
│   ├── useChat.ts
│   └── useChat.test.ts             ← Hook 测试
├── services/
│   ├── api.ts
│   └── api.test.ts                 ← API 层测试
└── stores/
    └── store.test.ts               ← 状态管理测试
```

### 4.2 优先级

#### P0 — 核心交互
| 组件/模块 | 测试点 |
|----------|--------|
| `useChat` hook | 消息发送/接收, SSE 连接, 错误处理 |
| `ChatPanel` | 渲染, 输入, 发送, 流式显示 |
| API Service | 请求封装, 错误处理, Token 注入 |

#### P1 — 业务页面
| 组件/模块 | 测试点 |
|----------|--------|
| `KnowledgePage` | 列表渲染, 创建, 搜索 |
| `KnowledgeDetail` | 文件上传, 文档列表, 标签 |
| `AgentsPage` | Agent 列表, DAG 可视化数据 |

#### P2 — 通用组件
| 组件/模块 | 测试点 |
|----------|--------|
| `ErrorDisplay` | 各种错误类型渲染 |
| `LoadingState` | 加载态显示 |
| `ConfirmAction` | 确认/取消交互 |

---

## 5. CI 集成矩阵 (与分支策略对齐)

| 分支 | Lint | Type | Unit | Integration | E2E | Coverage Gate |
|------|------|------|------|-------------|-----|---------------|
| `feature/*` PR | ✅ | ✅ | ✅ | ❌ | ❌ | 80% (unit only) |
| `develop` push | ✅ | ✅ | ✅ | ✅ | ❌ | 80% (all) |
| `release/*` PR | ✅ | ✅ | ✅ | ✅ | ✅ | 80% (all) |
| `main` push | ✅ | ✅ | ✅ | ✅ | ✅ | 80% (all) |

### 5.1 pytest markers 配置

```ini
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: 单元测试 (快速, 无外部依赖)",
    "integration: 集成测试 (需要 DB)",
    "e2e: 端到端测试",
    "slow: 慢速测试 (> 5s)",
]
```

### 5.2 CI 中的测试命令

```bash
# feature-ci: 仅 unit
pytest tests/unit/ -m "not slow" --cov=app --cov-fail-under=80

# develop-ci: unit + integration
pytest tests/ -m "not e2e" --cov=app --cov-fail-under=80

# release-ci: 全量
pytest tests/ --cov=app --cov-fail-under=80
```

---

## 6. 执行路线图

### Phase 1: 基础设施 (Day 1) 🔧
- [ ] 重构 `conftest.py` 分层 (root / unit / integration)
- [ ] 配置 pytest markers
- [ ] 验证 `pytest tests/unit/` 能在 < 5s 内收集完成
- [ ] 临时将 CI coverage gate 调为 50%，避免阻塞开发

### Phase 2: 后端 P0 单元测试 (Day 2-3) 🐍
- [ ] `test_security.py` — Auth/JWT
- [ ] `test_knowledge_service.py` — 知识库 CRUD
- [ ] `test_chat_service.py` — 对话核心
- [ ] `test_tag_service.py` — 标签系统
- [ ] `test_rag_gateway.py` — RAG 网关
- [ ] `test_schemas.py` — 数据模型验证
- [ ] 目标: 覆盖率 ≥ 50%

### Phase 3: 后端 P1 + 前端 P0 (Day 4-5) ⚛️
- [ ] 后端 Retrieval / Ingestion / Memory 测试
- [ ] 前端 `useChat` hook 测试
- [ ] 前端 `ChatPanel` 组件测试
- [ ] 前端 API Service 测试
- [ ] 目标: 后端覆盖率 ≥ 65%, 前端覆盖率 ≥ 40%

### Phase 4: 集成测试 + 覆盖率冲刺 (Day 6-7) 🚀
- [ ] 后端 Integration 测试 (Knowledge API, Chat API, Auth API)
- [ ] 前端业务页面测试
- [ ] 目标: 全线覆盖率 ≥ 80%, CI 全绿

### Phase 5: E2E + 持续维护 (Day 8+) 🎯
- [ ] Playwright E2E 关键路径 (登录 → 创建 KB → 上传 → 问答)
- [ ] 集成到 release-ci
- [ ] 建立测试编写规范 (新功能必须附带测试)

---

## 7. 测试编写规范

### 7.1 命名规范
```python
# 文件: test_{module_name}.py
# 函数: test_{method}_{scenario}_{expected_result}
def test_create_kb_with_valid_data_returns_201():
    ...
def test_create_kb_without_name_raises_validation_error():
    ...
```

### 7.2 AAA 模式
```python
def test_example():
    # Arrange — 准备数据和依赖
    service = KnowledgeService(mock_session)
    
    # Act — 执行被测行为
    result = await service.create_kb(name="test")
    
    # Assert — 验证结果
    assert result.name == "test"
    assert result.id is not None
```

### 7.3 Fixture 复用
- 通用 mock 放 `conftest.py`
- 模块专用 fixture 放同目录 `conftest.py`
- 避免在测试函数内重复构造相同的 mock

### 7.4 CI 红线
- 新增功能 PR 必须包含对应测试
- 覆盖率不得低于当前基线 (ratchet 机制)
- 测试不得依赖外部网络或真实 API Key
