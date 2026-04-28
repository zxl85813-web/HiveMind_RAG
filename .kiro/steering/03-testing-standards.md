---
description: 测试规范 — 编辑测试文件时自动加载
inclusion: fileMatch
fileMatchPattern: "**/test_*.py,**/*.test.{ts,tsx},**/*.spec.{ts,tsx},**/tests/**"
---

# 测试规范

编写测试时，必须遵守以下规范。

## 完整测试指南
#[[file:.agent/rules/testing_guidelines.md]]

## 速记要点

### 测试金字塔
- 单元测试 70%: 独立函数/Service 方法，毫秒级
- 集成测试 20%: API → Service → DB 贯通，用内存 SQLite
- E2E 测试 10%: Playwright 驱动，仅覆盖主干流程

### 覆盖率
- 全局 ≥ 80%，增量代码 ≥ 90%

### Mock 决策树
1. 系统级依赖 (os.time, uuid) → 需要固定值时 mock
2. 昂贵的外部服务 (LLM, 邮件) → 必须 mock
3. 内部 Service → 优先不 mock，构造 Fixtures
4. 数据库 Session → 集成测试禁止 mock，用内存 SQLite

### 常见陷阱
- Pydantic V2: 构造时必须提供所有必填字段
- Async Generator: 用 `MagicMock(return_value=gen())` 而非 `AsyncMock`
- 双视角测试: 每个 API 至少写契约视角 + 容错视角
