# HMER Phase 1 - 架构重构极微切片计划 (Micro-Plan)

> **对于 AI Agent:** 必须使用 `subagent-tdd-loop` 技能来逐个执行这些 Task。请按照 checkbox (`- [ ]`) 的顺序推进。

**目标:** 解决 745ms TTFT 性能瓶颈，实现意图预测脚手架 (Intent Scaffolding) 与多路并行检索。
**图谱锚点:** `RAGGateway`, `SwarmOrchestrator`, `IntentScaffoldingService`, `TieredParallelOrchestrator`
---

### Task 1: 数据模型扩展 (Persistence)

**涉及文件:**
- Modify: `backend/app/models/observability.py`
- Create: `backend/app/models/intent.py`
- Test: `backend/tests/unit/models/test_observability_v1.py`

- [ ] **Step 1: Write the failing test (Red)**
  ```python
  def test_intent_cache_model_fields():
      from app.models.intent import IntentCache
      cache = IntentCache(query_hash="abc", predicted_intent="chat")
      assert cache.query_hash == "abc"
  ```
- [ ] **Step 2: 用本地基建运行它并期待失败**
  Run: `pytest backend/tests/unit/models/test_observability_v1.py`
  Expected: FAIL (ModuleNotFoundError)
- [ ] **Step 3: Write minimal implementation**
  Create `backend/app/models/intent.py` with `IntentCache` class.
- [ ] **Step 4: Check & Pass (Green)**
  Run: `./.agent/checks/run_checks.ps1`
  Expected: PASS
- [ ] **Step 5: Git Commit**
  Run: `git add . && git commit -m "feat: add intent cache persistence layer"`

---

### Task 2: 意图预测脚手架 (Intent Scaffolding Service)

**涉及文件:**
- Create: `backend/app/services/intent_scaffolding.py`
- Test: `backend/tests/unit/services/test_intent_scaffolding.py`

- [ ] **Step 1: Write the failing test (Red)**
  ```python
  @pytest.mark.asyncio
  async def test_predict_intent_partial():
      service = IntentScaffoldingService()
      intent = await service.predict_intent_stream("What is the...")
      assert intent is not None
  ```
- [ ] **Step 2: 期待失败**
  Expected: FAIL
- [ ] **Step 3: Minimal Implementation**
  Implement `predict_intent_stream` using basic keyword matching or a fast-eco model.
- [ ] **Step 4: Check & Pass**
  Expected: PASS
- [ ] **Step 5: Git Commit**

---

### Task 3: 多路并行检索器 (Tiered Parallel Orchestrator)

**涉及文件:**
- Create: `backend/app/services/retrieval/parallel_orchestrator.py`
- Test: `backend/tests/unit/services/test_parallel_retrieval.py`

- [ ] **Step 1: Write the failing test (Red)**
  ```python
  @pytest.mark.asyncio
  async def test_parallel_execution():
      orchestrator = TieredParallelOrchestrator()
      results = await orchestrator.search_all("test query")
      assert "vector" in results
  ```
- [ ] **Step 2: 期待失败**
- [ ] **Step 3: Implementation**
  Using `asyncio.gather` to trigger Vector, Graph, and Grep.
- [ ] **Step 4: Check & Pass**
- [ ] **Step 5: Git Commit**

---
