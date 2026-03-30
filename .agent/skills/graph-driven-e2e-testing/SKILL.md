---
name: graph-driven-e2e-testing
description: 基于 Neo4j 架构图谱的端到端 (E2E) 测试用例全链路生成器。
---

# 🕸️ Graph-Driven E2E Test Generator (图谱驱动测试生成)

> **触发时机 (When to use)**: 当用户要求“根据图谱生成完整的测试用例”、“对 REQ-XXX 进行全路径测试覆盖”、或“确保某项业务实现跨端无断链”时。

## 🧠 核心理念 (Core Concept)

传统的测试生成（如 `generate-tests`）是基于**单个文件 (File-Centric)** 的。
而本技能是基于**业务路径 (Path-Centric)** 的，我们通过查询 Neo4j，将一个 `Requirement` (业务需求) 关联的：
1. **Frontend 状态与动作** (UI_State, UI_Handler)
2. **API 契约** (DataContract, APIEndpoint)
3. **Backend 路由与逻辑** (File, Services)
4. **数据库存储** (DatabaseModel)
...全部串联起来，生成一个 **“模拟用户真实流转”** 的系统级集成测试。

## 🛠️ 执行步骤 (Execution Steps)

### Step 1: 图谱路径提取 (Path Extraction)
首先，不要盲目去猜测代码。你必须先在 Neo4j 中拉取该业务的“全景地图”。
请运行配套脚本提取链路：
```powershell
python .agent/skills/graph-driven-e2e-testing/scripts/extract_business_path.py --req <REQ-ID>
# 或者如果是针对某个功能点：
python .agent/skills/graph-driven-e2e-testing/scripts/extract_business_path.py --query "KnowledgeBase"
```

### Step 2: 链路理解 (Comprehension)
仔细阅读上述脚本输出的 JSON 链路报告。识别以下关键节点：
- **Trigger**: 前端是哪个 `UI_Handler` 触发的操作？
- **Contract**: 它请求的 `APIEndpoint` 是什么？Payload 长什么样 (`DataContract`)？
- **Process**: 后端经过了哪几个 Service 文件？
- **Store**: 最终落到了哪个 Database Model？

### Step 3: 深入代码获取精确结构 (Deep File Introspection) -> 极其重要
图谱只告诉你“它在哪”，不会告诉你“长啥样”。
拿到图谱路径中的 `File` 节点或 `DataContract` 名字后，你**必须**使用 `view_file` 工具打开对应的真实文件（例如打开 `backend/app/schemas/knowledge.py` 或 `frontend/src/services/api.ts`）。
- **必须读取 Pydantic/TS 接口定义**，以确保你在测试中构造的 Payload 拥有 100% 正确的字段和类型（不准靠猜！）。
- **必须阅读报错的 Service 函数**，了解它依赖哪些内部 `def`，从而决定如何正确使用 `@patch` 拦截。

### Step 4: 知识对齐 (Knowledge Alignment)
在写任何代码前，你必须先使用 `view_file` 工具阅读 `.agent/skills/graph-driven-e2e-testing/library/testing-patterns.md`，严格遵循其中的 Mock 定义与断言规范。

### Step 5: 多维端到端测试生成 (Three-Tier E2E Generation)
根据提取出的图谱链路，你需要生成以下**三种粒度的测试资产**。
要求：**你的每一行关键测试代码（如发起请求、Mock、断言）上方，必须加上对应的图谱节点追踪注释。**
例如：`# [Trace: APIEndpoint /api/v1/knowledge]` 或 `# [Trace: DataContract KnowledgeBaseCreate]`。

1. **API 契约测试 (Backend - pytest)**
   - **位置**: `backend/tests/api/`
   - **目标**: 针对链路中的 `APIEndpoint` 与 `DataContract` (请求/返回负载)，使用 `TestClient` 发起快速网络请求验证。主要测边界、权限拦截、字段有效性。

2. **后端全链路系统测试 (Backend - pytest)**
   - **位置**: `backend/tests/system/`
   - **目标**: 从 `SwarmOrchestrator` 或顶层 Service 入手，针对链路中的业务核心枢纽进行验证，必须走到 `DatabaseModel` 或副作用发生点（如打点记录）。

3. **前端 UI 自动化测试 (Frontend - Playwright)**
   - **位置**: `frontend/tests/e2e/` (如果目录不存在则创建)
   - **目标**: 找到链路中的 `UI_State` 和 `UI_Handler`。编写一个 `.spec.ts` 脚本，模拟点击触发 `Handler` 的完整流程。必须包含拦截或模拟真实后端的网络请求 (Request Interception)。

### Step 5: 全自动自我纠错闭环 (Self-Healing Loop) - 极其关键！
代码生成绝非终点，**你必须证明它能跑得通**。
1. **执行 Pytest**: 运行 `pytest <你刚写的后端测试文件> -v`。
2. **执行 Playwright**: 运行 `npx playwright test <你刚写的前端测试文件>` (如果环境允许)。
3. **根据报错重构代码**: 如果测试 Fail，立刻提取报错 `stderr`，修复你的断言、修复忘记 mock 的引用，然后再次执行。此循环最多 3 次。
4. **交付成果**: 向用户展示绿色的测试输出面板以及代码说明。


---
**系统提示**: 此技能极大地利用了我们构建的 `index_architecture` 图谱数据。你编写的测试绝不应该只局限于某一个 function，而是要证明 **“这条路线从头走到尾是畅通的”**。
