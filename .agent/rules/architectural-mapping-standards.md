# 📜 架构图谱使用规范

> **原则**: 凡涉及结构性变更（修改核心逻辑、重构、删除代码），必须先询问“软件大脑”。

## 1. 强制性行为
- **自省优先**: 在响应用户重构请求前，AI Agent 必须调用 `query_architecture.py` 获取当前受影响的节点。
- **关联补全**: 在创建新测试或新设计时，必须在文档/代码中显式标记关联项（如 `@covers REQ-XXX`, `@specifies DES-XXX`），以便索引器自动捕获。
- **状态同步**: 任何导致目录结构、Skill 增减的变更，必须在任务结束前运行 `index_architecture.py` 刷新图谱。

## 2. 路由逻辑建议
- **精准读码**: AI Agent 应根据图谱返回的 `files` 列表进行多线程读取，禁止在不确定的情况下对 `backend/app` 进行递归扫描以节省 Tokens。
- **影子检查**: 如果发现代码中存在图谱未记录的关系，Agent 应主动报告并更新 `index_architecture.py` 的解析逻辑。

## 3. 标准化标签
- `@covers REQ-NNN`: 测试代码关联需求。
- `@specifies DES-NNN`: 设计文档关联设计单。
- `@implements APP/PATH`: 代码实现文件路径映射。

## 4. 刚性治理 (Rigid Governance)
- **零容忍备份**: 禁止在代码库中存放 `.bak`, `.tmp`, `.old` 等备份文件。必须使用 Git 版本管理而非手动备份。
- **强制登记**: 所有位于 `scripts/` 或 `app/scripts/` 的工具脚本，必须在 `REGISTRY.md` 中登记职责。未登记且孤立的脚本将被视为死代码清理。
- **孤立节点巡检**: Agent 每次完成重大重构后，应运行 `scratch/analyze_isolated.py`。如果发现新增了非预期的孤立节点，必须立即修复关联关系或清理冗余资产。
- **关联可追溯**: 任何新生成的 Design Doc (DES) 必须至少链接到一个 Requirement (REQ)。禁止创建任何物理上孤立的架构节点。

---
*Created by Antigravity AI | 2026-04-16 (Updated)*
