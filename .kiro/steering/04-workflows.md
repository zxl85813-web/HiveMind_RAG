---
description: 开发工作流索引 — 手动引用
inclusion: manual
---

# 开发工作流索引

本项目定义了标准化的开发工作流，位于 `.agent/workflows/` 目录。
在执行特定任务时，请参考对应的工作流文档。

## 可用工作流

| 工作流 | 用途 | 文件 |
|--------|------|------|
| 创建组件 | 新建前端组件的标准流程 | `.agent/workflows/create-component.md` |
| 创建 API | 新建后端 API 端点的标准流程 | `.agent/workflows/create-api.md` |
| 功能分解 | 将大需求拆解为可执行任务 | `.agent/workflows/decompose-feature.md` |
| 开发功能 | 端到端功能开发流程 | `.agent/workflows/develop-feature.md` |
| 数据库设计 | 新建/修改数据库表的流程 | `.agent/workflows/design-database.md` |
| 代码审查 | Code Review 标准流程 | `.agent/workflows/code-review.md` |
| 编写测试 | 测试编写标准流程 | `.agent/workflows/write-tests.md` |
| 需求提取 | 从对话中提取结构化需求 | `.agent/workflows/extract-requirement.md` |

## 使用方式
在 Kiro 聊天中输入 `#04-workflows` 即可加载此索引。
需要具体工作流时，可以告诉我"按照 create-api 工作流来"。
