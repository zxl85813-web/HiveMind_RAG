---
name: l2-integration-governance
description: 负责 L2 级的集成测试治理，包含脏数据注入、契约审计与跨库数据一致性探测。当用户提到“API 变更”、“数据库同步”、“脏数据处理”、“契约测试”或“副作用验证”时，必须调用此技能进行审计。
---

# 🛡️ L2 集成治理技能 (L2 Governance Skill)

> **使用场景**: 
> 1. 在 API 契约变更后，验证前端调用是否会断裂。
> 2. 验证复杂业务流程（如 RAG 写入）在多个数据库（PG/Neo4j）间的一致性。
> 3. 验证系统在面对“脏数据/坏数据”时的鲁棒性。

## 🧩 核心组件 (Specialists)

### 1. 脏数据注入器 (`scripts/poison_injector.py`)
- **任务**: 在测试前人为制造故障场景（僵尸节点、循环依赖、超大载荷）。
- **目的**: 确保系统不因为底层数据的小毛病而产生非预期的 500 崩溃。

### 2. 真相探测器 (`scripts/integrity_prober.py`)
- **任务**: 运行深层业务 Invariants 审计。
- **目的**: 绕过 API 的“伪 200”回复，直接检查数据库物理状态是否符合业务逻辑。

### 3. 契约校验器 (`scripts/contract_diff.py`)
- **任务**: 监控 OpenAPI 变更。
- **目的**: 预防 Breaking Changes 导致的生产事故。

## 📝 执行步骤 (Engineering Workflow)

### Step 1: 环境预热 (Poisoning)
```powershell
python .agent/skills/l2-integration-governance/scripts/poison_injector.py --type zombie_node
```

### Step 2: 触发业务流程
使用 `hm_test.py` 运行对应的集成测试用例。

### Step 3: 深度审计
```powershell
python .agent/skills/l2-integration-governance/scripts/integrity_prober.py --id "TARGET_ENTITY_ID"
```

## 🛡️ 验收标准 (DoD)
- 所有 `Invariant Rules` 探测结果为 PASS。
- 脏数据下的 API 响应必须是 4xx (Client Error) 或有优雅处理，严禁 5xx。
- 契约 Diff 分析结果必须经过 Manual 确认或符合向下兼容规则。
