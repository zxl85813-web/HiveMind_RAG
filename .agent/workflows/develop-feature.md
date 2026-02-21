---
description: 开发新功能前的标准流程 — 先查注册表再开发
---

# 🔄 开发新功能标准流程

每次开发新功能时，**必须**按以下流程执行。这确保了组件复用、一致性和可追溯性。

## 步骤

### 1. 查阅功能注册表 (REGISTRY.md)
// turbo
```bash
cat REGISTRY.md
```
- 检查是否已存在相同或相似功能
- 如果存在相似功能，评估是否可以**复用**或**扩展**现有代码
- 如果决定新建，确认不会与现有功能冲突

### 2. 确认目录位置
- 对照 `.agent/rules/project-structure.md` 确认新文件应放在哪个目录
- **严禁创建新目录**，除非先更新 project-structure.md 并得到确认

### 3. 检查依赖
- 前端: 新功能需要的 UI 组件是否在 Ant Design / Ant Design X 中已有？
- 后端: 是否可以复用 `services/` 层已有的服务？
- 是否需要新的 Pydantic Schema？（放在 `schemas/` 目录）

### 4. 编写代码
- 遵循 `.agent/rules/coding-standards.md` 的规范
- 前端样式遵循 `.agent/rules/frontend-design-system.md`
- **必须包含完整注释**（模块 docstring、类 docstring、方法 docstring）
- 注释中包含 `参见: REGISTRY.md > ...` 的交叉引用

### 5. 更新功能注册表
- 在 `REGISTRY.md` 中注册新功能/组件
- 包含：名称、描述、文件位置、依赖关系、使用示例

### 6. 检查一致性
- 日志用 loguru 了吗？
- 配置用 settings 了吗？
- 前端样式用 Design Token 了吗？
- HTTP 请求走 services/ 层了吗？
- 有没有重复造轮子？

## 流程图
```
需求分析 → 查注册表 → [存在?] → YES → 复用/扩展
                         ↓ NO
                    确认目录位置
                         ↓
                    检查依赖/组件
                         ↓
                    编写代码 (含注释)
                         ↓
                    更新 REGISTRY.md
                         ↓
                    一致性检查
                         ↓
                    完成 ✅
```
