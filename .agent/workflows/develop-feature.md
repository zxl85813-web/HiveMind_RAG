---
description: 开发新功能前的标准流程 — 先查注册表再开发
---

# 🔄 开发新功能标准流程

每次开发新功能时，**必须**按以下流程执行。这确保了组件复用、一致性和可追溯性。

## 步骤

### 1. 生态探索与技能匹配 (Skill Discovery)
- **触发**: 当需求涉及通用能力（部署、数据清洗、第三方集成等）时。
- **动作**: 使用 `find-skills` 技能（`npx skills find <query>`）。
- **目的**: 避免重复造轮子，看看是否有 Vercel 等大厂沉淀的开箱即用 Agent Skill 可以解决。

### 2. 架构图谱寻路与注册查询 (Architectural Mapping)
- **执行命令**: 使用 `architectural-mapping` 技能。
- **动作**: 
  ```powershell
  python .agent/skills/architectural-mapping/scripts/query_architecture.py --req "新功能相关关键词"
  ```
- **目的**: 
  - 检查是否已存在相似功能（替代单纯 cat REGISTRY.md）。
  - **精准定位**: 获取受影响的现有文件调用链和绝对路径，避免 AI 幻觉生成错误路径。

### 2. 确认目录位置
- 对照 `.agent/rules/project-structure.md` 确认新文件应放在哪个目录。
- **强制**: 必须遵循图谱建议的物理隔离边界。

### 4. 检查依赖、组件库与前沿最佳实践
- 前端: 新功能需要的 UI 组件是否在 Ant Design / Ant Design X 中已有？如果不确定复合组件如何设计，请查阅 `vercel-composition-patterns`。
- 后端: 是否可以复用 `services/` 层已有的服务？
- 性能: 涉及数据请求和组件状态时，严格遵守 `vercel-react-best-practices` 规则。

### 4. 极微任务切片与 TDD 开发 (GSD 加速引擎)
- **第一步 (规划)**: 调用 `generate-micro-plan` 技能。
  - 基于第一步查出的图谱路径，将功能拆解为 **2-5 分钟** 的微型 TDD 任务。
  - 任务列表必须写入 `TODO.md` 或变更档。
- **第二步 (执行)**: 进入 `subagent-tdd-loop` 循环。
  - **红 (Red)**: 写必挂测试。
  - **绿 (Green)**: 写最小实现。
  - **重构/安全门禁**: 强制运行 `./.agent/checks/run_checks.ps1`。
  - **提交**: 每个微任务完成后自动 Git Commit。

### 5. 更新功能注册表与图谱同步
- 在 `REGISTRY.md` 中注册新功能/组件。
- **强制同步**: 运行 `python .agent/skills/architectural-mapping/scripts/index_architecture.py` 将新代码逻辑重写回 Neo4j 图谱。

### 7. 一致性核查与 UI 审计
- 日志、配置、Design Token 是否符合规范？
- **架构自省**: 是否存在绕过拦截器或破坏韧性设计的写法？
- **UI/UX 审计**: 运行 `web-design-guidelines` 技能检查代码，确保无界面的瑕疵。

### 8. 集成测试生成 (E2E)
- **动作**: 如果变更涉及完整的主链路流程（如提交表单、状态切换），必须调用 `playwright-generate-test` 技能。
- **目的**: 将刚才完成的 TDD 原则上浮至端到端（E2E）层级，用 Playwright 验证用户真实交互行为。

## 流程图 (Superpowered HiveMind)
```
需求碰撞 (REQ) → 生态检索(find-skills) → 图谱寻路 (Neo4j) → [冲突/复用?] → YES → 扩展现有
                          ↓ NO
                     确认物理目录
                          ↓
                     核对 Vercel 性能与组件规范 (React Rules)
                          ↓
                     极微切片 (Micro-Plan)
                          ↓
                     TDD 子代理循环 (Subagent Loop)
                          ↓
                     质量门禁 (run_checks.ps1) + Commit
                          ↓
                     UI 与合规审计 (Web Design Guidelines)
                          ↓
                     E2E 测试生成 (Playwright)
                          ↓
                     图谱与注册表自更新 (Index)
                          ↓
                     完成 ✅
```

