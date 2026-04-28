---
description: 后端开发规范 — 编辑 Python 文件时自动加载
inclusion: fileMatch
fileMatchPattern: "**/*.py"
---

# 后端开发规范 (Python / FastAPI)

编辑后端代码时，必须遵守以下规范。

## 后端模块设计规范
#[[file:.agent/rules/backend-design-standards.md]]

## 后端工具库清单
#[[file:.agent/rules/backend-utilities-inventory.md]]

## 数据库设计规范
#[[file:.agent/rules/database-design-standards.md]]

## 测试规范
#[[file:.agent/rules/testing_guidelines.md]]

## 速记要点

### 五层流水线
1. 路由层 `api/routes/` — 接收请求、调 Service
2. 服务层 `services/` — 核心业务逻辑
3. 智能层 `agents/`, `rag/` — LLM 推理、向量检索
4. 基础设施层 `core/`, `auth/` — DB、JWT、配置
5. 数据层 `models/`, `schemas/` — ORM、API 契约

### Service 方法命名
- `get_` 获取单个 | `list_` 获取列表 | `create_` 创建
- `update_` 修改 | `remove_` 软删除
- `_check_` / `_validate_` 内部校验 | `_build_` 内部构建

### 异常处理
- 使用 `app.core.exceptions` 中的自定义异常
- 禁止在 Service 中返回 tuple 或特殊字符串表示错误
- 全局异常处理器统一转换为 ApiResponse 格式
