---
description: 开发新功能前的标准流程 — 先查注册表再开发
---

# 🔄 开发新功能标准流程

每次开发新功能时，**必须**按以下流程执行。这确保了组件复用、一致性和可追溯性。

## 步骤

### 1. 架构图谱寻路与注册查询 (Architectural Mapping)
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

### 3. 检查依赖与组件库
- 前端: 新功能需要的 UI 组件是否在 Ant Design / Ant Design X 中已有？
- 后端: 是否可以复用 `services/` 层已有的服务？

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

### 6. 一致性最后核查
- 日志、配置、Design Token 是否符合规范？
- **架构自省**: 是否存在绕过拦截器或破坏韧性设计的写法？

## 流程图 (Superpowered HiveMind)
```
需求碰撞 (REQ) → 图谱寻路 (Neo4j) → [冲突/复用?] → YES → 扩展现有
                         ↓ NO
                    确认物理目录
                         ↓
                    极微切片 (Micro-Plan)
                         ↓
                    TDD 子代理循环 (Subagent Loop)
                         ↓
                    质量门禁 (run_checks.ps1) + Commit
                         ↓
                    图谱与注册表自更新 (Index)
                         ↓
                    完成 ✅
```

