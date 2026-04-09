---
description: 启动“收割模式”：自动化诊断、环境注入、批量测试与深度验收的一站式流程
---

# 🚜 测试收割工作流 (Harvest Testing)

> **触发方式**: 输入 `/harvest-test` 或在完成核心资产修改后触发。
> **目标**: 将资产从“未测试”状态转化为“高确定性”的可验证状态。

## 📋 执行路线图 (Execution Roadmap)

### Step 1: 盲区诊断 (Gaps Detection)
// turbo
```powershell
python .agent/skills/graph-driven-testing/scripts/gap_analyzer.py --mode assets
```
- 根据输出的红色 ID（如 `REQ-NNN`），确定本次收割的优先级。

### Step 2: 环境抗性准备 (Poisoning)
// turbo
```powershell
python .agent/skills/l2-integration-governance/scripts/poison_injector.py --type zombie_node
```
- 如果收割目标涉及数据库操作，必须先注入背景噪音。

### Step 3: 自动化用例生成与执行 (Validated Gen)
// turbo
```powershell
python backend/scripts/testing/hm_test.py all --threshold 60
```
- **自愈机制**: 如果测试失败，读取 `logs/testing/report.html` 中的异常信息，进入 `sys-debug` 循环修复代码或 Case。

### Step 4: 逻辑真相核检 (Deep Probing)
// turbo
```powershell
python .agent/skills/l2-integration-governance/scripts/integrity_prober.py --id <刚刚生成的业务ID>
```
- 验证数据库物理层的拓扑一致性。

### Step 5: 契约审计 (Contract Safeguard)
// turbo
```powershell
python .agent/skills/l2-integration-governance/scripts/contract_diff.py --baseline <基准文件> --current <最新文件>
```

### Step 6: 图谱回填 (Knowledge Sync)
- **动作**: 运行 `scripts/index_architecture.py`。
- **结果**: Neo4j 中的相关资产节点颜色变绿，并关联最新的 `TST` 节点。

---

## 🛡️ 验收 checklist
- [ ] `hm_test.py` 报告全绿。
- [ ] `integrity_prober` 反馈无逻辑偏移。
- [ ] 开发者的 Reflection Log 中记录了本次收割发现的 Bug 数量及修复点。
