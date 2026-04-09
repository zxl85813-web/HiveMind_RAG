---
name: testing-orchestrator
description: 负责全量测试的大规模编排与执行。每当用户需要“跑一边测试”、“执行全量检查”、“验证覆盖率是否达标”或“进行批量回归”时，必须启动此技能。
---

# 🎼 测试编排技能 (Testing Orchestrator Skill)

> **使用场景**: 
> 1. 执行 L1-L2 的全量作业。
> 2. 自动化生成并查看 `logs/testing/report.html`。
> 3. 强制执行覆盖率门槛校验。

## 🧩 核心组件 (Specialists)
- **Executor**: 封装在 `backend/scripts/testing/hm_test.py`。
- **Coverage Guard**: 监控 `pyproject.toml` 中的 `fail_under` 阈值。

## 📝 执行步骤 (Engineering Workflow)

### Stage 1: 选择执行模式
- **Unit Mode**: `python scripts/testing/hm_test.py unit --path <dir>` (核心逻辑验证)。
- **Fuzz Mode**: `python scripts/testing/hm_test.py fuzz` (边界压力探测)。
- **Mutate Mode**: `python scripts/testing/hm_test.py mutate --path <file>` (用例韧性验证)。

### Stage 2: 报告审计
运行结束后，必须检查 `backend/logs/testing/report.html`。如果发现 FAILED 项目，必须挂载 `systematic-debugging` 技能进行修复。

### Stage 3: 阈值验收
如果 `pytest-cov` 反馈低于 60%，该批次作业被视为“验收未通过”，自动标记为 `FAIL_NOT_ENOUGH_COVERAGE`。

## 🛡️ Best Practices
- **Parallel First**: 优先运行 `unit` 模式。
- **Cleanup**: 运行后确认环境变量 `TESTING=1` 已正确清理。
