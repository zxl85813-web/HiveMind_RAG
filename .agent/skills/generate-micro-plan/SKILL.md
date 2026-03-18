---
name: generate-micro-plan
description: 极微粒度任务规划器 (基于 Superpowers 理念)，结合Neo4j架构图谱将设计文档精确拆解为 2-5 分钟的 TDD 微型任务列表
---

# 🔪 Generate Micro Plan (微观任务切片)

## Overview (总则)
撰写极其详细的执行计划，假设接手代码的 AI Agent (或者新手程序员) 对我们的项目毫无上下文。你不仅要告诉他们改什么，还要告诉他们精确的文件路径、需要写的测试、以及预期的运行结果。
- 必须遵循 DRY, YAGNI, TDD。
- 强制**高频 Commit**。

**前置依赖声明：** "我正在使用 `generate-micro-plan` 技能来创建微型实施计划。"

## 🕸️ 图谱寻路 (Graph-Driven File Resolution)
在规划 Task 涉及的具体文件 (`Files`) 前，你**必须**使用 Neo4j 图谱查询脚本获取真实的关联文件路径，严禁凭空捏造（幻觉）代码路径！
- 执行查询：`python .agent/skills/architectural-mapping/scripts/query_architecture.py --req "相关需求或实体"`
- 将查询返回的真实文件路径用于后续的任务切片。

## Bite-Sized Task Granularity (2-5分钟极微粒度)
每一个 Task 只能包含一个原子的 TDD 动作循环：
1. "写出必挂的测试"
2. "运行测试，确认它失败了 (Red)"
3. "写最小实现代码"
4. "运行测试并通过质量门禁 (Green)"
5. "Commit"

## 📍 HiveMind 本土化输出
你的输出结果必须是一份 Markdown 格式的 Task List，请将其追加到所在功能分支的变更目录或项目根目录的 `TODO.md` 中。包含如下头部（Header）：

```markdown
# [Feature Name] 极微切片计划 (Micro-Plan)

> **对于 AI Agent:** 必须使用 `subagent-tdd-loop` 技能来逐个执行这些 Task。请按照 checkbox (`- [ ]`) 的顺序推进。

**目标:** [一句话描述]
**图谱锚点:** [列出刚才查出来的主要模块节点]
---
```

## Task Structure (强制输出格式)
在生成 Task 时，必须使用以下格式：

### Task N: [组件/逻辑名]

**涉及文件:**
- Create/Modify: `精确查找到的代码路径`
- Test: `精确查找到的测试路径`

- [ ] **Step 1: Write the failing test (Red)**
  (请在此处写下完整的 pytest 或 vitest/playwright 测试用例雏形)

- [ ] **Step 2: 用本地基建运行它并期待失败**
  Run: `pytest tests/...` (后端) 或 `npm run test ...` (前端)
  Expected: FAIL

- [ ] **Step 3: Write minimal implementation**
  (提供能让测试通过的最小代码边界示例)

- [ ] **Step 4: Check & Pass (Green)**
  Run: `./.agent/checks/run_checks.ps1` (调用全局质量安全门禁)
  Expected: PASS (0 Errors)

- [ ] **Step 5: Git Commit**
  Run: `git add . && git commit -m "feat/fix: pass task N"`

## Remember
- **永远提供绝对精准的文件路径** (由图谱保证)。
- 提供完整的测试和验证命令。
- 一次只解决一个小问题点。
