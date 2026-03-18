# 🦸 Superpowers x HiveMind: 增强版工业级研发框架指南

> **现状**: 本项目已深度集成 `Superpowers` 核心技能，并结合 `Neo4j` 架构图谱与 `FE-GOV` 治理标准进行了“本土化”缝合。

---

## 🛠️ 核心技能图谱 (New Skills)

### 1. 🎯 [generate-micro-plan](.agent/skills/generate-micro-plan/SKILL.md) (极微计划)
- **触发时机**: 在任何 `Implementation` 动作之前。
- **职责**: 
  - 调用 `architectural-mapping` 查询 Neo4j 图谱，获取准确的文件依赖和路径。
  - 将复杂需求切分为 **2-5 分钟** 的原子级 TDD 任务。
  - 强制生成 Red (测试失败) -> Green (功能实现) 的检查清单。

### 2. 🔁 [subagent-tdd-loop](.agent/skills/subagent-tdd-loop/SKILL.md) (TDD 循环)
- **职责**: 派发隔离的子代理执行任务，并强制：
  - **写必挂测试**: 证明测试确实有效。
  - **最小量实现**: 拒绝过度设计 (YAGNI)。
  - **自动 Commit**: 每一个原子任务完成后自动生成高质量 Git 提交。

### 3. 🔍 [systematic-debugging](.agent/skills/systematic-debugging/SKILL.md) (系统化调试)
- **职责**: 禁止盲目猜测，强制执行 **Root Cause Tracing (回溯追踪)**。
- **防御原则**: 修复一个 Bug 时，必须在数据流经的**每一层 (Entry/Logic/Env/Debug)** 都添加校验。

### 4. ✅ [verification-before-completion](.agent/skills/verification-before-completion/SKILL.md) (完工验证)
- **铁律**: **证据先于声明**。如果不运行特定的验证命令并查看输出，严禁声称“Done”或“Fixed”。

---

## 🎨 前端工程化与生态扩展 (Frontend & Ecosystem Extensions)

随着技能生态的丰富，我们在基础 TDD 循环的上方，增加了垂直领域（主要是前端、UI、测试）的治理能力：

### 1. 🔍 [find-skills](.agents/skills/find-skills/SKILL.md) (生态技能检索)
- **触发时机**: 面临新的技术需求，或在规划新功能时寻找大厂打磨好的最佳实践。
- **职责**: 使用 `npx skills find` 从开源市场检索相关的现成技能包。

### 2. ⚛️ [vercel-react-best-practices](.agents/skills/vercel-react-best-practices/SKILL.md) (React 性能规范)
- **触发时机**: 修改 React 组件、Next.js 路由或涉及状态请求时。
- **职责**: 强制进行性能规则审计，避免异步瀑布流（Waterfalls）、消除不必要的 Re-render。

### 3. 🧩 [vercel-composition-patterns](.agents/skills/vercel-composition-patterns/SKILL.md) (React 复合模式)
- **触发时机**: 当面临“组件通过增加 `boolean` 属性导致属性爆炸”的重构诉求时。
- **职责**: 指导 Agent 使用组合（Composition）、Context 提升等模式写出可维护的 React 代码。

### 4. 💅 [web-design-guidelines](.agents/skills/web-design-guidelines/SKILL.md) (Web 设计/无障碍准则)
- **触发时机**: UI 组件完工前的最后审查 (`/develop-feature` 流程的第 7 步)。
- **职责**: 通过 Vercel Labs 提供的远程设计规范，对颜色对比度、间距、交互提示等进行检查。

### 5. 🧪 [playwright-generate-test](.agents/skills/playwright-generate-test/SKILL.md) (E2E 测试生成)
- **触发时机**: 涉及完整业务链路的用户故事开发完毕后。
- **职责**: 指导 Playwright MCP 结合上下文自动构建并执行端到端自动化测试脚本。

---

## 🌊 核心工作流变更 (Modified Workflows)

### `/develop-feature` (开发新功能)
这是本项目最核心的工作流，现已全面“Superhero”化：
1. **图谱寻路**: 弃用手动查阅 `REGISTRY.md`，改为 `query_architecture.py` 获取上下文。
2. **切片计划**: 强制调用 `generate-micro-plan`。
3. **TDD 执行**: 全过程在子代理沙盒中完成，主代理仅负责指挥和合并。
4. **同步回馈**: 完成后自动运行 `index_architecture.py` 同步新文件到 Neo4j。

---

## 🧑‍💻 维护者守则 (Maintainer Rules)

1. **先计划，后动手**: 永远不要直接修改代码。必须先看到勾选框。
2. **测试是第一等公民**: 如果一个修改没有对应的测试用例（或改动了已有测试），Agent 必须拒绝合并。
3. **图谱即真理**: 每次结构性重构后，确保运行 `index_architecture.py`。
4. **证据固化**: 所有的验证日志（如 Vitest 结果）应记录在任务汇报中。

---

## 📈 收益预估
- **回归率**: 降低 60%-80%。
- **代码一致性**: 提升 100%（强制遵循图谱和 Lint）。
- **心智负担**: 线性化。Agent 每次只处理 5 分钟逻辑，不再会“在 Context 中迷失”。

---
*HiveMind Governance Team (Adapting Superpowers principles)*
