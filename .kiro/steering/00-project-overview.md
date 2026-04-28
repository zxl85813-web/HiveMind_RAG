---
description: 项目总纲 — 始终加载的核心规范与约束
inclusion: always
---

# HiveMind Intelligence Swarm — 开发总纲

## 项目概述
这是一个 AI-First 的智能协作平台，后端 FastAPI + SQLModel，前端 React + TypeScript + Ant Design。
系统包含 RAG 检索增强生成、多智体蜂巢协作、知识图谱、治理引擎等核心模块。

## 核心规范索引

本项目有完善的开发规范体系，位于 `.agent/rules/` 目录。开发前**必须**遵守以下规范：

### 编码规范（始终生效）
#[[file:.agent/rules/coding-standards.md]]

### 项目结构（始终生效）
#[[file:.agent/rules/project-structure.md]]

### API 设计规范
#[[file:.agent/rules/api-design-standards.md]]

## 关键约束速查

### 后端一致性（必须遵守）
- 配置: `app.core.config.settings`，禁止 `os.environ`
- 日志: `loguru.logger`，禁止 `print()` 和 `logging`
- HTTP: `httpx` async，禁止 `requests`
- 数据验证: Pydantic / SQLModel，禁止 raw dict
- 时间: `datetime.now(timezone.utc)`，禁止 `datetime.now()`
- ID: `uuid.uuid4()`，禁止自增 ID

### 前端一致性（必须遵守）
- UI: Ant Design / Ant Design X，禁止自制基础组件
- 样式: CSS Modules + Design Tokens，禁止硬编码色值
- 状态: Zustand store，禁止 useState 管理跨组件状态
- 数据: @tanstack/react-query，禁止手动 useEffect + fetch
- 类型: 禁止 `any`，使用 `unknown` + 类型收窄

### 模块调用边界（违反将被 Reject）
- `api/routes/` → 只能调用 `services/`, `auth/`, `schemas/`, `common/`
- `services/` → 可调用 `agents/`, `auth/`, `audit/`, `models/`, `common/`
- `agents/` → 可调用 `llm/`, `memory/`, `rag/`, `mcp/`, `skills/`
- 禁止反向依赖（如 `agents/` 调用 `api/` 或 `services/`）

### API 响应格式（强制）
所有 API 必须使用 `ApiResponse.ok(data=...)` 包装，禁止裸返回 List/Dict。

## 开发工作流
#[[file:.agent/rules/design-and-implementation-methodology.md]]

## 当前开发状态
#[[file:TODO.md]]
