# 🕵️ 架构资产审计工作流 (Graph Audit & Cleanup)
// turbo-all

> **使用场景**: 当项目出现冗余、孤立节点过多，或者需要进行周期性“减肥”与健康检查时启动。

## 📥 准入标准
- 拥有 Neo4j 访问权限。
- 当前分支代码已提交。

## 🚀 审计步骤

### Step 1: 扫描孤立节点
执行诊断脚本，识别失联的资产：
```powershell
python scratch/analyze_isolated.py
```

### Step 2: 自动治理 (Healing)
尝试对存在的孤立节点进行自动化修复：
```powershell
python scratch/govern_isolated_nodes.py
```

### Step 3: 手动判定与归档
- 如果 `Design` 节点依然孤立：检查是否缺失 `关联需求：REQ-XXX` 标签。
- 如果 `File` 节点依然孤立：检查是否为无用代码（Dead Code），确认后物理删除。

### Step 4: 物理审计 (Hard Cleanup)
强制清理磁盘上的冗余垃圾：
```powershell
Get-ChildItem -Recurse -Include *.bak,*.tmp,*.old,*.backup | Remove-Item -Force
Get-ChildItem -Path . -Filter "tmp_*" | Remove-Item -Force
```

### Step 5: 图谱同步与验证
重新索引全量资产，确保图谱与现实 100% 对齐：
```powershell
python .agent/skills/architectural-mapping/scripts/index_architecture.py
```

## 🏁 完工标准
- 图谱中的孤立节点（Isolated Nodes）降至最低（仅剩第三方库或故意预留的资产）。
- `REGISTRY.md` 中记录的所有脚本均能与图谱节点一一对应。
- 磁盘无 `.bak`, `.tmp` 等违规后缀文件。

---
*Created by Antigravity AI | 2026-04-16*
